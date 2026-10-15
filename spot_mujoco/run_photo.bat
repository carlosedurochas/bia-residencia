@echo off
REM Tira uma foto do Spot no MuJoCo usando o Python do ambiente conda C:\mujoco-env.
REM Argumentos extras sao repassados ao script (ex.: run_photo.bat --gui)
C:\mujoco-env\python.exe "%~dp0spot_photo.py" %*
