# Gera o programa (dist\EcoGuard\EcoGuard.exe) e o instalador (instalador\Instalar-EcoGuard.exe).
# Rode na raiz do projeto:  powershell -ExecutionPolicy Bypass -File tools\gerar_exe.ps1
# Com -Publicar, também cria a release v<versão> no GitHub: os programas já instalados avisam que há versão nova.
param([switch]$Publicar)
$ErrorActionPreference = "Stop"
$versao = (.\.venv\Scripts\python.exe -c "from versao import VERSAO; print(VERSAO)").Trim()
Write-Host "Versão $versao"
.\.venv\Scripts\python.exe tools\gerar_icones.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean EcoGuard.spec
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Instale o Inno Setup: winget install JRSoftware.InnoSetup" }
& $iscc "/DVersao=$versao" tools\instalador.iss
Write-Host "Pronto: instalador\Instalar-EcoGuard.exe"
if ($Publicar) {
    gh release create "v$versao" instalador\Instalar-EcoGuard.exe --title "EcoGuard $versao" --notes "Instalador do EcoGuard $versao. Rodar por cima da versão instalada atualiza o programa e mantém os dados."
}
