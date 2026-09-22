param(
  [string]$SkillPath = (Join-Path $PSScriptRoot '..\..\skills\zotero-literature-note')
)

$ErrorActionPreference = 'Stop'

$SkillPath = (Resolve-Path -LiteralPath $SkillPath).Path
$SkillParent = Split-Path -Parent $SkillPath
$RepoRoot = Split-Path -Parent $SkillParent
$VersionPath = Join-Path $RepoRoot 'docs\components\zotero-literature-note\VERSION'
$ChangelogPath = Join-Path $RepoRoot 'docs\components\zotero-literature-note\CHANGELOG.md'

foreach ($RequiredRootFile in @($VersionPath, $ChangelogPath)) {
  if (-not (Test-Path -LiteralPath $RequiredRootFile -PathType Leaf)) {
    throw "Missing required release file: $RequiredRootFile"
  }
}

$Version = (Get-Content -Raw -LiteralPath $VersionPath).Trim()
$SemVerPattern = '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$'
if ($Version -notmatch $SemVerPattern -or $Version.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0) {
  throw "VERSION must be a valid SemVer-compatible filename component, found: $Version"
}

$Changelog = Get-Content -Raw -LiteralPath $ChangelogPath
$ChangelogHeadingPattern = "(?m)^##\s+$([regex]::Escape($Version))\s+-\s+\d{4}-\d{2}-\d{2}\s*$"
if ($Changelog -notmatch $ChangelogHeadingPattern) {
  throw "CHANGELOG.md missing dated release heading for VERSION $Version"
}

$Required = @(
  'SKILL.md',
  'agents\openai.yaml',
  'references\workflow.md',
  'references\mineru-cache-policy.md',
  'references\visual-evidence-policy.md',
  'references\pdf-toolchain-appendix.md',
  'references\evidence-policy.md',
  'references\citation-policy.md',
  'references\output-versioning.md',
  'references\prompt-templates.md',
  'references\template-index.md',
  'references\templates\research-standard.md',
  'references\templates\flexible-note.md',
  'references\templates\layered-explainer.md'
)

foreach ($RelativePath in $Required) {
  $Path = Join-Path $SkillPath $RelativePath
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "Missing required file: $RelativePath"
  }
}

$SkillMdPath = Join-Path $SkillPath 'SKILL.md'
$SkillMd = Get-Content -Raw -LiteralPath $SkillMdPath
if ($SkillMd -notmatch '(?s)^---\s*\r?\n(.+?)\r?\n---') {
  throw 'SKILL.md frontmatter is missing or invalid.'
}

$Frontmatter = $Matches[1]
$FrontmatterKeys = @(
  [regex]::Matches($Frontmatter, '(?m)^([A-Za-z0-9_-]+):') |
    ForEach-Object { $_.Groups[1].Value }
)
$UnexpectedKeys = @($FrontmatterKeys | Where-Object { $_ -notin @('name', 'description') })
if ($UnexpectedKeys.Count -gt 0 -or @($FrontmatterKeys | Sort-Object -Unique).Count -ne 2) {
  throw 'SKILL.md frontmatter must contain only name and description.'
}
if ($Frontmatter -notmatch '(?m)^name:\s*zotero-literature-note\s*$') {
  throw 'SKILL.md frontmatter name must be zotero-literature-note.'
}
if ($Frontmatter -notmatch '(?m)^description:\s*\S+') {
  throw 'SKILL.md frontmatter description is missing.'
}

if ((Get-Content -LiteralPath $SkillMdPath).Count -gt 500) {
  throw 'SKILL.md must remain under 500 lines; move details into references.'
}

$OpenAiYaml = Get-Content -Raw -LiteralPath (Join-Path $SkillPath 'agents\openai.yaml')
foreach ($Pattern in @('display_name:', 'short_description:', 'default_prompt:', 'allow_implicit_invocation:')) {
  if ($OpenAiYaml -notmatch [regex]::Escape($Pattern)) {
    throw "agents\openai.yaml missing required field: $Pattern"
  }
}
if ($OpenAiYaml -notmatch 'display_name:\s*"Zotero Literature Note"') {
  throw 'agents\openai.yaml display_name must be Zotero Literature Note.'
}

function Assert-Contains {
  param(
    [string]$RelativePath,
    [string[]]$Patterns
  )

  $Path = Join-Path $SkillPath $RelativePath
  $Text = Get-Content -Raw -LiteralPath $Path
  foreach ($Pattern in $Patterns) {
    if ($Text -notmatch [regex]::Escape($Pattern)) {
      throw "$RelativePath missing required rule phrase: $Pattern"
    }
  }
}

Assert-Contains 'SKILL.md' @(
  'cropped figures or selected key-panel crops',
  'Use rendered full PDF pages only as QA fallback',
  'Do not treat generating a PDF page screenshot as completing visual evidence processing',
  'Visual QA must include actual inspection of the image content'
)

Assert-Contains 'references\visual-evidence-policy.md' @(
  'Figure/Panel Crop Decision Ladder',
  'Crop Acceptance Criteria',
  'Default subdirectories for retained visual assets',
  'Prefer a verified MinerU figure image',
  'render the relevant PDF page at high resolution',
  'crop source',
  'source page',
  'crop kind',
  'inserted/fallback role',
  'fallback page asset',
  'manual/automatic crop note'
)

Assert-Contains 'references\pdf-toolchain-appendix.md' @(
  'Recommended Crop Workflow',
  'Render the relevant PDF page at high resolution',
  'Crop the full figure or selected panel',
  'Visually inspect the crop',
  'Retain the full-page render under `pages/`',
  'PyMuPDF / `fitz` is an acceptable default local tool'
)

Assert-Contains 'references\output-versioning.md' @(
  'Keep cropped figures and inserted panel images at the asset root',
  'Store rendered full pages under `pages/`',
  'Store QA candidates under `qa/`',
  'rejected-but-retained crops under `unused/`',
  'Do not insert rendered full pages into the final note by default'
)

Assert-Contains 'references\templates\layered-explainer.md' @(
  'cropped figure or selected panel crop',
  'rendered full PDF page',
  '<img src="./{note-filename-without-.md}.assets/{figure-file}.png"',
  'fallback 说明'
)

Write-Output "Validated skill package: $SkillPath"
