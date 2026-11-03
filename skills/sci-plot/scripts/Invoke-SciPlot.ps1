#requires -Version 7.0
param(
    [string]$Python,
    [Parameter(Position=0, ValueFromRemainingArguments=$true)]
    [string[]]$CommandArgs
)
$ErrorActionPreference = 'Stop'
if (-not $Python) { $Python = $env:SCI_PLOT_PYTHON }
$runtime = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'scientific-plotting.runtime.json'
if (-not $Python -and (Test-Path -LiteralPath $runtime)) {
    $Python = (Get-Content -LiteralPath $runtime -Raw | ConvertFrom-Json).python_executable
}
if (-not $Python) { $Python = (Get-Command python -ErrorAction Stop).Source }
if (-not $CommandArgs) { $CommandArgs = @('doctor') }
& $Python -B (Join-Path $PSScriptRoot 'run_sci_plot.py') @CommandArgs
exit $LASTEXITCODE
