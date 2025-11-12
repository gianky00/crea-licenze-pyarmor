@echo off
setlocal
REM Cambia la directory corrente in quella in cui si trova questo file .bat
cd /d %~dp0
REM Esegue lo script Python dell'interfaccia grafica
echo Avvio di Obfuscator Generale...
python.exe obfuscator_generale.py
endlocal
pause
