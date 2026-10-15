@echo off
REM Tira uma foto do Spot no Isaac Sim usando o Python do ambiente conda C:\isaac-env.
REM Argumentos extras sao repassados ao script (ex.: run_photo.bat --gui)
set OMNI_KIT_ACCEPT_EULA=YES
C:\isaac-env\python.exe "%~dp0spot_photo.py" %*
