import psycopg
from psycopg import DatabaseError  # Импорт исключения для обработки ошибок БД

from database.db import get_connection


def create_images():
    try:
        with get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS images (
                            id SERIAL PRIMARY KEY,
                            filename VARCHAR(100) NOT NULL UNIQUE,
                            original_filename VARCHAR(100) NOT NULL,
                            size INTEGER NOT NULL,
                            upload_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            file_type VARCHAR(10) NOT NULL
                        )
                    ''')
                    conn.commit()
                    return 'Таблица images успешно создана'
            except DatabaseError as e:
                # Откат транзакции при ошибке SQL
                conn.rollback()
                print(f'Ошибка выполнения SQL: {e}')
                return f'Ошибка создания таблицы: {str(e)}'
    except Exception as e:
        # Обработка ошибок подключения
        print(f'Не удалось подключиться к БД: {e}')
        return f'Ошибка подключения: {str(e)}'
