@echo off
SET "PythonTool=%~dp0..\PR105\TBMU_MAIN\ToolFiles\utils\Python\run.bat"

:: Exécuter le script Python
CALL %PythonTool% DIDSend.py

exit /b 0