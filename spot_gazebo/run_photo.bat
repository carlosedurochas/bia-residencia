@echo off
REM Tira a foto do Spot no Gazebo Harmonic, que roda dentro do WSL2 (distro Ubuntu).
REM   run_photo.bat         salva spot_gazebo.png
REM   run_photo.bat --gui   abre tambem a interface do Gazebo (a foto e salva ao fechar a janela)
wsl -d Ubuntu --cd "%~dp0" -e bash run_photo.sh %*
