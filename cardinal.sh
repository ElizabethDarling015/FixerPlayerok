#!/usr/bin/env bash
#
# PlayerokCardinal — установка, настройка и запуск одним скриптом (Linux/macOS).
# Достаточно закинуть проект на чистый сервер и запустить: Python 3.11+ поставится
# автоматически (apt/dnf/pacman/apk/zypper/brew), дальше venv, зависимости, настройка, запуск.
#
#   ./cardinal.sh            первый запуск: установка + настройка + запуск бота
#   ./cardinal.sh --setup    заново пройти настройку (перезапишет configs/main.toml)
#   ./cardinal.sh --check    проверить токен и авторизацию на Playerok (бота не запускает)
#   ./cardinal.sh --update   принудительно обновить зависимости и запустить
#   ./cardinal.sh --service  установить systemd-сервис автозапуска (Linux)
#   ./cardinal.sh --help     справка
#
# Идемпотентный: повторный запуск ничего не ломает и не трогает конфиги.
#
set -euo pipefail
cd "$(dirname "$0")"

# ----------------------------------------------------------------------
# Цвета (стиль FunPayCardinal: яркие красный/циан + мигающие фиолетовые рамки)
# ----------------------------------------------------------------------
if [ -t 1 ]; then
    RED=$'\033[1;91m'; MAGENTA=$'\033[1;35m'; CYAN=$'\033[1;96m'; BOLD=$'\033[1m'
    GREEN=$'\033[1;92m'; YELLOW=$'\033[1;93m'; GREY=$'\033[0;90m'; NC=$'\033[0m'
    PURPLE=$'\033[5;35m'
else
    RED=""; MAGENTA=""; CYAN=""; BOLD=""; GREEN=""; YELLOW=""; GREY=""; NC=""; PURPLE=""
fi

FRAME="################################################################################"

say()  { echo "${CYAN}[PlayerokCardinal]${NC} $*"; }
ok()   { echo "${GREEN}  ✔${NC} $*"; }
warn() { echo "${YELLOW}  !${NC} $*"; }
die()  {
    echo >&2
    echo "${PURPLE}${FRAME}${NC}" >&2
    echo "${RED}Произошла ошибка: $*${NC}" >&2
    echo "${PURPLE}${FRAME}${NC}" >&2
    exit 2
}
step() {
    echo
    echo "${PURPLE}${FRAME}${NC}"
    echo "$*"
    echo "${PURPLE}${FRAME}${NC}"
}

# Вопрос с необязательным значением по умолчанию → ответ в $REPLY (EOF → ASK_EOF=1).
ASK_EOF=0
ask() {
    local prompt="${CYAN}  ❯${NC} ${BOLD}$1${NC}"
    if [ -n "${2:-}" ]; then prompt="$prompt ${GREY}[$2]${NC}"; fi
    read -r -p "$prompt: " REPLY || { REPLY=""; ASK_EOF=1; }
    REPLY="${REPLY:-${2:-}}"
}

# Вопрос да/нет → в $REPLY "true"/"false" (для TOML).
ask_yn() {
    local default="${2:-n}" hint="[y/N]"
    if [ "$default" = "y" ]; then hint="[Y/n]"; fi
    read -r -p "${CYAN}  ❯${NC} ${BOLD}$1${NC} ${GREY}$hint${NC} " REPLY || REPLY=""
    REPLY="${REPLY:-$default}"
    case "$REPLY" in y|Y|yes|Yes|д|Д|да|Да) REPLY="true" ;; *) REPLY="false" ;; esac
}

# Экранирование значения для TOML-строки в двойных кавычках.
esc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

banner() {
    echo "${CYAN}"
    cat <<'EOF'
 ██████╗ ██╗      █████╗ ██╗   ██╗███████╗██████╗  ██████╗ ██╗  ██╗
 ██╔══██╗██║     ██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗██╔═══██╗██║ ██╔╝
 ██████╔╝██║     ███████║ ╚████╔╝ █████╗  ██████╔╝██║   ██║█████╔╝
 ██╔═══╝ ██║     ██╔══██║  ╚██╔╝  ██╔══╝  ██╔══██╗██║   ██║██╔═██╗
 ██║     ███████╗██║  ██║   ██║   ███████╗██║  ██║╚██████╔╝██║  ██╗
 ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝
EOF
    echo "${RED}"
    cat <<'EOF'
      ██████╗ █████╗ ██████╗ ██████╗ ██╗███╗   ██╗ █████╗ ██╗
     ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔══██╗██║
     ██║     ███████║██████╔╝██║  ██║██║██╔██╗ ██║███████║██║
     ██║     ██╔══██║██╔══██╗██║  ██║██║██║╚██╗██║██╔══██║██║
     ╚██████╗██║  ██║██║  ██║██████╔╝██║██║ ╚████║██║  ██║███████╗
      ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝
EOF
    echo "${NC}"
    echo "${RED} * Проект ${CYAN}PlayerokCardinal — бот-комбайн для продавцов Playerok${NC}"
    echo "${RED} * Панель ${CYAN}Telegram-бот → /menu${NC}"
    echo
}

usage() {
    banner
    sed -n 's/^#   //p' "$0"
    exit 0
}

MODE="run"; FORCE_SETUP=0
case "${1:-}" in
    --help|-h)  usage ;;
    --setup)    FORCE_SETUP=1 ;;
    --check)    MODE="check" ;;
    --update)   MODE="update" ;;
    --service)  MODE="service" ;;
    "")         ;;
    *)          die "Неизвестный аргумент: $1 (см. ./cardinal.sh --help)" ;;
esac

# Как в FunPayCardinal: чистый экран → логотип → ссылки.
[ -t 1 ] && clear
banner

# ----------------------------------------------------------------------
# Мастер настройки: пишет configs/main.toml (+ пустые autoresponse/autodelivery)
# ----------------------------------------------------------------------
setup_config() {
    say "Ответьте на вопросы — конфиги будут созданы автоматически."
    say "Потом всё можно поменять в ${BOLD}configs/${NC} или через Telegram-панель (/menu)."

    # --- 1. Playerok ---
    echo
    echo "${BOLD}  1. Аккаунт Playerok${NC}"
    echo "${GREY}  Cookies: браузер → DevTools (F12) → Network → любой запрос к playerok.com →"
    echo "  заголовок Cookie. Можно вставить и просто значение куки token (eyJ...) без token=.${NC}"
    COOKIES=""
    while true; do
        ask "Cookies или значение token"
        # Обрезаем пробелы/переводы строк по краям (частый артефакт копипаста).
        COOKIES=$(printf '%s' "$REPLY" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        case "$COOKIES" in
            *token=*)
                ;;
            ""|*"="*|*";"*)
                # Пусто либо похоже на строку cookies, но без token= — просим ещё раз.
                [ "$ASK_EOF" = "1" ] && die "Ввод прерван — настройка не завершена."
                warn "Не похоже ни на cookies с ${BOLD}token=${NC}, ни на значение токена — попробуйте ещё раз."
                continue ;;
            *)
                # Голое значение токена (обычно JWT eyJ...) — оборачиваем сами.
                COOKIES="token=$COOKIES" ;;
        esac
        # Локальная проверка токена: JWT из 3 частей, расшифровывается, не просрочен.
        # Обрезанный при вставке токен сервер Playerok встречает ошибкой 500.
        if TOKEN_WARN=$("$PYTHON" - "$COOKIES" <<'PYEOF'
import base64, json, sys, time
cookies = sys.argv[1]
token = next((p.split("=", 1)[1].strip() for p in cookies.split(";") if p.strip().startswith("token=")), "")
parts = token.split(".")
if len(parts) != 3:
    print(f"token не похож на JWT (частей: {len(parts)} вместо 3, длина: {len(token)}) — похоже, вставился не целиком")
    sys.exit(1)
try:
    payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
except Exception:
    print("не удалось расшифровать token — возможно, он повреждён")
    sys.exit(1)
exp = payload.get("exp")
if isinstance(exp, (int, float)) and exp < time.time():
    print("token просрочен — зайдите на playerok.com и скопируйте свежий")
    sys.exit(1)
PYEOF
        ); then
            break
        fi
        warn "Проверка токена: $TOKEN_WARN"
        ask_yn "Использовать этот token всё равно?" n
        [ "$REPLY" = "true" ] && break
    done
    ok "Cookies приняты."
    case "$COOKIES" in
        *__ddg5_*) ;;
        *) warn "Куки ${BOLD}__ddg5_${NC} нет — пробуем без неё (обычно хватает имитации Chrome)." ;;
    esac
    ask "User-Agent браузера ${GREY}(Enter — стандартный Chrome)${NC}" ""
    USER_AGENT="$REPLY"
    ask "Прокси, формат http://user:pass@host:port ${GREY}(Enter — без прокси)${NC}" ""
    PROXY="$REPLY"
    if [ -n "$PROXY" ]; then
        case "$PROXY" in
            http://*|https://*|socks5://*|socks4://*) ok "Прокси: $PROXY" ;;
            *) warn "Прокси не похож на URL (ожидается http://... или socks5://...) — записал как есть." ;;
        esac
    fi

    # --- 2. Telegram ---
    echo
    echo "${BOLD}  2. Telegram-бот (панель управления и уведомления)${NC}"
    echo "${GREY}  Создайте бота у @BotFather и вставьте токен. Enter — работать без Telegram.${NC}"
    ask "Токен TG-бота" ""
    TG_TOKEN="$REPLY"
    ADMIN_IDS="[]"
    if [ -n "$TG_TOKEN" ]; then
        case "$TG_TOKEN" in
            *:*) ok "Токен принят." ;;
            *)   warn "Токен выглядит подозрительно (нет ':') — проверьте его." ;;
        esac
        ask "ID админов через запятую ${GREY}(Enter — привязка секретным кодом из консоли)${NC}" ""
        ids=$(printf '%s' "$REPLY" | tr -cd '0-9,')
        ids=$(printf '%s' "$ids" | sed -e 's/,,*/,/g' -e 's/^,//' -e 's/,$//' -e 's/,/, /g')
        ADMIN_IDS="[$ids]"
        if [ "$ADMIN_IDS" = "[]" ]; then
            warn "Админы не заданы — при старте бот напечатает код привязки в консоль."
        else
            ok "Админы: $ADMIN_IDS"
        fi
    else
        warn "Без Telegram: панель управления и уведомления будут недоступны."
    fi

    # --- 3. Модули ---
    echo
    echo "${BOLD}  3. Модули (всё переключается позже из TG-панели)${NC}"
    ask_yn "Авто-выдача товаров?" y;                    MOD_AUTODELIVERY="$REPLY"
    ask_yn "Автоответчик на команды?" y;                MOD_AUTORESPONSE="$REPLY"
    ask_yn "Приветствие новых покупателей?" n;          MOD_GREETING="$REPLY"
    ask_yn "Автоподнятие лотов (тратит баланс!)?" n;    MOD_AUTORAISE="$REPLY"
    ask_yn "Автовосстановление лотов после продажи?" n; MOD_AUTORESTORE="$REPLY"
    ask_yn "Вечный онлайн?" y;                          MOD_ONLINE="$REPLY"
    ask_yn "Ежедневная сводка в Telegram?" y;           MOD_DIGEST="$REPLY"

    ask "Язык интерфейса (ru/en)" "ru"
    case "$REPLY" in en|EN|En) LANGUAGE="en" ;; *) LANGUAGE="ru" ;; esac

    # --- Запись файлов ---
    mkdir -p configs storage/stock storage/logs
    {
        echo "language = \"$LANGUAGE\""
        echo
        echo "[playerok]"
        echo "cookies = \"$(esc "$COOKIES")\""
        if [ -n "$USER_AGENT" ]; then echo "user_agent = \"$(esc "$USER_AGENT")\""; fi
        if [ -n "$PROXY" ]; then echo "proxy = \"$(esc "$PROXY")\""; fi
        echo
        echo "[telegram]"
        echo "token = \"$(esc "$TG_TOKEN")\""
        echo "admin_ids = $ADMIN_IDS"
        echo
        echo "[modules]"
        echo "autodelivery = $MOD_AUTODELIVERY"
        echo "autoraise = $MOD_AUTORAISE"
        echo "autoresponse = $MOD_AUTORESPONSE"
        echo "autorestore = $MOD_AUTORESTORE"
        echo "greeting = $MOD_GREETING"
        echo "online = $MOD_ONLINE"
        echo "digest = $MOD_DIGEST"
    } > configs/main.toml

    if [ ! -f configs/autoresponse.toml ]; then
        {
            echo "[commands]"
            echo "\"!привет\" = \"Привет, \$username! Чем могу помочь?\""
        } > configs/autoresponse.toml
    fi
    if [ ! -f configs/autodelivery.toml ]; then
        echo "[lots]" > configs/autodelivery.toml
    fi

    echo
    ok "Конфиг создан: ${BOLD}configs/main.toml${NC}"
    ok "Автоответчик:  ${BOLD}configs/autoresponse.toml${NC} (пример команды внутри)"
    ok "Авто-выдача:   ${BOLD}configs/autodelivery.toml${NC} (лоты добавляются из TG-панели)"
}

# ----------------------------------------------------------------------
# Шаг 1/4 — Python 3.11+ (ставится автоматически, если не найден)
# ----------------------------------------------------------------------

# Ищет подходящий интерпретатор → $PYTHON (пусто, если не найден).
find_python() {
    PYTHON=""
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3; do
        if command -v "$candidate" >/dev/null 2>&1 \
           && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            return 0
        fi
    done
    return 1
}

# Определяет дистрибутив → $OS_ID / $OS_LIKE (пусто, если /etc/os-release нет).
detect_os() {
    OS_ID=""; OS_LIKE=""
    if [ -r /etc/os-release ]; then
        OS_ID=$(. /etc/os-release && printf '%s' "${ID:-}")
        OS_LIKE=$(. /etc/os-release && printf '%s' "${ID_LIKE:-}")
    fi
}

# Готовит $SUDO ("" под root, "sudo" иначе; умирает, если sudo нужен, но не установлен).
need_sudo() {
    SUDO=""
    if [ "$(id -u)" != "0" ]; then
        command -v sudo >/dev/null 2>&1 \
            || die "Нужны права root для установки пакетов: запустите скрипт от root или поставьте sudo."
        SUDO="sudo"
    fi
}

# Подключает на Ubuntu репозиторий universe и PPA deadsnakes (там живут pythonX.Y и pythonX.Y-venv).
apt_enable_extra_repos() {
    say "Подключаю репозитории universe и deadsnakes…"
    $SUDO apt-get install -y software-properties-common || true
    $SUDO add-apt-repository -y universe || true
    $SUDO add-apt-repository -y ppa:deadsnakes/ppa || true
    $SUDO apt-get update -y || true
}

# Ставит Python 3.11+ через пакетный менеджер системы (apt/dnf/pacman/apk/zypper/brew).
install_python() {
    say "Python 3.11+ не найден — устанавливаю автоматически…"
    need_sudo

    if [ "$(uname)" = "Darwin" ]; then
        command -v brew >/dev/null 2>&1 \
            || die "На macOS нужен Homebrew (https://brew.sh) или Python с https://python.org — потом запустите ./cardinal.sh снова."
        brew install python@3.12 || die "brew install python@3.12 не удался."
        return 0
    fi

    detect_os
    case " $OS_ID $OS_LIKE " in
        *debian*|*ubuntu*)
            export DEBIAN_FRONTEND=noninteractive
            $SUDO apt-get update -y
            # Штатные пакеты: Debian 12+ / Ubuntu 24.04+ дают Python 3.11+.
            $SUDO apt-get install -y python3 python3-venv python3-pip || true
            if ! find_python; then
                case " $OS_ID $OS_LIKE " in
                    *ubuntu*)
                        # Старая Ubuntu (20.04/22.04): свежий Python из PPA deadsnakes.
                        apt_enable_extra_repos
                        $SUDO apt-get install -y python3.12 python3.12-venv
                        ;;
                    *)
                        die "В репозиториях этой версии Debian нет Python 3.11+ — обновитесь до Debian 12 (bookworm) или поставьте Python вручную."
                        ;;
                esac
            fi
            ;;
        *rhel*|*centos*|*rocky*|*alma*)
            # Ветка ДО fedora: у RHEL-клонов ID_LIKE содержит "fedora", но штатный
            # python3 там старый — ставим версионированный пакет.
            $SUDO dnf install -y python3.12 python3.12-pip \
                || $SUDO dnf install -y python3.11 python3.11-pip
            ;;
        *fedora*)
            $SUDO dnf install -y python3 python3-pip
            ;;
        *arch*)
            $SUDO pacman -Sy --noconfirm python python-pip
            ;;
        *alpine*)
            $SUDO apk add --no-cache python3 py3-pip
            ;;
        *suse*)
            $SUDO zypper --non-interactive install python312 python312-pip \
                || $SUDO zypper --non-interactive install python311 python311-pip
            ;;
        *)
            die "Не удалось определить пакетный менеджер (${OS_ID:-неизвестная ОС}). Установите Python 3.11+ вручную и запустите ./cardinal.sh снова."
            ;;
    esac
}

step "Проверяю Python… (1/4)"
if ! find_python; then
    install_python
    find_python || die "Python установлен, но 3.11+ не появился в PATH — откройте новый терминал или установите вручную."
fi
ok "Python найден: ${BOLD}$($PYTHON --version)${NC}"

# ----------------------------------------------------------------------
# Режим --service: systemd-юнит (только Linux)
# ----------------------------------------------------------------------
if [ "$MODE" = "service" ]; then
    [ "$(uname)" = "Linux" ] || die "systemd-сервис доступен только на Linux."
    command -v systemctl >/dev/null 2>&1 || die "systemctl не найден — система без systemd."
    say "Устанавливаю systemd-сервис (нужны права sudo)…"
    sudo cp "PlayerokCardinal@.service" /etc/systemd/system/PlayerokCardinal@.service
    sudo systemctl daemon-reload
    sudo systemctl enable "PlayerokCardinal@$(whoami).service"
    ok "Сервис установлен. Управление:"
    echo "    ${BOLD}sudo systemctl start PlayerokCardinal@$(whoami)${NC}    # запустить"
    echo "    ${BOLD}sudo systemctl status PlayerokCardinal@$(whoami)${NC}   # статус"
    echo "    ${BOLD}journalctl -u PlayerokCardinal@$(whoami) -f${NC}        # логи"
    warn "Сервис ожидает проект в /home/$(whoami)/PlayerokAPI — поправьте юнит, если папка другая."
    exit 0
fi

# ----------------------------------------------------------------------
# Шаг 2/4 — Настройка (первый запуск или --setup)
# ----------------------------------------------------------------------
step "Первичная настройка… (2/4)"
if [ "$FORCE_SETUP" = "1" ] || [ ! -f "configs/main.toml" ]; then
    setup_config
else
    ok "Конфиги уже есть: ${BOLD}configs/main.toml${NC} ${GREY}(перенастроить: ./cardinal.sh --setup)${NC}"
fi

# ----------------------------------------------------------------------
# Шаг 3/4 — Виртуальное окружение и зависимости
# ----------------------------------------------------------------------

# Пробует создать .venv (тихо); успех — только если внутри работает pip
# (venv без pip — типичный результат падения ensurepip). При неудаче убирает мусор.
create_venv() {
    if "$PYTHON" -m venv .venv 2>/dev/null \
       && [ -x ".venv/bin/python" ] \
       && ".venv/bin/python" -m pip --version >/dev/null 2>&1; then
        return 0
    fi
    rm -rf .venv
    return 1
}

# Ставит pip внутрь готового venv (ensurepip → get-pip.py). 0 — pip работает.
bootstrap_venv_pip() {
    ".venv/bin/python" -m pip --version >/dev/null 2>&1 && return 0
    ".venv/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
    if ! ".venv/bin/python" -m pip --version >/dev/null 2>&1; then
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://bootstrap.pypa.io/get-pip.py | ".venv/bin/python" - || true
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- https://bootstrap.pypa.io/get-pip.py | ".venv/bin/python" - || true
        fi
    fi
    ".venv/bin/python" -m pip --version >/dev/null 2>&1
}

# Создаёт .venv, доставляя всё, чего не хватает: пакет pythonX.Y-venv (с обновлением списков
# и подключением universe/deadsnakes на Ubuntu), в крайнем случае — virtualenv через get-pip.py.
ensure_venv() {
    create_venv && return 0
    need_sudo

    # 1) Debian/Ubuntu: venv — отдельный пакет; списки пакетов на свежем сервере могут быть пустыми.
    if command -v apt-get >/dev/null 2>&1; then
        detect_os
        export DEBIAN_FRONTEND=noninteractive
        say "Доставляю пакет venv для $PYTHON…"
        $SUDO apt-get update -y || true
        $SUDO apt-get install -y "${PYTHON}-venv" || $SUDO apt-get install -y python3-venv || true
        # 2) Не нашлось (частая причина: на минимальной Ubuntu выключен universe,
        #    а для python из deadsnakes нужен его же PPA) — подключаем репозитории и повторяем.
        if ! create_venv; then
            case " ${OS_ID:-} ${OS_LIKE:-} " in
                *ubuntu*)
                    apt_enable_extra_repos
                    $SUDO apt-get install -y "${PYTHON}-venv" || $SUDO apt-get install -y python3-venv || true
                    ;;
            esac
        fi
        create_venv && return 0
    fi

    # 3) Универсальный запасной путь: virtualenv не требует системного ensurepip.
    say "python -m venv недоступен — пробую virtualenv…"
    if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://bootstrap.pypa.io/get-pip.py | $SUDO "$PYTHON" - || true
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- https://bootstrap.pypa.io/get-pip.py | $SUDO "$PYTHON" - || true
        fi
    fi
    $SUDO "$PYTHON" -m pip install -q virtualenv 2>/dev/null \
        || $SUDO "$PYTHON" -m pip install -q --break-system-packages virtualenv 2>/dev/null || true
    if "$PYTHON" -m virtualenv .venv >/dev/null 2>&1 && [ -x ".venv/bin/python" ]; then
        return 0
    fi
    rm -rf .venv
    return 1
}

step "Устанавливаю зависимости… (3/4)"
FIRST_INSTALL=0
if [ ! -x ".venv/bin/python" ]; then
    FIRST_INSTALL=1
    say "Создаю виртуальное окружение .venv…"
    ensure_venv || die "Не удалось создать .venv. Поставьте пакет venv вручную (${BOLD}apt install ${PYTHON}-venv${NC}) и запустите ./cardinal.sh снова."
    ok "Виртуальное окружение создано."
fi
VENV_PY=".venv/bin/python"

# Лечим битый venv без pip (остаётся после падения ensurepip в старых версиях скрипта).
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    say "В .venv нет pip — чиню…"
    if ! bootstrap_venv_pip; then
        say "Не удалось добавить pip — пересоздаю .venv…"
        rm -rf .venv
        FIRST_INSTALL=1
        ensure_venv || die "Не удалось создать .venv. Поставьте пакет venv вручную (${BOLD}apt install ${PYTHON}-venv${NC}) и запустите ./cardinal.sh снова."
    fi
    ok "pip в .venv работает."
fi

if [ "$FIRST_INSTALL" = "1" ] || [ "$MODE" = "update" ] || ! "$VENV_PY" -c "import aiogram, playerokapi, cardinal" >/dev/null 2>&1; then
    say "Ставлю/обновляю зависимости (pip install -e \".[cardinal]\")…"
    "$VENV_PY" -m pip install --upgrade pip -q
    "$VENV_PY" -m pip install -e ".[cardinal]" -q || die "Не удалось установить зависимости."
    ok "Зависимости установлены."
else
    ok "Зависимости на месте ${GREY}(обновить: ./cardinal.sh --update)${NC}."
fi

# Проверяем конфиг тем же валидатором, что использует бот (русские ошибки pydantic).
if "$VENV_PY" - <<'PYEOF'
import sys
try:
    from cardinal.settings import load_main_settings
    load_main_settings()
except Exception as exc:
    print(exc)
    sys.exit(1)
PYEOF
then
    ok "Конфиг ${BOLD}configs/main.toml${NC} прошёл валидацию."
else
    die "Конфиг не прошёл валидацию (см. выше). Исправьте configs/main.toml или запустите ./cardinal.sh --setup"
fi

# ----------------------------------------------------------------------
# Режим --check: локальная проверка токена + живая авторизация на Playerok
# ----------------------------------------------------------------------
if [ "$MODE" = "check" ]; then
    step "Проверяю токен и авторизацию на Playerok…"
    if "$VENV_PY" - <<'PYEOF'
import sys
import tomllib

from cardinal.first_setup import check_token
from playerokapi.account import Account

with open("configs/main.toml", "rb") as f:
    cfg = tomllib.load(f)["playerok"]

warn = check_token(cfg["cookies"])
print("Локальная проверка токена:", warn or "OK")

account = Account(cookies=cfg["cookies"], user_agent=cfg.get("user_agent"), proxy=cfg.get("proxy"))
account.get()
profile = account.profile
balance = profile.balance.value if profile is not None and profile.balance is not None else "?"
print(f"Авторизация OK: {account.username} | баланс: {balance}")
PYEOF
    then
        echo
        echo "${GREEN}${FRAME}"
        echo "Проверка пройдена — можно запускать: ./cardinal.sh"
        echo "${FRAME}${NC}"
        exit 0
    else
        die "Авторизация не прошла (см. вывод выше). Обновите token: ./cardinal.sh --setup"
    fi
fi

# ----------------------------------------------------------------------
# Предложение автозапуска (однократно, при первой установке на Linux)
# ----------------------------------------------------------------------
if [ "$FIRST_INSTALL" = "1" ] && [ "$(uname)" = "Linux" ] && command -v systemctl >/dev/null 2>&1 && [ -t 0 ]; then
    echo
    ask_yn "Установить systemd-сервис для автозапуска?" n
    if [ "$REPLY" = "true" ]; then
        "$0" --service
    fi
fi

# ----------------------------------------------------------------------
# Шаг 4/4 — Запуск
# ----------------------------------------------------------------------
echo
echo "${GREEN}${FRAME}"
echo "Установка завершена. Запускаю PlayerokCardinal! (4/4)"
echo
echo "Панель управления: напишите своему Telegram-боту /menu"
echo "Остановка:         Ctrl+C"
echo "Логи:              storage/logs/cardinal.log"
echo "Перенастройка:     ./cardinal.sh --setup"
echo "Проверка токена:   ./cardinal.sh --check"
echo "Автозапуск (24/7): ./cardinal.sh --service"
echo "${FRAME}${NC}"
echo
exec "$VENV_PY" -m cardinal
