@echo off
setlocal
REM Cambia la directory corrente in quella in cui si trova questo file .bat
cd /d %~dp0
REM Esegue lo script Python dell'interfaccia grafica
echo Avvio di License Manager...
python.exe license_manager.py
endlocal
pause
