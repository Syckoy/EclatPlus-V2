@echo off
setlocal
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" (
  echo Python 3.12 introuvable. Installe-le puis relance.
  exit /b 1
)
"%PY%" -m pip install --disable-pip-version-check -q pyinstaller
"%PY%" -m PyInstaller --noconfirm --clean --onefile --noconsole --name EclatPlus --distpath dist --workpath build --specpath build eclatplus.py
echo.
echo EXE: %~dp0dist\EclatPlus.exe
