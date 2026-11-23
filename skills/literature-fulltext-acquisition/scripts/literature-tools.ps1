param([string]$Tool)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$skillRoot = Split-Path -Parent $PSScriptRoot
$settings = @{}
$configPath = Join-Path $skillRoot 'config\local.json'
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    $settings = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json -AsHashtable
}
$toolsHome = if ($env:LITERATURE_TOOLS_ROOT) { $env:LITERATURE_TOOLS_ROOT } else { $settings['tools_root'] }
$protectedRoot = if ($env:LITERATURE_PROTECTED_ROOT) { $env:LITERATURE_PROTECTED_ROOT } else { $settings['protected_root'] }
$configured = -not [string]::IsNullOrWhiteSpace($toolsHome) -and -not [string]::IsNullOrWhiteSpace($protectedRoot)
if ($configured) {
    if (-not [IO.Path]::IsPathFullyQualified($toolsHome) -or -not [IO.Path]::IsPathFullyQualified($protectedRoot)) {
        throw 'Tools and protected roots must be absolute paths.'
    }
    $toolsHome = [IO.Path]::GetFullPath($toolsHome)
    $protectedRoot = [IO.Path]::GetFullPath($protectedRoot).TrimEnd([IO.Path]::DirectorySeparatorChar)
} elseif ($Tool -ne 'status') {
    throw 'Configure tools_root and protected_root in config/local.json, or the LITERATURE_TOOLS_ROOT and LITERATURE_PROTECTED_ROOT environment variables.'
} else {
    $toolsHome = Join-Path $skillRoot '.unconfigured'
}
$runtimeRoot = Join-Path $toolsHome 'runtimes'
$sharedState = Join-Path $toolsHome 'state'
$ToolArguments = @($args)
$entryPoints = @{
    'paper-search'     = Join-Path $runtimeRoot 'paper-search\.venv\Scripts\paper-search.exe'
    'paper-search-mcp' = Join-Path $runtimeRoot 'paper-search\.venv\Scripts\paper-search-mcp.exe'
    'openalex'         = Join-Path $runtimeRoot 'openalex\.venv\Scripts\openalex.exe'
    'instsci'          = Join-Path $runtimeRoot 'instsci\.venv\Scripts\instsci.exe'
    'instsci-mcp'      = Join-Path $runtimeRoot 'instsci\.venv\Scripts\instsci-mcp.exe'
}

function Test-HasOption {
    param(
        [string[]]$Items,
        [string[]]$Names
    )

    foreach ($item in $Items) {
        foreach ($name in $Names) {
            if ($item -eq $name -or $item.StartsWith("$name=")) {
                return $true
            }
        }
    }
    return $false
}

function Get-OptionValue {
    param(
        [string[]]$Items,
        [string[]]$Names
    )

    for ($index = 0; $index -lt $Items.Count; $index++) {
        foreach ($name in $Names) {
            if ($Items[$index] -eq $name) {
                if ($index + 1 -ge $Items.Count) {
                    throw "Missing value for $name."
                }
                return $Items[$index + 1]
            }
            if ($Items[$index].StartsWith("$name=")) {
                return $Items[$index].Substring($name.Length + 1)
            }
        }
    }
    return $null
}

function Get-OptionValues {
    param(
        [string[]]$Items,
        [string[]]$Names
    )

    $values = [System.Collections.Generic.List[string]]::new()
    for ($index = 0; $index -lt $Items.Count; $index++) {
        $item = $Items[$index]
        foreach ($name in $Names) {
            if ($item -eq $name) {
                if ($index + 1 -ge $Items.Count) {
                    throw "Missing value for $name."
                }
                $values.Add($Items[$index + 1])
                $index++
                break
            }
            if ($item.StartsWith("$name=")) {
                $values.Add($item.Substring($name.Length + 1))
                break
            }
            if ($name.Length -eq 2 -and $name.StartsWith('-') -and -not $name.StartsWith('--') -and $item.StartsWith($name) -and $item.Length -gt 2) {
                $values.Add($item.Substring(2))
                break
            }
        }
    }
    return @($values)
}

function Assert-NoReparsePointInPath {
    param([string]$FullPath)

    $current = $FullPath
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw 'Output directories cannot use symlinks or directory junctions.'
            }
        }
        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrWhiteSpace($parent) -or [string]::Equals($parent, $current, [StringComparison]::OrdinalIgnoreCase)) {
            break
        }
        $current = $parent
    }
}

function Assert-OutputPath {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw 'The output directory must be an absolute path.'
    }

    if ($Path.StartsWith('\\') -or $Path.StartsWith('//')) {
        throw 'UNC and device-namespace paths are not permitted as output directories.'
    }

    if (-not [IO.Path]::IsPathFullyQualified($Path)) {
        throw 'The output directory must be an absolute path.'
    }

    $fullPath = [IO.Path]::GetFullPath($Path)
    if ($fullPath -match '(?:^|[\\/])[^\\/]*~\d+(?:$|[\\/])') {
        throw 'Windows 8.3 short paths are not permitted as output directories.'
    }

    $driveRoot = [IO.Path]::GetPathRoot($fullPath)
    if ([string]::Equals($fullPath, $driveRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'A drive root cannot be used as an output directory.'
    }

    Assert-NoReparsePointInPath -FullPath $fullPath

    foreach ($toolRoot in @($protectedRoot, $toolsHome)) {
        $prefix = $toolRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        if ($fullPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
            [string]::Equals($fullPath, $toolRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Downloaded literature cannot be written into the configured protected tool workspace.'
        }
    }

}

function Assert-IntegerRange {
    param(
        [string]$Value,
        [int]$Minimum,
        [int]$Maximum,
        [string]$OptionName
    )

    $number = 0
    if (-not [int]::TryParse($Value, [ref]$number) -or $number -lt $Minimum -or $number -gt $Maximum) {
        throw "$OptionName must be between $Minimum and $Maximum."
    }
}

function Assert-OpenAlexWindowsCompatibilityPatch {
    if ($env:OS -ne 'Windows_NT') {
        return
    }

    $downloaderPath = Join-Path $runtimeRoot 'openalex\.venv\Lib\site-packages\openalex_cli\downloader.py'
    if (-not (Test-Path -LiteralPath $downloaderPath -PathType Leaf)) {
        throw "OpenAlex downloader module is missing: $downloaderPath"
    }

    $source = Get-Content -LiteralPath $downloaderPath -Raw
    if ($source -notmatch 'registered_signals' -or $source -notmatch 'except \(NotImplementedError, RuntimeError\)') {
        throw 'OpenAlex 0.3.3 is missing the required Windows asyncio compatibility patch. Reapply patches\openalex-official-0.3.3-windows-signals.patch.'
    }
}

function Test-OpenAccessFilter {
    param([string[]]$Items)

    $filters = @(Get-OptionValues -Items $Items -Names @('-f', '--filter'))
    if ($filters.Count -eq 0) {
        return $false
    }
    $effectiveFilter = $filters[$filters.Count - 1]
    foreach ($clause in ($effectiveFilter -split ',')) {
        $trimmed = $clause.Trim()
        if ($trimmed -match '^(?i:open_access\.is_oa\s*:\s*true|(?:best_oa_location|primary_location)\.license\s*:\s*(?!null\b|none\b)[^!,\s]+)$') {
            return $true
        }
    }
    return $false
}

function Assert-SafeArguments {
    param([string[]]$Items)

    foreach ($item in $Items) {
        if ($item -match '^(?i:(?:--(?:api[_-]?key|apikey|access[_-]?token|auth|basic[_-]?auth|bearer|cookie|cookies|elsevier[_-]api[_-]key|elsevier[_-]inst[_-]token|header|inst[_-]?token|password|secret|secret[_-]?key|token)|-H))(?:=|$)' -or
            ($item.StartsWith('-H') -and $item.Length -gt 2)) {
            throw 'Credential-bearing command options are disabled; use environment variables or an approved interactive setup.'
        }
        if ($item -match '^(?i:(?:--?)?(?:tor|tor[_-]?port|socks\d?|prox(?:y|ies)|(?:http|https|socks\d?)[_-]?proxy|proxy[_-]?(?:server|pool|rotation)|rotate[_-]?proxies|user[_-]?agent[_-]?rotate))(?:=|$)') {
            throw 'Blocked by policy: Tor and proxy/rotation routes are not permitted.'
        }
    }

    $joined = $Items -join ' '
    if ($joined -match '(?i)(sci[\W_]*hub|sci[\W_]*net|lib[\W_]*gen|library[\W_]*genesis|anna[\x27\u2019]?s[\W_]*archive|z[\W_]*lib(?:rary)?|shadow[\W_]*lib|nexus[\W_]*stc|stc[\W_]*nexus)') {
        throw 'Blocked by policy: Sci-Hub, LibGen, Anna''s Archive, Z-Library, and other shadow-library routes are not permitted.'
    }
}

function Show-Status {
    foreach ($name in $entryPoints.Keys | Sort-Object) {
        $state = if (Test-Path -LiteralPath $entryPoints[$name] -PathType Leaf) { 'installed' } else { 'missing' }
        "{0}: {1}" -f $name, $state
    }

    foreach ($name in @(
        'SCIVERSE_API_TOKEN',
        'OPENALEX_API_KEY',
        'UNPAYWALL_EMAIL',
        'SEMANTIC_SCHOLAR_API_KEY',
        'CORE_API_KEY',
        'ELSEVIER_API_KEY',
        'INST_TOKEN'
    )) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        $state = if ([string]::IsNullOrWhiteSpace($value)) { 'not set' } else { 'set' }
        "env:{0}: {1}" -f $name, $state
    }
}

Assert-SafeArguments -Items $ToolArguments

$allowedTools = @('status', 'paper-search', 'paper-search-mcp', 'openalex', 'instsci', 'instsci-mcp')
if ([string]::IsNullOrWhiteSpace($Tool) -or $Tool -notin $allowedTools) {
    throw "Tool must be one of: $($allowedTools -join ', ')."
}

if ($Tool -eq 'status') {
    if ($ToolArguments.Count -gt 0) {
        throw 'status does not accept arguments.'
    }
    Show-Status
    exit 0
}

$executable = $entryPoints[$Tool]
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Tool entry point is missing: $executable"
}

if ($Tool -eq 'paper-search' -and $ToolArguments.Count -gt 0) {
    $operation = $ToolArguments[0]
    if ($operation -in @('download', 'read')) {
        $outputPaths = @(Get-OptionValues -Items $ToolArguments -Names @('-o', '--save-path'))
        if ($outputPaths.Count -eq 0) {
            throw 'paper-search download/read requires an explicit -o or --save-path output directory.'
        }
        foreach ($outputPath in $outputPaths) {
            Assert-OutputPath -Path $outputPath
        }
    }
}

if ($Tool -eq 'openalex' -and $ToolArguments.Count -gt 0 -and $ToolArguments[0] -eq 'download') {
    Assert-OpenAlexWindowsCompatibilityPatch
    $outputPaths = @(Get-OptionValues -Items $ToolArguments -Names @('-o', '--output'))
    if ($outputPaths.Count -eq 0) {
        throw 'openalex download requires an explicit -o or --output directory.'
    }
    foreach ($outputPath in $outputPaths) {
        Assert-OutputPath -Path $outputPath
    }
    if ((Test-HasOption -Items $ToolArguments -Names @('--content')) -and -not (Test-OpenAccessFilter -Items $ToolArguments)) {
        throw 'OpenAlex PDF/XML content requires an explicit OA or license filter. Use paper-search for DOI-level OA retrieval.'
    }
    $workerValues = @(Get-OptionValues -Items $ToolArguments -Names @('--workers'))
    if ($workerValues.Count -eq 0) {
        $ToolArguments += @('--workers', '4')
    } else {
        foreach ($workerValue in $workerValues) {
            Assert-IntegerRange -Value $workerValue -Minimum 1 -Maximum 4 -OptionName '--workers'
        }
    }
}

if ($Tool -in @('instsci', 'instsci-mcp')) {
    $browserCache = Join-Path $sharedState 'instsci\cloakbrowser'
    if (-not (Test-Path -LiteralPath $browserCache -PathType Container)) {
        throw "InstSci browser cache is missing: $browserCache"
    }
    $env:INSTSCI_CLOAKBROWSER_CACHE_DIR = $browserCache
    $env:CLOAKBROWSER_CACHE_DIR = $browserCache
    $env:PYTHONUTF8 = '1'
}

if ($Tool -eq 'instsci' -and $ToolArguments.Count -gt 0) {
    $operation = $ToolArguments[0]
    if ($operation -in @('fetch', 'batch', 'papers', 'publisher-batch', 'est-batch')) {
        $outputPaths = @(Get-OptionValues -Items $ToolArguments -Names @('-o', '--output'))
        if ($outputPaths.Count -eq 0) {
            throw 'InstSci acquisition commands require an explicit -o or --output directory.'
        }
        foreach ($outputPath in $outputPaths) {
            Assert-OutputPath -Path $outputPath
        }
        $concurrencyValues = @(Get-OptionValues -Items $ToolArguments -Names @('-j', '--concurrency'))
        foreach ($concurrencyValue in $concurrencyValues) {
            Assert-IntegerRange -Value $concurrencyValue -Minimum 1 -Maximum 2 -OptionName '--concurrency'
        }
    }
    if ($operation -in @('batch', 'papers', 'publisher-batch', 'est-batch') -and -not (Test-HasOption -Items $ToolArguments -Names @('--broker', '--no-broker'))) {
        $ToolArguments += '--no-broker'
    }
}

& $executable @ToolArguments
exit $LASTEXITCODE
