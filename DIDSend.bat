@echo off
::call %~dp0..\..\__SetEnv.bat
SET PythonTool="%~dp0..\..\..\Utils\python\run.bat"

:: Exécuter le script Python
CALL %PythonTool% DIDSend.py

pause
exit /b 0