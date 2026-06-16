"""
Модуль определения моделей (таблиц) базы данных.

Содержит функции для создания и инициализации таблиц в PostgreSQL.
"""
import psycopg
from psycopg import DatabaseError
from database.db import get_connection
import logging

logger: logging.Logger = logging.getLogger(__name__)


def create_images() -> str:
    """
    Создаёт таблицу ``images`` для хранения метаданных изображений.

    Структура таблицы:
        - ``id``              — SERIAL PRIMARY KEY;
        - ``filename``        — уникальное имя файла (сгенерированное);
        - ``original_filename``   — оригинальное имя файла пользователя;
        - ``size``            — размер файла в байтах;
        - ``upload_time``     — дата и время загрузки;
        - ``file_type``       — формат файла (jpg, png, gif).

    Returns:
        Строка с сообщением об успехе или ошибке.
    """
    try:
        with get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS images (
                            id SERIAL PRIMARY KEY,
                            filename VARCHAR(255) NOT NULL UNIQUE,
                            original_filename VARCHAR(255) NOT NULL,
                            size INTEGER NOT NULL,
                            upload_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            file_type VARCHAR(10) NOT NULL
                        )
                    """)
                    conn.commit()
                    msg: str = "Таблица images успешно создана"
                    logger.info(msg)
                    return msg
            except DatabaseError as e:
                conn.rollback()
                error_msg: str = f"Ошибка создания таблицы SQL: {e}"
                logger.error(error_msg)
                return error_msg
    except Exception as e:
        error_msg = f"Не удалось подключиться к БД: {e}"
        logger.error(error_msg)
        return error_msg