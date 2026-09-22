param([Parameter(Mandatory=$true)][string]$RuntimeRoot)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not [IO.Path]::IsPathFullyQualified($RuntimeRoot)) { throw 'RuntimeRoot must be absolute.' }
$python = Join-Path $runtimeRoot 'Scripts\python.exe'
$sitePackages = Join-Path $runtimeRoot 'Lib\site-packages'
$downloader = Join-Path $sitePackages 'openalex_cli\downloader.py'
$patch = Join-Path $PSScriptRoot 'openalex-official-0.3.3-windows-signals.patch'

foreach ($requiredPath in @($python, $downloader, $patch)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required file is missing: $requiredPath"
    }
}

$version = & $python -c "import importlib.metadata as m; print(m.version('openalex-official'))"
if ($LASTEXITCODE -ne 0 -or $version.Trim() -ne '0.3.3') {
    throw "This patch is pinned to openalex-official 0.3.3; found '$($version.Trim())'."
}

$source = Get-Content -LiteralPath $downloader -Raw
if ($source -match 'registered_signals' -and $source -match 'except \(NotImplementedError, RuntimeError\)') {
    'OpenAlex Windows signal patch is already applied.'
    exit 0
}
if ($source -notmatch 'loop\.add_signal_handler\(sig, self\._request_shutdown\)') {
    throw 'The downloader source does not match the expected unpatched 0.3.3 implementation.'
}

$resolvedTarget = [IO.Path]::GetFullPath($downloader)
$resolvedPackageRoot = [IO.Path]::GetFullPath((Join-Path $sitePackages 'openalex_cli'))
if (-not $resolvedTarget.StartsWith("$resolvedPackageRoot\", [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Patch target escaped the OpenAlex package directory.'
}

Push-Location $sitePackages
try {
    & git apply --check --unsafe-paths $patch
    if ($LASTEXITCODE -ne 0) {
        throw 'OpenAlex patch preflight failed.'
    }
}
finally {
    Pop-Location
}

# uv may install package files as hard links into its cache. Replace this one
# directory entry with an independent copy before patching so the cache remains pristine.
$replacement = "$resolvedTarget.codex-replacement"
if (Test-Path -LiteralPath $replacement) {
    throw "Unexpected replacement file already exists: $replacement"
}
Copy-Item -LiteralPath $resolvedTarget -Destination $replacement
Remove-Item -LiteralPath $resolvedTarget
Move-Item -LiteralPath $replacement -Destination $resolvedTarget

Push-Location $sitePackages
try {
    & git apply --unsafe-paths $patch
    if ($LASTEXITCODE -ne 0) {
        throw 'OpenAlex patch application failed.'
    }
}
finally {
    Pop-Location
}

$patchedSource = Get-Content -LiteralPath $downloader -Raw
if ($patchedSource -notmatch 'registered_signals' -or $patchedSource -notmatch 'except \(NotImplementedError, RuntimeError\)') {
    throw 'OpenAlex patch verification failed.'
}

'OpenAlex Windows signal patch applied successfully.'
