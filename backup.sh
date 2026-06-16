#!/bin/bash
# ============================================================
# backup.sh — скрипт резервного копирования базы данных
# PostgreSQL для проекта «Сервер картинок 2.0».
#
# Использование:
#   chmod +x backup.sh
#   ./backup.sh
#
# Результат:
#   Файл backup_YYYY-MM-DD_HHMMSS.sql в папке ./backups/
# ============================================================

# Имя контейнера PostgreSQL (должно совпадать с docker-compose.yaml)
CONTAINER_NAME="image_server_db"
DB_USER="postgres"
DB_NAME="images_db"

# Папка для бэкапов
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

# Формируем имя файла с датой и временем
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

echo "Создание резервной копии базы данных '${DB_NAME}'..."
echo "Контейнер: ${CONTAINER_NAME}"
echo "Файл: ${BACKUP_FILE}"

# Выполняем pg_dump внутри контейнера
docker exec -t "${CONTAINER_NAME}" \
    pg_dump -U "${DB_USER}" "${DB_NAME}" > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✅ Резервная копия успешно создана: ${BACKUP_FILE}"
    echo "   Размер: $(du -h "${BACKUP_FILE}" | cut -f1)"
else
    echo "❌ Ошибка при создании резервной копии!"
    exit 1
fi