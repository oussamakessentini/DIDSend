@echo off
setlocal enabledelayedexpansion

:: set env val
SET "PythonTool=%~dp0..\..\PR105\TBMU_MAIN\ToolFiles\utils\Python\run.bat"

:: Initialize variables
set "count=0"

:: Find Python scripts that start with a number (0-9)
for /f "delims=" %%f in ('dir /b /on *.py') do (
        set /a count+=1
        set "file!count!=%%f"
)

:: Check if no files were found
if %count%==0 (
    echo No matching Python scripts found!
    pause
    exit /b
)

:: Display menu
echo.
echo Select a Python script to execute:
for /l %%i in (1,1,%count%) do (
    set "filename=!file%%i!"

    rem Check if the filename starts with a number followed by an underscore
    for /f "tokens=1,* delims=_" %%a in ("!filename!") do (
        if "%%a" NEQ "!filename!" set "filename=%%b"
    )

    echo [%%i] !filename!
)

:: Get user choice
set /p "choice=Enter the number of the script to execute: "

:: Validate choice
if not defined file%choice% (
    echo Invalid selection!
    pause
    exit /b
)

:: Execute the selected Python script
echo Running !file%choice%! ...
call %PythonTool% "!file%choice%!"

endlocal
