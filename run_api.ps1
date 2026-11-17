# Start API with anaconda Python + fastapi-learning site-packages.
# Build the path from PSScriptRoot so Windows PowerShell's ANSI script
# decoding cannot corrupt the Chinese workspace path.
$fastapiSitePackages = Join-Path (Split-Path $PSScriptRoot -Parent) "fastapi-learning\.venv\Lib\site-packages"
$env:PYTHONPATH = $fastapiSitePackages
& "python" -m uvicorn app.main:app --reload --port 8000