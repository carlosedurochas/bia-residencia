@echo off
REM Executa a simulacao do Spot com o Python do ambiente conda do Isaac Sim.
REM Argumentos extras sao repassados ao script (ex.: run_spot.bat --keyboard)
set OMNI_KIT_ACCEPT_EULA=YES
C:\isaac-env\python.exe "%~dp0spot_sim.py" %*
