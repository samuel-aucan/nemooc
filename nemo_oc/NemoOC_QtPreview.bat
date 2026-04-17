@echo off
cd /d "%~dp0"
set NEMOOC_QT_SKIP_LOGIN=1
python app_qt/main.py
