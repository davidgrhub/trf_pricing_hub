from concurrent.futures import ProcessPoolExecutor, as_completed
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.firefox.webdriver import WebDriver
from sqlalchemy.ext.asyncio import result
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine
from datetime import datetime, timedelta
from dataclasses import dataclass
from selenium import webdriver
import pandas as pd
import numpy as np
import platform
import time


# Clase para el resultado del bloque
@dataclass
class Result:
    result: bool
    error: str | None = None


# Funciones auxiliares
def get_rules(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str) -> pd.DataFrame:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Leemos la tabla y la convertimos en DataFrame
    df = pd.read_sql(f"SELECT DISTINCT expedia_airport_code, expedia_hotel_code FROM rules", con=engine)
    # Terminamos la función regresando el DataFrame
    return df


# Función main
def main_competitiveness(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str) -> Result:
    print("\t[Competitiveness Block] Scraping & processing 🧨")
    # Obtenemos las reglas para el scraping
    try:
        df = get_rules(db_user, db_user_password, db_host, db_port, db_name)
        print(f"\t • Rules successfully retrieved. Rows loaded: {len(df)}")
    except Exception as e:
        print("\t ❌ Failed to retrieve rules from database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Terminamos la función main
    return Result(result=True)