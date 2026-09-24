from loguru import logger
import sys

# Configure logger
logger.remove()  # Remove default handler
logger.add(sys.stdout, level="INFO", format="{time} | {level} | {message}")
logger.add("logs/app.log", rotation="10 MB", level="DEBUG", enqueue=True, backtrace=True, diagnose=True)
