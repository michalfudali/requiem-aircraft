@echo off
title BiPOL Requiem - Server (Python 3.13 + OpenVSP)
cd /d "%~dp0"
echo ========================================================
echo   Uruchamianie serwera BiPOL Requiem (MEiL PW)
echo   Srodowisko: Python 3.13 (.venv) + OpenVSP 3.55.0
echo   Adres lokalny: http://127.0.0.1:5000
echo   Zatrzymanie: Ctrl + C
echo ========================================================
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    py -3.13 app.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Proba uruchomienia przez 'py -3.11 app.py'...
    py -3.11 app.py
    if %ERRORLEVEL% NEQ 0 (
        echo Proba uruchomienia przez 'python app.py'...
        python app.py
        if %ERRORLEVEL% NEQ 0 (
            echo.
            echo [BLAD] Nie udalo sie uruchomic aplikacji.
            echo Upewnij sie, ze Python oraz zaleznosci sa zainstalowane:
            echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
        )
    )
)
pause
