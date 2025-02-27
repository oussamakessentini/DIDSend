@echo off
::call %~dp0..\..\__SetEnv.bat
SET PythonTool="%~dp0..\PR105\TBMU_MAIN\ToolFiles\Utils\Python\run.bat"

:: Exécuter le script Python
::CALL %PythonTool% DIDSend.py
CALL %PythonTool% DIDParseFileAndSend.py
exit /b 0