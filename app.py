"""
Основной модуль Flask-приложения «Сервер картинок 2.0».

Предоставляет REST API и веб-интерфейс для:
- загрузки изображений (JPG, PNG, GIF);
- просмотра списка загруженных изображений с пагинацией;
- удаления изображений;
- резервного копирования базы данных.
"""

import logging
import math
import os
import traceback
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_cors import CORS
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from database.models import create_images
from database.repository import (
    delete_image_by_id,
    get_image_by_id,
    get_images_list,
    get_total_images_count,
    save_metadata,
)
from settings import (
    ALLOWED_IMAGE_FORMATS,
    BASE_DIR,
    IMAGES_DIR,
    LOGS_DIR,
    MAX_FILE_SIZE,
    REQUEST_LIMIT,
    ensure_directories_exist,
)

app: Flask = Flask(__name__)
CORS(app)
# ──────────────────────────────────────────────
# Применяем настройки
# ──────────────────────────────────────────────

app.config["MAX_CONTENT_LENGTH"] = REQUEST_LIMIT
# ──────────────────────────────────────────────
# Создаём директории при запуске приложения
# ──────────────────────────────────────────────
ensure_directories_exist()

# ──────────────────────────────────────────────
# Настройка логирования
# ──────────────────────────────────────────────
logging.basicConfig(
    filename=LOGS_DIR / "app.log",
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
)

logger: logging.Logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Вспомогательные функции
# ──────────────────────────────────────────────
def detect_image_extension(file_data: bytes) -> Optional[str]:
    """
    Определяет расширение изображения по его бинарному содержимому.

    Args:
        file_data: Бинарные данные файла.

    Returns:
        Строка с расширением ('jpg', 'png', 'gif')
        или None, если формат не поддерживается.
    """
    try:
        with Image.open(BytesIO(file_data)) as image:
            fmt: Optional[str] = image.format
            image.verify()
            return ALLOWED_IMAGE_FORMATS.get(fmt)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


# ──────────────────────────────────────────────
# Маршруты: страницы
# ──────────────────────────────────────────────
@app.get("/")
def home() -> str:
    """Главная страница сервиса."""
    return render_template("index.html")


@app.get("/upload")
def upload_page() -> str:
    """Страница загрузки изображений."""
    return render_template("upload.html")


@app.get("/images-list")
def images_page() -> str:
    """
    Страница списка загруженных изображений с пагинацией.

    Query-параметры:
        page (int): Номер страницы (по умолчанию 1).

    Returns:
        Отрендеренный HTML-шаблон images_list.html.
    """
    page: int = request.args.get("page", 1, type=int)
    per_page: int = 10
    offset: int = (page - 1) * per_page

    try:
        total_images: int = get_total_images_count()
        total_pages: int = (math.ceil(total_images / per_page) if total_images > 0 else 1)
        images = get_images_list(per_page=per_page, offset=offset)

        formatted_images: list[dict] = []
        for img in images:
            img_id, filename, original_filename, size, upload_time, file_type = img
            formatted_images.append(
                {
                    "id": img_id,
                    "filename": filename,
                    "original_filename": original_filename,
                    "size_kb": round(size / 1024, 2),
                    "upload_time": (
                        upload_time.strftime("%Y-%m-%d %H:%M:%S")
                        if upload_time
                        else "—"
                    ),
                    "file_type": file_type,
                    "url": f"/images/{filename}",
                }
            )

        return render_template(
            "images_list.html",
            images=formatted_images,
            page=page,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages,
        )
    except Exception as e:
        logger.error("Error reading images from database: %s", e)
        return jsonify({"error": "Failed to read images list"}), 500


# ──────────────────────────────────────────────
# Маршруты: API загрузки
# ──────────────────────────────────────────────
@app.post("/upload")
def upload_image():
    """
    Обработчик загрузки изображений.

    Принимает файл из поля формы ``image``, проверяет формат и размер,
    сохраняет на диск и записывает метаданные в PostgreSQL.

    Returns:
        JSON с информацией о загруженном файле (статус 201)
        или JSON с описанием ошибки.
    """
    uploaded_file = request.files.get("image")
    if uploaded_file is None:
        logger.warning("No image uploaded. Файл image не найден в запросе.")
        return jsonify(
            {
                "error": (
                    "No image uploaded. Файл не найден. "
                    "Поле формы должно называться 'image'"
                ),
            }
        ), 400

    original_filename: str = uploaded_file.filename or "Unknown"

    if not original_filename or original_filename == "Unknown":
        logger.warning("File has no name")
        return jsonify({"error": "Файл не имеет имени"}), 400

    try:
        file_data: bytes = uploaded_file.read()
    except Exception as e:
        logger.error("Error reading file %s: %s", original_filename, e)
        return jsonify({"error": "Error reading file"}), 500

    if not file_data:
        logger.warning("Empty file uploaded: %s", original_filename)
        return jsonify({"error": "Файл пустой"}), 400

    if len(file_data) > MAX_FILE_SIZE:
        logger.warning(
            "File %s exceeds size limit (5 MB)", original_filename
        )
        return jsonify({"error": "Файл не должен быть больше 5 МБ."}), 413

    image_extension: Optional[str] = detect_image_extension(file_data)
    if image_extension is None:
        logger.warning("Unsupported image format: %s", original_filename)
        return jsonify(
            {
                "error": (
                    "Файл неверного формата. "
                    "Поддерживаются только jpg, png, gif."
                ),
            }
        ), 400

    # Генерируем уникальное имя файла
    unique_filename: str = f"{uuid.uuid4().hex}.{image_extension}"
    target_path: Path = IMAGES_DIR / unique_filename
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Сохраняем файл на диск
    try:
        target_path.write_bytes(file_data)
        logger.info("File saved to disk: %s", unique_filename)
    except PermissionError as e:
        logger.error(
            "Permission denied when saving file %s: %s", unique_filename, e
        )
        return jsonify({"error": "Нет прав на запись файла"}), 500
    except OSError as e:
        logger.error("OS error when saving file %s: %s", unique_filename, e)
        return jsonify({"error": "Ошибка файловой системы"}), 500

    # Сохраняем метаданные в БД
    try:
        save_metadata(
            filename=unique_filename,
            original_filename=original_filename,
            size=len(file_data),
            file_type=image_extension,
        )
    except Exception as e:
        # Если БД упала — удаляем файл с диска (откат)
        target_path.unlink(missing_ok=True)
        logger.error(
            "File deleted. Error saving metadata for %s to DB: %s",
            unique_filename,
            e,
        )
        return jsonify({"error": "Error saving metadata file"}), 500

    logger.info(
        "Image uploaded successfully: %s → %s",
        original_filename,
        unique_filename,
    )

    return jsonify(
        {
            "message": "Изображение успешно загружено",
            "filename": unique_filename,
            "original_filename": original_filename,
            "url": f"/images/{unique_filename}",
            "full_url": (
                request.host_url.rstrip("/") + f"/images/{unique_filename}"
            ),
            "size": len(file_data),
        }
    ), 201


# ──────────────────────────────────────────────
# Маршруты: удаление
# ──────────────────────────────────────────────
@app.get("/delete/<int:id>")
def delete_image(id: int):
    """
    Удаляет изображение из базы данных и с диска.

    Args:
        id: Уникальный идентификатор записи в таблице images.

    Returns:
        Редирект на страницу списка изображений
        или JSON с ошибкой.
    """
    try:
        image: Optional[tuple] = get_image_by_id(id)
        if image is None:
            logger.warning("Image with id=%d not found in database", id)
            return jsonify({"error": "Изображение не найдено"}), 404

        img_id: int = image[0]
        filename: str = image[1]

        # Удаляем физический файл
        file_path: Path = IMAGES_DIR / filename
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info("Physical file deleted: %s from disk", filename)
            except Exception as e:
                logger.error(
                    "Error deleting physical file %s: %s", filename, e
                )

        # Удаляем запись из БД
        delete_image_by_id(img_id)
        logger.info(
            "Image record deleted from DB: id=%d, file=%s", img_id, filename
        )

        return redirect(url_for("images_page"))

    except Exception as e:
        logger.error("Error deleting image id=%d: %s", id, e)
        return jsonify({"error": "Ошибка при удалении изображения"}), 500


# ──────────────────────────────────────────────
# Маршруты: отдача файлов (Nginx fallback)
# ──────────────────────────────────────────────
@app.get("/images/<filename>")
def get_image(filename: str):
    """
    Отдаёт запрошенное изображение.

    Args:
        filename: Имя файла изображения.

    Returns:
        Файл изображения или JSON с ошибкой.
    """
    file_path: Path = IMAGES_DIR / filename
    if not file_path.exists():
        logger.warning("Requested file not found: %s", filename)
        return jsonify({"error": "File not found"}), 404
    if not file_path.is_file():
        logger.warning("Invalid file path requested: %s", filename)
        return jsonify({"error": "Invalid file path"}), 400
    try:
        return send_from_directory(str(IMAGES_DIR), filename)
    except Exception as e:
        logger.error("Error serving file %s: %s", filename, e)
        return jsonify({"error": "Error serving file"}), 500


# ──────────────────────────────────────────────
# Обработчики ошибок
# ──────────────────────────────────────────────
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e: RequestEntityTooLarge) -> tuple:
    """Обрабатывает ошибку превышения размера файла."""
    logger.error("File too large: %s", e)
    return jsonify({"error": "Файл слишком большой"}), 413


@app.errorhandler(BadRequest)
def handle_bad_request(e: BadRequest) -> tuple:
    """Обрабатывает некорректные запросы."""
    logger.error("Bad request: %s", e)
    return jsonify({"error": "Некорректный запрос"}), 400


if __name__ == "__main__":
    ensure_directories_exist()
    create_images()
    app.run(host="0.0.0.0", port=3000, debug=True)