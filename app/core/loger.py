import os
import logging
from logging.handlers import RotatingFileHandler

APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(APP_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "application.log")
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(name: str = 'Hɛnnu AI') -> logging.Logger:
    logger = logging.getLogger(name)

    # Évite d'ajouter de nouveaux handlers si le logger est déjà configuré
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # Empêche la remontée vers le root logger
    # On configure uniquement le RotatingFileHandler (Suppression de basicConfig)
    formatter = logging.Formatter(LOGGING_FORMAT)
    
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8"
    )
    # Correction de la variable 'formatter'
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger