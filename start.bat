@echo off
setlocal
cd /d "%~dp0"

echo === Project-X: starting ===

REM ---- Backend ----
cd backend
if not exist .venv (
  echo Creating Python virtual environment...
  python -m venv .venv || goto :err
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt || goto :err
start "Project-X backend" cmd /k "call .venv\Scripts\activate.bat && uvicorn app.main:app --reload"
cd ..

REM ---- Frontend ----
cd frontend
if not exist node_modules (
  echo Installing frontend packages...
  call npm install || goto :err
)
echo Starting frontend...
call npm run dev
goto :eof

:err
echo.
echo Something went wrong. See the message above.
pause
exit /b 1
