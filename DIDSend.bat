@echo off
CALL %~dp0\SetEnv.bat

:: Exécuter le script Python
::CALL %PythonTool% DIDSend.py
CALL %PythonTool% DIDParseFileAndSend.py

exit /b 0