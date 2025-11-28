Write-Host "Starting Droplet Analyzer (Flask) on http://localhost:5000"

if (Test-Path -Path ".\.venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment .venv"
    . .\.venv\Scripts\Activate.ps1
}

$env:FLASK_APP = "app.py"
python app.py