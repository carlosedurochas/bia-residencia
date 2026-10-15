@echo off
REM Tira uma foto do Spot no Webots R2025a (instalado em %LOCALAPPDATA%\Programs\Webots).
REM   run_photo.bat         abre o Webots minimizado, salva spot_webots.png e fecha
REM   run_photo.bat --gui   salva a foto e deixa o Webots aberto
set WEBOTS=%LOCALAPPDATA%\Programs\Webots\msys64\mingw64\bin\webots.exe
set WORLD=%~dp0worlds\spot_photo.wbt

if "%1"=="--gui" (
  set SPOT_PHOTO_KEEP=1
  "%WEBOTS%" --mode=realtime "%WORLD%"
) else (
  "%WEBOTS%" --batch --mode=realtime --minimize --stdout --stderr "%WORLD%"
)
