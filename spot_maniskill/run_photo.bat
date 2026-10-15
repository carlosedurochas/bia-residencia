@echo off
REM Tira a foto do Spot no ManiSkill3, que roda dentro do WSL2 (distro Ubuntu).
REM Argumentos extras sao repassados ao script (ex.: run_photo.bat --width 1920 --height 1080)
wsl -d Ubuntu --cd "%~dp0" -e bash run_photo.sh %*
