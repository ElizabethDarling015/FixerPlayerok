#!/usr/bin/env bash
#
# PlayerokCardinal — установка, настройка и запуск одним скриптом (Linux/macOS).
# Достаточно закинуть проект на чистый сервер и запустить: Python 3.11+ поставится
# автоматически (apt/dnf/pacman/apk/zypper/brew), дальше venv, зависимости, настройка, запуск.
#
#   ./cardinal.sh              первый запуск: установка + настройка + запуск бота
#   ./cardinal.sh --setup      заново пройти настройку (перезапишет configs/main.toml)
#   ./cardinal.sh --check      проверить токен и авторизацию на Playerok (бота не запускает)
#   ./cardinal.sh --update     принудительно обновить зависимости и запустить
#   ./cardinal.sh --update_fixer обновить код с репозитория FixerPlayerok
#   ./cardinal.sh --service    установить systemd-сервис автозапуска (Linux)
#   ./cardinal.sh --offline    запуск в оффлайн-режиме (без подключения к Playerok API)
#   ./cardinal.sh --help       справка
#
# Идемпотентный: повторный запуск ничего не ломает и не трогает конфиги.
#
set -euo pipefail
cd "$(dirname "$0")"

# ----------------------------------------------------------------------
# Цвета и статус-префиксы (читаемо в xterm/ssh)
# ----------------------------------------------------------------------
if [ -t 1 ]; then
    RED=$'\033[1;91m'; CYAN=$'\033[1;96m'; BOLD=$'\033[1m'
    GREEN=$'\033[1;92m'; YELLOW=$'\033[1;93m'; GREY=$'\033[0;90m'; NC=$'\033[0m'
else
    RED=""; CYAN=""; BOLD=""; GREEN=""; YELLOW=""; GREY=""; NC=""
fi

TAG="${CYAN}[PlayerokCardinal]${NC}"

# Тихий apt: без Hit/Get/Unpacking/needrestart-простыни; ошибки остаются видимыми.
export DEBIAN_FRONTEND="${DEBIAN_FRONTEND:-noninteractive}"
export NEEDRESTART_MODE="${NEEDRESTART_MODE:-a}"
export NEEDRESTART_SUSPEND="${NEEDRESTART_SUSPEND:-1}"

info() { echo "${TAG} ${CYAN}›${NC} $*"; }
ok()   { echo "${TAG} ${GREEN}✓${NC} $*"; }
warn() { echo "${TAG} ${YELLOW}!${NC} $*"; }
err()  { echo "${TAG} ${RED}✖${NC} $*" >&2; }
die()  {
    echo >&2
    err "$*"
    exit 2
}
step() {
    echo
    echo "${TAG} ${BOLD}${CYAN}$*${NC}"
}

# Спиннер на время фоновой команды (только в TTY). Возвращает код wait.
_spin() {
    local pid="$1" msg="$2" frames='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' i=0
    if [ ! -t 1 ]; then
        wait "$pid"
        return $?
    fi
    while kill -0 "$pid" 2>/dev/null; do
        i=$(( (i + 1) % 10 ))
        printf '\r%s %s %s' "${TAG}" "${CYAN}${frames:$i:1}${NC}" "$msg"
        sleep 0.08
    done
    printf '\r\033[K'
    wait "$pid"
}

# Тихий apt-get: весь вывод в лог (включая needrestart-хуки).
# apt_quiet — при ошибке показывает хвост лога (для финальных шагов).
# apt_try   — молча возвращает код (для ретраев / || true).
_apt_run() {
    local show_err="$1"; shift
    local logfile rc=0 label
    case "$*" in
        update)     label="Обновляю списки пакетов…" ;;
        install\ *) label="Устанавливаю: ${*#install }" ;;
        *)          label="apt-get $*" ;;
    esac
    logfile=$(mktemp "${TMPDIR:-/tmp}/pc-apt.XXXXXX") || logfile="/tmp/pc-apt.$$"
    (
        ${SUDO:-} env DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a NEEDRESTART_SUSPEND=1 \
            apt-get -y -qq "$@" >"$logfile" 2>&1
    ) &
    if ! _spin $! "$label"; then
        rc=$?
    fi
    if [ "$rc" -eq 0 ]; then
        rm -f "$logfile"
        return 0
    fi
    if [ "$show_err" = "1" ]; then
        err "apt-get $* не удался (код $rc):"
        tail -n 40 "$logfile" >&2 || true
    fi
    rm -f "$logfile"
    return "$rc"
}
apt_quiet() { _apt_run 1 "$@"; }
apt_try()   { _apt_run 0 "$@"; }

# Тихая установка через brew/dnf/pacman/apk/zypper со спиннером.
_pkg_quiet() {
    local label="$1"; shift
    local logfile rc=0
    logfile=$(mktemp "${TMPDIR:-/tmp}/pc-pkg.XXXXXX") || logfile="/tmp/pc-pkg.$$"
    ( "$@" >"$logfile" 2>&1 ) &
    if ! _spin $! "$label"; then
        rc=$?
    fi
    if [ "$rc" -ne 0 ]; then
        err "$* не удался (код $rc):"
        tail -n 40 "$logfile" >&2 || true
    fi
    rm -f "$logfile"
    return "$rc"
}

# Вопрос с необязательным значением по умолчанию → ответ в $REPLY (EOF → ASK_EOF=1).
ASK_EOF=0
ask() {
    local prompt="${TAG} ${CYAN}❯${NC} ${BOLD}$1${NC}"
    if [ -n "${2:-}" ]; then prompt="$prompt ${GREY}[$2]${NC}"; fi
    read -r -p "$prompt: " REPLY || { REPLY=""; ASK_EOF=1; }
    REPLY="${REPLY:-${2:-}}"
}

# Вопрос да/нет → в $REPLY "true"/"false" (для TOML).
ask_yn() {
    local default="${2:-n}" hint="[y/N]"
    if [ "$default" = "y" ]; then hint="[Y/n]"; fi
    read -r -p "${TAG} ${CYAN}❯${NC} ${BOLD}$1${NC} ${GREY}$hint${NC} " REPLY || REPLY=""
    REPLY="${REPLY:-$default}"
    case "$REPLY" in y|Y|yes|Yes|д|Д|да|Да) REPLY="true" ;; *) REPLY="false" ;; esac
}

# Экранирование значения для TOML-строки в двойных кавычках.
esc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

banner() {
    # ANSI Shadow: PLAYEROK (cyan) + CARDINAL (red) — как на скрине терминала.
    echo
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
    echo "  ${GREY}бот-комбайн для продавцов Playerok  ·  /menu в Telegram${NC}"
    echo "  ${GREY}Создатель:${NC} ${CYAN}https://t.me/Scwee_xz${NC}"
    echo
}

usage() {
    banner
    sed -n 's/^#   //p' "$0"
    exit 0
}

MODE="run"; FORCE_SETUP=0; OFFLINE_MODE=0; UPDATE_FIXER=0
case "${1:-}" in
    --help|-h)  usage ;;
    --setup)    FORCE_SETUP=1 ;;
    --check)    MODE="check" ;;
    --update)   MODE="update" ;;
    --update_fixer) UPDATE_FIXER=1 ;;
    --service)  MODE="service" ;;
    --offline|-o) OFFLINE_MODE=1 ;;
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
    info "Ответьте на вопросы — конфиги будут созданы автоматически."
    info "Потом всё можно поменять в ${BOLD}configs/${NC} или через Telegram-панель (/menu)."

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
    info "Подключаю репозитории universe и deadsnakes…"
    apt_try install software-properties-common || true
    $SUDO add-apt-repository -y universe >/dev/null 2>&1 || true
    $SUDO add-apt-repository -y ppa:deadsnakes/ppa >/dev/null 2>&1 || true
    apt_try update || true
    ok "Репозитории готовы."
}

# Ставит Python 3.11+ через пакетный менеджер системы (apt/dnf/pacman/apk/zypper/brew).
install_python() {
    info "Python 3.11+ не найден — устанавливаю автоматически…"
    need_sudo

    if [ "$(uname)" = "Darwin" ]; then
        command -v brew >/dev/null 2>&1 \
            || die "На macOS нужен Homebrew (https://brew.sh) или Python с https://python.org — потом запустите ./cardinal.sh снова."
        _pkg_quiet "Устанавливаю python@3.12 (Homebrew)…" brew install python@3.12 \
            || die "brew install python@3.12 не удался."
        ok "Пакет python@3.12 установлен."
        return 0
    fi

    detect_os
    case " $OS_ID $OS_LIKE " in
        *debian*|*ubuntu*)
            apt_try update || true
            # Штатные пакеты: Debian 12+ / Ubuntu 24.04+ дают Python 3.11+.
            if apt_try install python3 python3-venv python3-pip; then
                ok "Пакеты python3 / python3-venv / python3-pip установлены."
            fi
            if ! find_python; then
                case " $OS_ID $OS_LIKE " in
                    *ubuntu*)
                        # Старая Ubuntu (20.04/22.04): свежий Python из PPA deadsnakes.
                        apt_enable_extra_repos
                        apt_quiet install python3.12 python3.12-venv \
                            || die "Не удалось установить python3.12 из deadsnakes."
                        ok "Пакет python3.12-venv установлен."
                        ;;
                    *)
                        die "В репозиториях этой версии Debian нет Python 3.11+ — обновитесь до Debian 12 (bookworm) или поставьте Python вручную."
                        ;;
                esac
            else
                ok "Python установлен."
            fi
            ;;
        *rhel*|*centos*|*rocky*|*alma*)
            # Ветка ДО fedora: у RHEL-клонов ID_LIKE содержит "fedora", но штатный
            # python3 там старый — ставим версионированный пакет.
            _pkg_quiet "Устанавливаю python3.12 (dnf)…" $SUDO dnf install -y -q python3.12 python3.12-pip \
                || _pkg_quiet "Устанавливаю python3.11 (dnf)…" $SUDO dnf install -y -q python3.11 python3.11-pip \
                || die "dnf install python3.12/3.11 не удался."
            ok "Python установлен."
            ;;
        *fedora*)
            _pkg_quiet "Устанавливаю python3 (dnf)…" $SUDO dnf install -y -q python3 python3-pip \
                || die "dnf install python3 не удался."
            ok "Python установлен."
            ;;
        *arch*)
            _pkg_quiet "Устанавливаю python (pacman)…" $SUDO pacman -Sy --noconfirm --quiet python python-pip \
                || die "pacman install python не удался."
            ok "Python установлен."
            ;;
        *alpine*)
            _pkg_quiet "Устанавливаю python3 (apk)…" $SUDO apk add --no-cache --quiet python3 py3-pip \
                || die "apk add python3 не удался."
            ok "Python установлен."
            ;;
        *suse*)
            _pkg_quiet "Устанавливаю python312 (zypper)…" $SUDO zypper --non-interactive --quiet install python312 python312-pip \
                || _pkg_quiet "Устанавливаю python311 (zypper)…" $SUDO zypper --non-interactive --quiet install python311 python311-pip \
                || die "zypper install python312/311 не удался."
            ok "Python установлен."
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
# Режим --update_fixer: обновление кода с GitHub (ElizabethDarling015/FixerPlayerok)
# ----------------------------------------------------------------------
if [ "$UPDATE_FIXER" = "1" ]; then
    step "Обновление Fixer с GitHub…"
    
    # Проверяем наличие venv
    if [ ! -x ".venv/bin/python" ]; then
        info "Виртуальное окружение не найдено. Сначала запустите ./cardinal.sh для установки."
        die "Прервано."
    fi
    
    VENV_PY=".venv/bin/python"
    
    # Запускаем Python скрипт обновления
    info "Скачиваю и применяю обновления с ElizabethDarling015/FixerPlayerok…"
    
    if "$VENV_PY" - <<'PYEOF'
import sys
from pathlib import Path
from cardinal.self_update import update_from_github

print("🔄 Обновление с репозитория: ElizabethDarling015/FixerPlayerok")
print(f"📁 Целевая директория: {Path.cwd()}")
print("-" * 60)

result = update_from_github(
    root=Path.cwd(),
    repo="ElizabethDarling015/FixerPlayerok",
    branch="main",
    update_deps=True
)

print("\n" + "=" * 60)
if result.ok:
    print(f"✅ {result.message}")
    if result.detail:
        print(f"📝 Детали:\n{result.detail}")
    if result.changed:
        print("\n🎉 Код успешно обновлён!")
        print("💡 Запустите бота: ./cardinal.sh")
        sys.exit(0)
    else:
        print("\nℹ️  Изменений не обнаружено — у вас последняя версия.")
        sys.exit(0)
else:
    print(f"❌ {result.message}")
    if result.detail:
        print(f"📝 Детали ошибки:\n{result.detail}")
    print("\n💡 Проверьте:")
    print("   - Правильность имени репозитория")
    print("   - Доступность репозитория")
    print("   - Подключение к интернету")
    sys.exit(1)
PYEOF
    then
        echo
        ok "Обновление завершено успешно!"
        info "Запустите бота: ${BOLD}./cardinal.sh${NC}"
        exit 0
    else
        die "Ошибка обновления. Проверьте подключение к интернету и доступность репозитория."
    fi
fi

# ----------------------------------------------------------------------
# Режим --service: systemd-юнит (только Linux)
# ----------------------------------------------------------------------
if [ "$MODE" = "service" ]; then
    [ "$(uname)" = "Linux" ] || die "systemd-сервис доступен только на Linux."
    command -v systemctl >/dev/null 2>&1 || die "systemctl не найден — система без systemd."
    info "Устанавливаю systemd-сервис (нужны права sudo)…"
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
        local venv_pkg="${PYTHON}-venv"
        apt_try update || true
        if apt_try install "$venv_pkg"; then
            ok "Пакет ${venv_pkg} установлен."
        elif apt_try install python3-venv; then
            ok "Пакет python3-venv установлен."
        else
            warn "Пакет ${venv_pkg} не установился с первого раза — пробую дальше."
        fi
        # 2) Не нашлось (частая причина: на минимальной Ubuntu выключен universe,
        #    а для python из deadsnakes нужен его же PPA) — подключаем репозитории и повторяем.
        if ! create_venv; then
            case " ${OS_ID:-} ${OS_LIKE:-} " in
                *ubuntu*)
                    apt_enable_extra_repos
                    if apt_quiet install "$venv_pkg"; then
                        ok "Пакет ${venv_pkg} установлен."
                    elif apt_quiet install python3-venv; then
                        ok "Пакет python3-venv установлен."
                    fi
                    ;;
            esac
        fi
        create_venv && return 0
    fi

    # 3) Универсальный запасной путь: virtualenv не требует системного ensurepip.
    info "python -m venv недоступен — пробую virtualenv…"
    if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://bootstrap.pypa.io/get-pip.py | $SUDO "$PYTHON" - >/dev/null 2>&1 || true
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- https://bootstrap.pypa.io/get-pip.py | $SUDO "$PYTHON" - >/dev/null 2>&1 || true
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
    info "Создаю виртуальное окружение .venv…"
    ensure_venv || die "Не удалось создать .venv. Поставьте пакет venv вручную (${BOLD}apt install ${PYTHON}-venv${NC}) и запустите ./cardinal.sh снова."
    ok "Виртуальное окружение создано."
fi
VENV_PY=".venv/bin/python"

# Лечим битый venv без pip (остаётся после падения ensurepip в старых версиях скрипта).
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
    info "В .venv нет pip — чиню…"
    if ! bootstrap_venv_pip; then
        warn "Не удалось добавить pip — пересоздаю .venv…"
        rm -rf .venv
        FIRST_INSTALL=1
        ensure_venv || die "Не удалось создать .venv. Поставьте пакет venv вручную (${BOLD}apt install ${PYTHON}-venv${NC}) и запустите ./cardinal.sh снова."
    fi
    ok "pip в .venv работает."
fi

if [ "$FIRST_INSTALL" = "1" ] || [ "$MODE" = "update" ] || ! "$VENV_PY" -c "import aiogram, playerokapi, cardinal" >/dev/null 2>&1; then
    info "Ставлю зависимости (pip install -e \".[cardinal]\")…"
    _pkg_quiet "Обновляю pip…" "$VENV_PY" -m pip install --upgrade pip -q \
        || die "Не удалось обновить pip."
    _pkg_quiet "Устанавливаю зависимости…" "$VENV_PY" -m pip install -e ".[cardinal]" -q \
        || die "Не удалось установить зависимости."
    
    # Явно устанавливаем браузеры для Playwright (выполняется быстро, если уже установлено)
    info "Проверяю/устанавливаю браузеры Playwright…"
    "$VENV_PY" -m playwright install chromium >/dev/null 2>&1 || true
    ok "Зависимости и браузеры установлены."
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
        ok "Проверка пройдена — можно запускать: ${BOLD}./cardinal.sh${NC}"
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
step "Запускаю PlayerokCardinal… (4/4)"
ok "Установка завершена."
echo "  ${GREY}Панель:${NC}     Telegram-бот → /menu"
echo "  ${GREY}Стоп:${NC}        Ctrl+C"
echo "  ${GREY}Логи:${NC}        storage/logs/cardinal.log"
echo "  ${GREY}Setup:${NC}       ./cardinal.sh --setup"
echo "  ${GREY}Check:${NC}       ./cardinal.sh --check"
echo "  ${GREY}Обновление:${NC}  ./cardinal.sh --update_fixer"
echo "  ${GREY}Автозапуск:${NC}  ./cardinal.sh --service"
echo "  ${GREY}Создатель:${NC}   ${CYAN}https://t.me/Scwee_xz${NC}"
echo
if [ "$OFFLINE_MODE" = "1" ]; then
    echo "🔧 OFFLINE MODE: запуск без подключения к Playerok API"
    exec "$VENV_PY" -m cardinal --offline
else
    exec "$VENV_PY" -m cardinal
fi