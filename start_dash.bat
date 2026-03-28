@echo off

REM Активируем виртуальное окружение
call .venv\Scripts\activate

REM Запуск FastAPI сервера в отдельном окне
start cmd /k "python -m uvicorn Web.main:app --reload"

REM Переход в фронт
cd frontend

REM Запуск React dev server в отдельном окне
start cmd /k "npm run dev"

echo All servers started!
