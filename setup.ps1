# ==============================================================================
# Hermes Brain — PowerShell Installer Wrapper
# ==============================================================================
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Error "[ERROR] Python 3 is required but was not found in PATH."
    exit 1
}

& $pythonCmd.Source "$scriptDir\install.py" $args
