param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Cannot find venv python at $Python"
}

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $Python -m experiments.rag_reproduction.raglab.cli @Args
$exitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
exit $exitCode
