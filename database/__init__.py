"""
Пакет ``database`` — работа с базой данных PostgreSQL.

Предоставляет функции для:
- подключения к БД;
- создания таблиц;
- CRUD-операций с метаданными изображений.
"""

from .db import get_connection
from .models import create_images
from .repository import (
    delete_image_by_id,
    get_image_by_id,
    get_images_list,
    get_total_images_count,
    save_metadata,
)

__all__ = [
    "get_connection",
    "create_images",
    "save_metadata",
    "get_images_list",
    "get_total_images_count",
    "get_image_by_id",
    "delete_image_by_id",
]