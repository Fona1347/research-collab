[CmdletBinding()]
param(
    [string]$PythonCommand = "python",
    [string]$QuickValidatePath
)

$ErrorActionPreference = "Stop"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$skillRoot = Join-Path $repoRoot "skills\sciverse-research"

$requiredFiles = @(
    "SKILL.md",
    "agents\openai.yaml",
    "references\sciverse-api.md",
    "references\sciverse-paper-schema.md",
    "references\sciverse-codex-user-guide.md",
    "references\sciverse-validation-test.md",
    "references\mcp-upgrade-notes.md"
)

foreach ($relativePath in $requiredFiles) {
    $fullPath = Join-Path $skillRoot $relativePath
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        throw "Required Skill file is missing: $relativePath"
    }
}

if (-not $QuickValidatePath) {
    $QuickValidatePath = Join-Path $env:USERPROFILE ".codex\skills\.system\skill-creator\scripts\quick_validate.py"
}

if (-not (Test-Path -LiteralPath $QuickValidatePath -PathType Leaf)) {
    throw "skill-creator quick_validate.py was not found: $QuickValidatePath"
}

& $PythonCommand $QuickValidatePath $skillRoot
if ($LASTEXITCODE -ne 0) {
    throw "skill-creator validation failed."
}

$jsonFiles = @(
    (Join-Path $repoRoot "docs\components\sciverse-research\sciverse-skill.json"),
    (Join-Path $repoRoot "contracts\sciverse-research\evidence-record.schema.json"),
    (Join-Path $repoRoot "tests\sciverse-research\routing-cases.json")
)

foreach ($jsonFile in $jsonFiles) {
    try {
        Get-Content -Raw -LiteralPath $jsonFile | ConvertFrom-Json | Out-Null
    }
    catch {
        throw "Invalid JSON: $jsonFile"
    }
}

$skillText = Get-Content -Raw -LiteralPath (Join-Path $skillRoot "SKILL.md")
$referenceMatches = [regex]::Matches($skillText, 'references/([A-Za-z0-9._-]+\.md)')
foreach ($match in $referenceMatches) {
    $referencePath = Join-Path $skillRoot ("references\" + $match.Groups[1].Value)
    if (-not (Test-Path -LiteralPath $referencePath -PathType Leaf)) {
        throw "SKILL.md references a missing file: $($match.Groups[1].Value)"
    }
}

$openAiYaml = Get-Content -Raw -LiteralPath (Join-Path $skillRoot "agents\openai.yaml")
if ($openAiYaml -notmatch '\$sciverse-research') {
    throw "agents/openai.yaml default_prompt must mention `$sciverse-research."
}

$tokenLikeMatches = Get-ChildItem -LiteralPath $skillRoot -Recurse -File |
    Where-Object { $_.FullName -notmatch '[\\/]\.git[\\/]' } |
    Select-String -Pattern 'sv-[A-Za-z0-9]{8,}' -CaseSensitive

if ($tokenLikeMatches) {
    throw "Potential Sciverse token-like value found in repository content."
}

& $PythonCommand (Join-Path $PSScriptRoot "check_contracts.py")
if ($LASTEXITCODE -ne 0) {
    throw "Portable routing/contract validation failed."
}

Write-Output "Validation passed: $skillRoot"
