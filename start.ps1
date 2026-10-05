$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path '.venvScriptspython.exe')) {
    Write-Host '[DZ] Creating virtual environment...'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -m venv .venv
    } else {
        python -m venv .venv
    }
    & ..venvScriptspython.exe -m pip install --upgrade pip
    & ..venvScriptspython.exe -m pip install -r requirements.txt
}

try {
    & ..venvScriptspython.exe -c 'import flask,psutil,mss,cv2,numpy,pyautogui'
} catch {
    & ..venvScriptspython.exe -m pip install -r requirements.txt
}

Write-Host '[DZ] Starting DZ Control at http://127.0.0.1:5000'
Write-Host '[DZ] First-run password is generated securely and printed once by the app'
& ..venvScriptspython.exe run.py
