Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$wrapper = Join-Path $PSScriptRoot '..\..\skills\literature-fulltext-acquisition\scripts\literature-tools.ps1'
$neverCreatedOutput = Join-Path ([IO.Path]::GetTempPath()) ('literature-smoke-' + [Guid]::NewGuid().ToString('N'))

& $wrapper status
& $wrapper paper-search --help | Out-Null
& $wrapper openalex --help | Out-Null
& $wrapper instsci --help | Out-Null

try {
    & $wrapper paper-search download arxiv 0000.00000
    throw 'Expected the paper-search output-directory guard to fail.'
}
catch {
    if ($_.Exception.Message -notmatch 'explicit.*output') {
        throw
    }
}

try {
    & $wrapper openalex download --ids W2741809807 --content pdf -o $neverCreatedOutput
    throw 'Expected the OpenAlex OA-filter guard to fail.'
}
catch {
    if ($_.Exception.Message -notmatch 'OA or license filter') {
        throw
    }
}

try {
    & $wrapper instsci papers .\dois.txt
    throw 'Expected the InstSci output-directory guard to fail.'
}
catch {
    if ($_.Exception.Message -notmatch 'explicit.*output') {
        throw
    }
}

try {
    & $wrapper paper-search download arxiv 0000.00000 -o (Join-Path $env:LITERATURE_PROTECTED_ROOT 'downloads')
    throw 'Expected the shared-tool-tree output guard to fail.'
}
catch {
    if ($_.Exception.Message -notmatch 'cannot be written into the configured protected tool workspace') {
        throw
    }
}

$secretMarker = 'SMOKE_SECRET_MUST_NOT_APPEAR_94F12A'
try {
    & $wrapper openalex status --api-key $secretMarker
    throw 'Expected the command-line credential guard to fail.'
}
catch {
    if ($_.Exception.Message -notmatch 'Credential-bearing' -or $_.Exception.Message -match $secretMarker) {
        throw
    }
}

try {
    & $wrapper paper-search search 'sci-hub fallback'
    throw 'Expected the prohibited-route guard to fail.'
}
catch {
    if ($_.Exception.Message -notmatch 'Blocked by policy') {
        throw
    }
}

try {
    & $wrapper openalex download --ids W2741809807 --workers 5 -o $neverCreatedOutput
    throw 'Expected the OpenAlex worker cap to fail.'
}
catch {
    if ($_.Exception.Message -notmatch '--workers must be between 1 and 4') {
        throw
    }
}

try {
    & $wrapper instsci papers .\dois.txt --concurrency 3 --output $neverCreatedOutput
    throw 'Expected the InstSci concurrency cap to fail.'
}
catch {
    if ($_.Exception.Message -notmatch '--concurrency must be between 1 and 2') {
        throw
    }
}

if (Test-Path -LiteralPath $neverCreatedOutput) {
    throw 'A guard-only smoke test unexpectedly created an output directory.'
}

'SMOKE_OK'
