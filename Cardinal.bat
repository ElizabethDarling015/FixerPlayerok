@echo off
chcp 65001 >nul
title PlayerokCardinal
cd /d "%~dp0"

rem ANSI-цвета (Windows 10+ / Windows Terminal)
for /f %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
set "CYAN=%ESC%[96m"
set "RED=%ESC%[91m"
set "GREEN=%ESC%[92m"
set "YELLOW=%ESC%[93m"
set "GREY=%ESC%[90m"
set "BOLD=%ESC%[1m"
set "NC=%ESC%[0m"
set "TAG=%CYAN%[PlayerokCardinal]%NC%"

cls
echo.
echo %CYAN% ██████╗ ██╗      █████╗ ██╗   ██╗███████╗██████╗  ██████╗ ██╗  ██╗%NC%
echo %CYAN% ██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝%NC%
echo %CYAN% ██████╔╝██║     ███████║ ╚████╔╝ █████╗  ██████╔╝██║   ██║█████╔╝%NC%
echo %CYAN% ██╔═══╝ ██║     ██╔══██║  ╚██╔╝  ██╔══╝  ██╔══██╗██║   ██║██╔═██╗%NC%
echo %CYAN% ██║     ███████╗██║  ██║   ██║   ███████╗██║  ██║╚██████╔╝██║  ██╗%NC%
echo %CYAN% ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝%NC%
echo.
echo %RED%      ██████╗ █████╗ ██████╗ ██████╗ ██╗███╗   ██╗ █████╗ ██╗%NC%
echo %RED%     ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔══██╗██║%NC%
echo %RED%     ██║     ███████║██████╔╝██║  ██║██║██╔██╗ ██║███████║██║%NC%
echo %RED%     ██║     ██╔══██║██╔══██╗██║  ██║██║██║╚██╗██║██╔══██║██║%NC%
echo %RED%     ╚██████╗██║  ██║██║  ██║██████╔╝██║██║ ╚████║██║  ██║███████╗%NC%
echo %RED%      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝%NC%
echo.
echo   %GREY%бот-комбайн для продавцов Playerok  ·  /menu в Telegram%NC%
echo   %GREY%Создатель:%NC% %CYAN%https://t.me/Scwee_xz%NC%
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
    echo %TAG% %RED%✖%NC%  Python 3.11+ не найден.
    echo      Скачайте его с https://www.python.org/downloads/ и при установке
    echo      обязательно отметьте галочку "Add Python to PATH".
    pause
    exit /b 1
)
echo %TAG% %GREEN%✓%NC% Python найден.

rem --- 2. Виртуальное окружение (создаётся один раз) ---
if not exist ".venv\Scripts\python.exe" (
    echo %TAG% %CYAN%›%NC% Создаю виртуальное окружение .venv…
    %PY_CMD% -m venv .venv || (echo %TAG% %RED%✖%NC% Не удалось создать .venv & pause & exit /b 1)
    echo %TAG% %GREEN%✓%NC% Виртуальное окружение создано.
)

rem --- 3. Зависимости (ставятся при первом запуске или если чего-то не хватает) ---
".venv\Scripts\python.exe" -c "import aiogram, playerokapi" >nul 2>&1
if errorlevel 1 (
    echo %TAG% %CYAN%›%NC% Ставлю зависимости (pip install -e ".[cardinal]")…
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q >nul
    ".venv\Scripts\python.exe" -m pip install -e ".[cardinal]" -q || (echo %TAG% %RED%✖%NC% Не удалось установить зависимости & pause & exit /b 1)
    echo %TAG% %GREEN%✓%NC% Зависимости установлены.
) else (
    echo %TAG% %GREEN%✓%NC% Зависимости на месте.
)

rem --- 4. Запуск (при отсутствии конфигов откроется мастер настройки) ---
if not exist "configs\main.toml" (
    echo %TAG% %YELLOW%!%NC% Конфигов ещё нет — сейчас откроется мастер первичной настройки.
)
echo %TAG% %CYAN%›%NC% Запускаю PlayerokCardinal…
echo   %GREY%Создатель:%NC% %CYAN%https://t.me/Scwee_xz%NC%
echo.
".venv\Scripts\python.exe" -m cardinal
pause
