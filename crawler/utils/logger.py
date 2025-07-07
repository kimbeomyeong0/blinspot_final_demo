import logging
from datetime import datetime

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('crawler/logs/crawler.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__) 