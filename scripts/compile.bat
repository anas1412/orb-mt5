@echo off
REM Compile ORB.mq5 on Windows.
REM
REM MetaEditor needs a path RELATIVE to the terminal directory and you must be
REM standing in that directory -- an absolute C:\... path makes it exit silently
REM with no .ex5 and no log. It also returns exit code 1 on a clean compile, so
REM judge success by the log's "0 errors, 0 warnings" line, never by errorlevel.

setlocal
if "%MT5_DIR%"=="" set MT5_DIR=C:\Program Files\MetaTrader 5
if "%~1"=="" (set TARGET=MQL5\Experts\ORB.mq5) else (set TARGET=%~1)

pushd "%MT5_DIR%" || (echo Cannot find %MT5_DIR% -- set MT5_DIR & exit /b 1)
"%MT5_DIR%\MetaEditor64.exe" /compile:"%TARGET%" /log
popd

echo.
echo Compile log sits next to the source, UTF-16LE. Check the last line:
echo   type "%MT5_DIR%\%TARGET:.mq5=.log%"
endlocal
