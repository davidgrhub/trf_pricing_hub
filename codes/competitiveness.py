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
import subprocess
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


def vpn_on() -> str:
    # Conexión a USA
    process = subprocess.run(["nordvpn", "connect", "United_States"], check=True, capture_output=True, text=True)
    # Verificamos la IP obtenida para el log
    ip_check = subprocess.run(["curl", "-s", "https://ifconfig.me"], capture_output=True, text=True)
    # Terminamos la función regresando la nueva ip
    return ip_check.stdout.strip()


def vpn_off() -> str:
    # Desconectamos el vpn
    subprocess.run(["nordvpn", "disconnect"], check=True, capture_output=True)
    # Verificamos la IP original
    ip_check = subprocess.run(["curl", "-s", "https://ifconfig.me"], capture_output=True, text=True)
    # Terminamos la función regresando la ip
    return ip_check.stdout.strip()


# Funciones para scraping
def get_driver(geckodriver_path: str, headless: bool, timeout: int) -> tuple[WebDriver, WebDriverWait]:
    # Declaramos si el sistema operativo es windows
    is_windows = platform.system() == "Windows"
    # Declaramos el servicio del driver
    service = Service(geckodriver_path)
    # Configuramos las opciones
    options = webdriver.FirefoxOptions()
    options.set_preference("intl.accept_languages", "en-US,en")
    options.add_argument("-private-window")
    # Configuramos el headless
    if not (is_windows and headless is False):
        options.add_argument("--headless")
    # Iniciamos el driver
    driver = webdriver.Firefox(options=options, service=service)
    # Ingresamos el tiempo de espera
    wait = WebDriverWait(driver, timeout)
    # Terminamos la función regresando driver y wait
    return driver, wait


def run_scraping(airport_code: str, hotel_code: str, geckodriver_path: str, headless: bool, timeout: int) -> None:
    return


# Función main
def main_competitiveness(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str,
                         headless: bool, timeout: int, max_workers: int) -> Result:
    print("\t[Competitiveness Block] Scraping & processing 🧨")
    # Obtenemos las reglas para el scraping
    try:
        df = get_rules(db_user, db_user_password, db_host, db_port, db_name)
        print(f"\t • Rules successfully retrieved. Rows loaded: {len(df)}")
    except Exception as e:
        print("\t ❌ Failed to retrieve rules from database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Prendemos el VPN
    try:
        print("\t • Connecting to VPN")
        new_ip = vpn_on()
        print(f"\t\tCurrent IP: {new_ip}")
    except Exception as e:
        print("\t ❌ Failed to connect to VPN")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Iniciamos el scraping de competitividad


    print("\t • Starting delegations scraping")
    for _, row in df.iterrows():
        print(row['expedia_airport_code'], row['expedia_hotel_code'])


    # Apagamos el VPN
    try:
        print("\t • Disconnecting VPN")
        ip = vpn_off()
        print(f"\t\tOriginal IP: {ip}")
    except Exception as e:
        print("\t ❌ Failed to disconnect VPN")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Terminamos la función main
    return Result(result=True)