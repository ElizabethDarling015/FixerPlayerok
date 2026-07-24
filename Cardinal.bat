@echo off
chcp 65001 >nul
title PlayerokCardinal
cd /d "%~dp0"

echo.
echo  ============================================================
echo    PlayerokCardinal — бот-комбайн для продавцов Playerok
echo    установка + запуск одним файлом
echo  ============================================================
echo.

rem --- 1. Python 3.11+ ---
set "PY_CMD="
for %%V in (3.13 3.12 3.11) do (
    if not defined PY_CMD (
        py -%%V -c "exit()" >nul 2>&1 && set "PY_CMD=py -%%V"
    )
)
if not defined PY_CMD (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1 && set "PY_CMD=python"
)
if not defined PY_CMD (
    echo [ошибка] Python 3.11+ не найден.
    echo Скачайте его с https://www.python.org/downloads/ и при установке
    echo обязательно отметьте галочку "Add Python to PATH".
    pause
    exit /b 1
)
echo [OK] Python найден.

rem --- 2. Виртуальное окружение (создаётся один раз) ---
if not exist ".venv\Scripts\python.exe" (
    echo Создаю виртуальное окружение .venv…
    %PY_CMD% -m venv .venv || (echo [ошибка] Не удалось создать .venv & pause & exit /b 1)
    echo [OK] Виртуальное окружение создано.
)

rem --- 3. Зависимости (ставятся при первом запуске или если чего-то не хватает) ---
".venv\Scripts\python.exe" -c "import aiogram, playerokapi" >nul 2>&1
if errorlevel 1 (
    echo Ставлю зависимости (pip install -e ".[cardinal]")…
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    ".venv\Scripts\python.exe" -m pip install -e ".[cardinal]" -q || (echo [ошибка] Не удалось установить зависимости & pause & exit /b 1)
    echo [OK] Зависимости установлены.
) else (
    echo [OK] Зависимости на месте.
)

rem --- 4. Запуск (при отсутствии конфигов откроется мастер настройки) ---
if not exist "configs\main.toml" (
    echo Конфигов ещё нет — сейчас откроется мастер первичной настройки.
)
echo Запускаю PlayerokCardinal…
echo.
".venv\Scripts\python.exe" -m cardinal
pause
