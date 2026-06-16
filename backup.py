import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def create_backup():
    db_name = os.getenv("DATABASE_NAME", "images_db")
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_container_name = os.getenv("DB_CONTAINER_NAME", "image_server_db")

    os.makedirs("backups", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = f"backups/backup_{timestamp}.sql"

    command = ["docker", "exec", "-t", db_container_name, "pg_dump", "-U", db_user, db_name]

    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            subprocess.run(command, stdout=f, check=True)
        print(f"Резервная копия успешно создана: {backup_file}")
    except Exception as e:
         print(f"Ошибка при создании резервной копии:{e}")

if __name__ == "__main__":
    create_backup()