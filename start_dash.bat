@echo off

REM Запуск FastAPI сервера в отдельном окне
start cmd /k "cd Web && uvicorn main:app --reload"

REM Переход в фронт
cd frontend

REM Запуск React dev server в отдельном окне
start cmd /k "npm run dev"

echo All servers started!
pause