@echo off
set PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe
start "" "%PYW%" "%~dp0eclatplus.py" %*
