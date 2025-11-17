import logging
import requests

# Eén gedeelde requests sessie voor het hele project
session = requests.Session()

def setup_logging(level: str = "INFO"):
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=lvl, format="%(asctime)s - %(levelname)s - %(message)s")
