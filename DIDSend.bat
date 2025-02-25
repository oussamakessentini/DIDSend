@echo off
call %~dp0..\..\__SetEnv.bat

:: Exécuter le script Python
python DIDSend.py

pause
exit /b 0