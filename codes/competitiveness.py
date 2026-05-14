from concurrent.futures import ProcessPoolExecutor, as_completed
from selenium.webdriver.support import expected_conditions as ec, wait
from selenium.webdriver.firefox.webdriver import WebDriver
from sqlalchemy.engine import row
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


def get_data(airport_code: str, hotel_code: str, wait: WebDriverWait) -> list[dict]:
    print_value = f"\t\t• Airport Code: {airport_code}, Hotel Id: {hotel_code}"
    # Declaramos la lista de filas
    rows = []
    try:
        # Buscamos las tarjetas totales
        cards = wait.until(ec.visibility_of_all_elements_located(
            (By.XPATH, '//div[@class="uitk-layout-flex uitk-layout-flex-block-size-full-size '
                       'uitk-layout-flex-flex-direction-column uitk-layout-flex-justify-content-space-between"]')))
        # Buscamos en cada una de las tarjetas
        for card in cards:
            # Obtenemos el nombre del producto
            name = card.find_element(By.XPATH, './/h2[@class="uitk-heading uitk-heading-5 overflow-wrap"]').text
            # Obtenemos el nombre del proveedor
            supplier = card.find_element(By.XPATH, './/div[@class="uitk-text uitk-text-spacing-half '
                                                   'truncate-lines-3 uitk-type-300 uitk-text-default-theme"]').text
            # Buscamos el precio de venta
            sale = card.find_element(By.XPATH, './/div[@class="uitk-text uitk-type-500 uitk-type-medium '
                                               'uitk-text-emphasis-theme"]').text.replace("$","")
            # Creamos la nueva fila
            new_row = {
                'expedia_airport_code': airport_code,
                'expedia_hotel_code': int(hotel_code),
                'product': name,
                'supplier': supplier,
                'sale': int(sale),
            }
            rows.append(new_row)
    except TimeoutError:
        print_value += f"\n\t\t\t❌ Check the rule"
    # Iprimimos el mensaje
    print_value += f", Rows: {len(rows)}"
    print(print_value)
    # Terminamos la funcion regresando las filas
    return rows


def run_scraping(airport_code: str, hotel_code: str, geckodriver_path: str, headless: bool, timeout: int) -> list[dict]:
    # Obtenemos el driver
    driver, wait = get_driver(geckodriver_path, headless, timeout)
    # Ingresamos a expedia
    driver.get(f"https://www.expedia.com/ground-transfers/search?adults=2&airportCode={airport_code}&direction="
               f"FROM_AIRPORT&hotelId={hotel_code}&pickUpDate={(datetime.today() + timedelta(8)).strftime('%Y-%m-%d')}"
               f"&roundTrip=false")
    # Obtenemos la información
    rows = get_data(airport_code, hotel_code, wait)
    # Salimos de nuestro scraping cerrando el driver
    driver.close()
    driver.quit()
    # Termianmos la funcion regresando las filas
    return rows


# Función para subir la data
def upload_data(df: pd.DataFrame, db_user: str, db_user_password: str, db_host: str, db_port: int,
                db_name: str) -> None:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Agregamos el dataframe a la base de datos
    df.to_sql('competitiveness_result', con=engine, if_exists='replace', index=False)
    # Terminamos la función
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
    try:
        print("\t • Starting competitiveness scraping")
        # Definimos la ruta del geckodriver
        geckodriver_path = GeckoDriverManager().install()
        # Definimos la lista que almacenara todas las filas
        all_results = []
        # Iniciamos los scrapings
        with ProcessPoolExecutor(max_workers) as executor:
            futures = {executor.submit(run_scraping, row_['expedia_airport_code'], row_['expedia_hotel_code'],
                                       geckodriver_path, headless, timeout): row for _, row_ in df.iterrows()}
            # Procesamos los resultados
            for future in as_completed(futures):
                rows_result = future.result()
                if rows_result:
                    all_results.append(rows_result)
    except Exception as e:
        print("\t ❌ Failed to perform scraping for competitiveness")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Apagamos el VPN
    try:
        print("\t • Disconnecting VPN")
        ip = vpn_off()
        print(f"\t\tOriginal IP: {ip}")
    except Exception as e:
        print("\t ❌ Failed to disconnect VPN")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Subimos la data
    try:
        print("\t • Uploading final competitiveness to database")
        upload_data(pd.DataFrame(all_results), db_user, db_user_password, db_host, db_port, db_name)
        print("\t\tData uploaded successfully")
    except Exception as e:
        print("\t ❌ Failed to upload data to database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Terminamos la función main
    return Result(result=True)