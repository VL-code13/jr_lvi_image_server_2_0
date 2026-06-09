from database.db import get_connection
import logging


def save_metadata(filename: str, original_name: str, size: int, file_type: str) -> None:
    """
    Сохраняет метаданные изображения в базу данных.

    Args:
        filename: Уникальное имя файла (UUID)
        original_name: Оригинальное имя файла
        size: Размер файла в байтах
        file_type: Тип файла (jpg, png, gif)
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = '''
                INSERT INTO images (filename, original_name, size, file_type)
                VALUES (%s, %s, %s, %s)
            '''
            cursor.execute(sql, (filename, original_name, size, file_type))
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