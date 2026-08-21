@echo off
REM Run the headless backtest on Windows using tester.ini.
REM
REM MT5 refuses a second instance on the same data directory, so close the GUI
REM terminal first. tester.ini sets ShutdownTerminal=1, so this exits on its own.

setlocal
if "%MT5_DIR%"=="" set MT5_DIR=C:\Program Files\MetaTrader 5
if "%~1"=="" (set CFG=tester.ini) else (set CFG=%~1)

copy /y "%~dp0..\%CFG%" "%MT5_DIR%\%CFG%" >nul || (echo Could not copy %CFG% & exit /b 1)

pushd "%MT5_DIR%" || (echo Cannot find %MT5_DIR% -- set MT5_DIR & exit /b 1)
"%MT5_DIR%\terminal64.exe" /config:%CFG%
popd

echo.
echo Trade log: %%APPDATA%%\MetaQuotes\Terminal\Common\Files\ORB_*_tester.csv
echo Analyse with:  set MT5_COMMON=%%APPDATA%%\MetaQuotes\Terminal\Common\Files
endlocal
