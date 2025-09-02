$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir = Join-Path $ProjectRoot "backend"

Set-Location -Path $ProjectRoot
Write-Host "Executing commands from Project Root: $ProjectRoot"

try {
    Write-Host "Locating Poetry virtual environment from '$BackendDir'..."
    $VenvPath = (poetry -C $BackendDir env info --path)
    
    if (-not $VenvPath) {
        Write-Error "Could not find the Poetry virtual environment. Please run 'poetry install' in the '$BackendDir' directory."
        exit 1
    }

    $ActivationScript = Join-Path $VenvPath "Scripts\Activate.ps1"

    if (-not (Test-Path $ActivationScript)) {
        Write-Error "Activation script not found at '$ActivationScript'. The virtual environment may be corrupted."
        exit 1
    }

    Write-Host "Using Venv: $VenvPath"
    Write-Host "Activating environment and running Ruff on the entire project..."
    
    & $ActivationScript; ruff format; ruff check --fix
    
    Write-Host -ForegroundColor Green "✅ Ruff formatting and fixing complete for the entire project."

} catch {
    Write-Error "An error occurred: $_"
    exit 1
}