import os
from dotenv import load_dotenv
from typing import Optional
from logger import logger


def get_token(name: str,path : str) -> Optional[str]:
    load_dotenv(dotenv_path=path)
    TOKEN = os.getenv(name)
    if not TOKEN:
        logger.error(f"Не получилось найти {name} .env файл по пути {path}")
        return None
    else:
        return TOKEN
    