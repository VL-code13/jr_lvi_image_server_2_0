#!/usr/bin/env bash
# ============================================================
# backup.sh — скрипт резервного копирования базы данных
# PostgreSQL для проекта «Сервер картинок 2.0».
#
# Использование:
#   chmod +x backup.sh
#   ./backup.sh
#
# Результат:
#   Файл backup_YYYYMMDD-HHMMSS.sql в папке ./backups/
#
# Требования:
#   - Docker должен быть запущен
#   - Контейнер PostgreSQL должен быть активен
#   - Переменные можно переопределить через .env или окружение
# ============================================================

# ──────────────────────────────────────────────
# Строгий режим выполнения
# ──────────────────────────────────────────────
# -e  : выход при любой ошибке команды
# -u  : ошибка при использовании неопределённой переменной
# -o pipefail : пайплайн падает, если упала любая команда в нём
set -euo pipefail

# ──────────────────────────────────────────────
# Константы и пути
# ──────────────────────────────────────────────
# Абсолютный путь к директории скрипта (не зависит от cwd)
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="${SCRIPT_DIR}"
readonly BACKUP_DIR="${PROJECT_DIR}/backups"
readonly ENV_FILE="${PROJECT_DIR}/.env"

# Значения по умолчанию (переопределяются через .env или окружение)
CONTAINER_NAME="${DB_CONTAINER_NAME:-image_server_db}"
DB_USER="${DATABASE_USER:-postgres}"
DB_NAME="${DATABASE_NAME:-images_db}"

# Максимальное количество хранимых бэкапов (ротация)
readonly MAX_BACKUPS=10

# ──────────────────────────────────────────────
# Загрузка переменных из .env (если файл существует)
# ──────────────────────────────────────────────
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    set -a
    source "${ENV_FILE}"
    set +a
    # Повторно применяем значения после source
    CONTAINER_NAME="${DB_CONTAINER_NAME:-${CONTAINER_NAME}}"
    DB_USER="${DATABASE_USER:-${DB_USER}}"
    DB_NAME="${DATABASE_NAME:-${DB_NAME}}"
fi

# ──────────────────────────────────────────────
# Функции логирования
# ──────────────────────────────────────────────
log_info()  { echo -e "ℹ️  $*"; }
log_ok()    { echo -e "✅ $*"; }
log_error() { echo -e "❌ $*" >&2; }

# ──────────────────────────────────────────────
# Очистка при прерывании (Ctrl+C, ошибки)
# ──────────────────────────────────────────────
BACKUP_FILE=""
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 && -n "${BACKUP_FILE}" && -f "${BACKUP_FILE}" ]]; then
        log_error "Скрипт прерван. Удаляю неполный файл: ${BACKUP_FILE}"
        rm -f "${BACKUP_FILE}"
    fi
    exit "${exit_code}"
}
trap cleanup EXIT INT TERM

# ──────────────────────────────────────────────
# Проверка зависимостей
# ──────────────────────────────────────────────
check_dependencies() {
    if ! command -v docker &>/dev/null; then
        log_error "Docker не установлен или не находится в PATH."
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker daemon не запущен. Запустите Docker и повторите."
        exit 1
    fi

    # Проверяем, что контейнер существует и запущен
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Контейнер '${CONTAINER_NAME}' не запущен."
        log_info  "Запустите: docker-compose up -d"
        exit 1
    fi
}

# ──────────────────────────────────────────────
# Ротация старых бэкапов
# ──────────────────────────────────────────────
rotate_backups() {
    local count
    count=$(find "${BACKUP_DIR}" -maxdepth 1 -name "backup_*.sql" -type f | wc -l)

    if (( count > MAX_BACKUPS )); then
        local to_delete=$(( count - MAX_BACKUPS ))
        log_info "Ротация бэкапов: удаляю ${to_delete} старых файлов..."
        find "${BACKUP_DIR}" -maxdepth 1 -name "backup_*.sql" -type f -print0 \
            | xargs -0 ls -t \
            | tail -n "${to_delete}" \
            | xargs rm -f
    fi
}

# ──────────────────────────────────────────────
# Основная функция
# ──────────────────────────────────────────────
main() {
    log_info "Запуск резервного копирования базы данных '${DB_NAME}'..."
    log_info "Контейнер : ${CONTAINER_NAME}"
    log_info "Пользователь: ${DB_USER}"

    # Создаём директорию для бэкапов
    mkdir -p "${BACKUP_DIR}"

    # Формируем имя файла с датой и временем
    # Формат унифицирован с Python-версией (backup.py)
    local timestamp
    timestamp="$(date +"%Y%m%d-%H%M%S")"
    BACKUP_FILE="${BACKUP_DIR}/backup_${timestamp}.sql"

    log_info "Файл бэкапа: ${BACKUP_FILE}"

    # Выполняем pg_dump внутри контейнера
    # ВАЖНО: НЕ используем флаг -t (TTY), иначе в файле появятся \r
    if ! docker exec "${CONTAINER_NAME}" \
            pg_dump -U "${DB_USER}" "${DB_NAME}" > "${BACKUP_FILE}"; then
        log_error "Ошибка при выполнении pg_dump!"
        return 1
    fi

    # Проверяем, что файл создан и не пустой
    if [[ ! -s "${BACKUP_FILE}" ]]; then
        log_error "Файл бэкапа пустой или не создан!"
        return 1
    fi

    # Получаем размер файла
    local file_size
    if command -v du &>/dev/null; then
        file_size="$(du -h "${BACKUP_FILE}" | cut -f1)"
    else
        file_size="$(wc -c < "${BACKUP_FILE}") байт"
    fi

    log_ok "Резервная копия успешно создана!"
    log_info "   Путь  : ${BACKUP_FILE}"
    log_info "   Размер: ${file_size}"

    # Ротация старых бэкапов
    rotate_backups

    return 0
}

# ──────────────────────────────────────────────
# Точка входа
# ──────────────────────────────────────────────
check_dependencies
main