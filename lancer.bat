@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "SCRIPT=%~dp0eclatplus.py"
set "PY="

call :find_python
if defined PY goto :launch

echo.
echo Python 3.12 (64 bits) n'est pas installe sur ce PC.
echo Il est obligatoire pour lancer EclatPlus.
echo.
choice /C ON /N /M "Telecharger et installer Python maintenant ? [O]ui / [N]on : "
if errorlevel 2 (
  echo.
  echo Installation refusee. EclatPlus ne peut pas s'ouvrir sans Python.
  pause
  exit /b 1
)

call :install_python
call :find_python
if not defined PY (
  echo.
  echo Python n'a pas pu etre installe. Relance lancer.bat ou installe Python 3.12 64 bits.
  pause
  exit /b 1
)

:launch
set "PYW=%PY%"
for %%I in ("%PY%") do (
  if exist "%%~dpIpythonw.exe" set "PYW=%%~dpIpythonw.exe"
)
start "" "%PYW%" "%SCRIPT%" %*
exit /b 0

:find_python
set "PY="
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
  "%ProgramFiles%\Python312\python.exe"
) do (
  if not defined PY if exist "%%~P" (
    "%%~P" -c "import sys,tkinter; raise SystemExit(0 if sys.version_info>=(3,11) and sys.maxsize>2**32 else 1)" 2>nul
    if not errorlevel 1 set "PY=%%~P"
  )
)
if defined PY goto :eof

where py >nul 2>&1
if errorlevel 1 goto :eof
py -3-64 -c "import sys,tkinter; raise SystemExit(0 if sys.version_info>=(3,11) else 1)" 2>nul
if errorlevel 1 goto :eof
for /f "delims=" %%E in ('py -3-64 -c "import sys; print(sys.executable)"') do set "PY=%%E"
goto :eof

:install_python
set "PY_VER=3.12.10"
set "SETUP=%TEMP%\eclatplus-python-%PY_VER%-amd64.exe"
set "URL=https://www.python.org/ftp/python/%PY_VER%/python-%PY_VER%-amd64.exe"
echo.
echo Telechargement de Python %PY_VER%...
curl.exe -L --fail --retry 3 -o "%SETUP%" "%URL%"
if errorlevel 1 (
  echo Echec du telechargement.
  goto :eof
)
echo Installation (une seule fois, pour cet utilisateur)...
"%SETUP%" /passive InstallAllUsers=0 PrependPath=1 Include_tcltk=1 Include_pip=1 Include_launcher=1 Include_test=0 Shortcuts=0 SimpleInstall=1
timeout /t 2 /nobreak >nul
del "%SETUP%" >nul 2>&1
goto :eof
