@echo off
REM Tira a foto do Spot no Genesis, que roda dentro do WSL2 (distro Ubuntu).
REM Argumentos extras sao repassados ao script (ex.: run_photo.bat --gui)
wsl -d Ubuntu --cd "%~dp0" -e bash run_photo.sh %*
