# Optional Windows launcher. Standard usage is:
#   python -m uvicorn app.main:app --reload --port 8000
#
# Override the interpreter when needed:
#   $env:LEARNING_ASSISTANT_PYTHON = "C:\path\to\python.exe"

$python = $env:LEARNING_ASSISTANT_PYTHON
if (-not $python) {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $python = $venvPython
    } else {
        $python = "python"
    }
}

$sharedSitePackages = Join-Path (Split-Path $PSScriptRoot -Parent) "fastapi-learning\.venv\Lib\site-packages"
if (Test-Path $sharedSitePackages) {
    $env:PYTHONPATH = $sharedSitePackages
}

& $python -m uvicorn app.main:app --reload --port 8000
