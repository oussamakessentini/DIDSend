@echo off
set FILE_PATH=%~dp0..\BmsGen2_Copy\Tools\__SetEnv.bat

IF EXIST "%FILE_PATH%" (
    %FILE_PATH%
    set PythonTool="python"
    echo PATH=%~dp0.;%PATH%
) ELSE (
    echo File not found: %FILE_PATH%
    SET PythonTool="%~dp0..\PR105\TBMU_MAIN\ToolFiles\Utils\Python\run.bat"
)