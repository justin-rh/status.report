@ECHO OFF
REM StatusReport -- One-command build script
REM Run from the repo root. Requires Python 3.12 venv at .venv\
REM After build: copy dist\status_report\ to the USB flash drive.
REM
REM CALL is required before both activate.bat and pyinstaller.
REM Without CALL, the batch file exits after the first command returns.
REM See: github.com/orgs/pyinstaller/discussions/7084

ECHO Activating virtual environment...
CALL .venv\Scripts\activate.bat

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Failed to activate virtual environment.
    ECHO Make sure .venv\ exists: python -m venv .venv
    EXIT /B 1
)

ECHO Building status_report with PyInstaller...
CALL pyinstaller status_report.spec --noconfirm

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] PyInstaller build failed. Check output above.
    EXIT /B %ERRORLEVEL%
)

ECHO.
ECHO Build complete. Distributable is in: dist\status_report_v2.1\
ECHO Copy dist\status_report_v2.1\ to the USB flash drive.
