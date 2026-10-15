@echo off
REM Tira uma foto do Spot no Newton usando o Python do ambiente conda C:\newton-env.
REM Argumentos extras sao repassados ao script (ex.: run_photo.bat --gui)
C:\newton-env\python.exe "%~dp0spot_photo.py" %*
