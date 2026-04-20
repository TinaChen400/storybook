@echo off
setlocal
set "PY=D:\ComfyUI\venv\Scripts\python.exe"
set "APP=D:\Dev\stroybook\pipeline\app.py"
"%PY%" -m streamlit run "%APP%"
endlocal
