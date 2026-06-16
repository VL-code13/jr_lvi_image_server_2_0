"""
Модуль репозитория — CRUD-операции с таблицей ``images``.

Содержит функции для сохранения, получения и удаления
метаданных изображений в базе данных PostgreSQL.
"""
from database.db import get_connection
from typing import Optional
import logging

logger: logging.Logger = logging.getLogger(__name__)

def save_metadata(filename: str, original_filename: str, size: int, file_type: str) -> None:
    """
    Сохраняет метаданные изображения в базу данных.

    Args:
        filename: Уникальное имя файла (UUID)
        original_filename: Оригинальное имя файла
        size: Размер файла в байтах
        file_type: Тип файла (jpg, png, gif)
          Raises:
    Exception: При ошибке записи в БД.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = '''
                INSERT INTO images (filename, original_filename, size, file_type)
                VALUES (%s, %s, %s, %s)
            '''
            cursor.execute(sql, (filename, original_filename, size, file_type))
            conn.commit()
        logging.info(f"Saved metadata image {filename} to database")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error saving metadata image {filename} to database: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_images_list(limit: int = 10, offset: int = 0) -> list[dict]:
    """
    Получает список изображений из БД с пагинацией.

    Args:
        limit: Максимальное количество записей на странице.
        offset: Смещение от начала выборки.

    Returns:
        Список словарей с метаданными изображений,
        отсортированный по убыванию даты загрузки.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql: str = """
                SELECT id, filename, original_filename, size, upload_time, file_type
                FROM images
                ORDER BY upload_time DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, offset))
            rows = cursor.fetchall()
        return rows
    finally:
        if conn:
            conn.close()
            """
            columns: list[str] = [
                "id", "filename", "original_filename", "size", "upload_time", "file_type",
            ]
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching images from database: {e}")
        return []"""


def get_total_images_count() -> int:
    """
    Возвращает общее количество изображений в базе данных.

    Returns:
        Целое число — количество записей в таблице ``images``.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM images")
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error counting images in database: {e}")
        return 0
    finally:
        if conn:
            conn.close()


def get_image_by_id(image_id: int) -> Optional[dict]:
    """
    Получает метаданные одного изображения по его ID.

    Args:
        image_id: Уникальный идентификатор записи.

    Returns:
        Словарь с метаданными или ``None``, если запись не найдена.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql: str = """
                SELECT id, filename, original_filename, size, upload_time, file_type
                FROM images
                WHERE id = %s
            """
            cursor.execute(sql, (image_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            columns: list[str] = [
                "id", "filename", "original_filename", "size", "upload_time", "file_type",
            ]
            return dict(zip(columns, row))
    except Exception as e:
        logger.error(f"Error fetching image id={image_id} from database: {e}")
        return None
    finally:
        if conn:
            conn.close()


def delete_image_by_id(image_id: int) -> bool:
    """
    Удаляет запись об изображении из базы данных.

    Args:
        image_id: Уникальный идентификатор записи.

    Returns:
        ``True``, если запись успешно удалена; ``False`` в противном случае.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM images WHERE id = %s", (image_id,))
            conn.commit()
            deleted: bool = cursor.rowcount > 0
            if deleted:
                logger.info(f"Image record deleted from DB: id={image_id}")
            else:
                logger.warning(f"No image found with id={image_id} to delete")
            return deleted
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting image id={image_id} from database: {e}")
        return False
    finally:
        if conn:
            conn.close()