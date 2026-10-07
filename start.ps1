$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    Write-Host '[DZ] Creating virtual environment...'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -m venv .venv
    } else {
        python -m venv .venv
    }
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

try {
    & .\.venv\Scripts\python.exe -c 'import flask,psutil,mss,cv2,numpy,pyautogui'
} catch {
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}


Write-Host '[DZ] Starting DZ Control at http://127.0.0.1:5000'
Write-Host '[DZ] On first run, choose an admin username; a password will then be generated and printed below.'
& .\.venv\Scripts\python.exe run.py
