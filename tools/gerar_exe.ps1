# Gera o programa (dist\EcoGuard\EcoGuard.exe) e o instalador (instalador\Instalar-EcoGuard.exe).
# Rode na raiz do projeto:  powershell -ExecutionPolicy Bypass -File tools\gerar_exe.ps1
$ErrorActionPreference = "Stop"
.\.venv\Scripts\python.exe tools\gerar_icones.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean EcoGuard.spec
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Instale o Inno Setup: winget install JRSoftware.InnoSetup" }
& $iscc tools\instalador.iss
Write-Host "Pronto: instalador\Instalar-EcoGuard.exe"
