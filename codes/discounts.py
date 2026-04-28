from concurrent.futures import ProcessPoolExecutor, as_completed
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.firefox.webdriver import WebDriver
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
import platform
import time


# Clase para resultado
@dataclass
class Result:
    result: bool
    error: str | None = None


# Funciones auxiliares
def get_strategies(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str) -> pd.DataFrame:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Leemos la tabla y la convertimos en DataFrame
    df = pd.read_sql(f"SELECT * FROM final_strategies", con=engine)
    # Configuramos las columnas y sus formatos
    df['unique_id'] = df['unique_id'].astype(int)
    df['product_id'] = df['product_id'].astype(int)
    df['option_id'] = df['option_id'].astype(int)
    # Terminamos la función regresando el DataFrame
    return df


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


def sing_in(driver: WebDriver, wait: WebDriverWait, user: str, use_password: str) -> None:
    # Ingresamos a la Intranet
    driver.get('https://www.nexustours.com/intranet/login.aspx')
    # Login con azure
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//a[@id="_ctl0_data_holder_LoginAzure"]'))).click()
    # Ingresamos el correo
    mail = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="email"]')))
    mail.click()
    mail.send_keys(user)
    time.sleep(1.2)
    # Submit
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="submit"]'))).click()
    time.sleep(2)
    # Ingresamos la contraseña
    password = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="password"]')))
    password.click()
    password.send_keys(use_password)
    time.sleep(1.2)
    # Submit
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="submit"]'))).click()
    # Mantenemos la sesión
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="submit"]'))).click()
    # Esperamos a que entre a la intranet
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@id="_ctl0_toolbar_holder_localizador_rapido"]')))
    # Redirigimos a los descuentos
    driver.get('https://www.nexustours.com/Intranet/descuentos/default.aspx')
    # Terminamos la función
    return


def search_box(wait: WebDriverWait, box: str, active_value: str) -> None:
    time.sleep(2)
    # Buscamos el nombre de la estrategia
    discount_name = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@id="FNombreDescuento-inputEl"]')))
    discount_name.click()
    discount_name.send_keys(box)
    time.sleep(1.2)
    # Modificamos el filtro Activo/Inactivo
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//div[@id="ext-gen1220"]'))).click()
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//div[@data-qtip="{active_value}"]'))).click()
    # Buscamos
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//button[@id="button-1023-btnEl"]'))).click()
    # Esperamos a que cargue la búsqueda
    wait.until(ec.invisibility_of_element_located(
        (By.XPATH, '//div[id="loadmask-1068-msgEl"]')))
    time.sleep(5)
    # Terminamos la función
    return


def deactivate_box(wait: WebDriverWait, strategy: str, count: int) -> int:
    # Abrimos la edición
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//img[@data-qtip="Edit"]'))).click()
    # Comprobamos el nombre de la caja
    block_name = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//div[@id="nombreGrid-body"]')))
    name_box = block_name.find_element(By.XPATH, './div/table/tbody/tr[2]/td[2]/div').text
    # Comprobamos que el nombre coincida con la estrategia
    if name_box == strategy:
        # Desactivamos la caja
        wait.until(ec.visibility_of_element_located(
            (By.XPATH, '//input[@id="DescuentoActivo-inputEl"]'))).click()
        # Guardamos
        wait.until(ec.visibility_of_element_located(
            (By.XPATH, '//button[@id="guardarCerrar-btnEl"]'))).click()
        # Aceptamos
        wait.until(ec.visibility_of_element_located(
            (By.XPATH, '//button[@id="button-1005-btnEl"]'))).click()
        # Agregamos uno al contador
        count += 1
        time.sleep(5)
    # Terminamos la función
    return count


def close_driver(driver: WebDriver) -> None:
    # Cerramos el driver
    driver.close()
    # Quitamos la sesión del driver
    driver.quit()
    # Terminamos la función
    return


def run_deactivate(geckodriver_path: str, timeout: int, headless: bool, strategy: str, user: str,
                   use_password: str) -> None:
    # Obtenemos el driver
    driver, wait = get_driver(geckodriver_path, headless, timeout)
    # Iniciamos sesión
    sing_in(driver, wait, user, use_password)
    # Buscamos las cajas activas de la estrategia
    search_box(wait, strategy, "Active")
    # Contador de cajas
    box_count = 0
    # Comprobamos que tengamos cajas activas
    result_search = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//div[@id="tbtext-1065"]'))).text
    # Si no tenemos cajas activas
    if result_search == "No data to display":
        print("\t\t\t\tNo active boxes found for this strategy")
    # Si tenemos cajas activas
    else:
        # Buscamos el total de cajas a desactivar
        box_value = int(result_search.split()[-1])
        # Desactivamos caja por caja
        for _ in range(box_value):
            box_count = deactivate_box(wait, strategy, box_count)
        if box_count == box_value:
            print(f"\t\t\t\tSuccessfully deactivated: {box_count} discount boxes")
        else:
            print(f"\t\t\t\tDeactivated: {box_count} of {box_value} boxes")
    # Cerramos el driver
    close_driver(driver)
    # Terminamos la función
    return


def get_id_box(discount: float, strategy: str) -> str:
    # Menu de las cajas de descuento
    menu_box = {
        # Estrategia TRFSWGDIS
        'TRFSWGDIS 0.01': '10125',
        'TRFSWGDIS 0.02': '10126',
        'TRFSWGDIS 0.03': '10127',
        'TRFSWGDIS 0.04': '10128',
        'TRFSWGDIS 0.05': '10129',
        'TRFSWGDIS 0.06': '10130',
        'TRFSWGDIS 0.07': '10131',
        'TRFSWGDIS 0.08': '10132',
        'TRFSWGDIS 0.09': '10133',
        'TRFSWGDIS 0.1': '10134',
        'TRFSWGDIS 0.11': '10135',
        'TRFSWGDIS 0.12': '10136',
        'TRFSWGDIS 0.13': '10137',
        'TRFSWGDIS 0.14': '10138',
        'TRFSWGDIS 0.15': '10139',
        'TRFSWGDIS 0.16': '10140',
        'TRFSWGDIS 0.17': '10141',
        'TRFSWGDIS 0.18': '10142',
        'TRFSWGDIS 0.19': '10143',
        'TRFSWGDIS 0.2': '10144',
        'TRFSWGDIS 0.21': '10145',
        'TRFSWGDIS 0.22': '10146',
        'TRFSWGDIS 0.23': '10147',
        'TRFSWGDIS 0.24': '10148',
        'TRFSWGDIS 0.25': '10149',
        'TRFSWGDIS 0.26': '10150',
        'TRFSWGDIS 0.27': '10151',
        'TRFSWGDIS 0.28': '10152',
        'TRFSWGDIS 0.29': '10153',
        'TRFSWGDIS 0.3': '10154',
        'TRFSWGDIS 0.31': '10155',
        'TRFSWGDIS 0.32': '10156',
        'TRFSWGDIS 0.33': '10157',
        'TRFSWGDIS 0.34': '10158',
        'TRFSWGDIS 0.35': '10159',
        'TRFSWGDIS 0.36': '10160',
        'TRFSWGDIS 0.37': '10161',
        'TRFSWGDIS 0.38': '10162',
        'TRFSWGDIS 0.39': '10163',
        'TRFSWGDIS 0.4': '10164',
        'TRFSWGDIS 0.41': '10165',
        'TRFSWGDIS 0.42': '10166',
        'TRFSWGDIS 0.43': '10167',
        'TRFSWGDIS 0.44': '10168',
        'TRFSWGDIS 0.45': '10169',
        'TRFSWGDIS 0.46': '10170',
        'TRFSWGDIS 0.47': '10171',
        'TRFSWGDIS 0.48': '10172',
        'TRFSWGDIS 0.49': '10173',
        'TRFSWGDIS 0.5': '10174',
        # Estrategia TRFPVPAMDIS
        'TRFPVPAMDIS 0.01': '10183',
        'TRFPVPAMDIS 0.02': '10184',
        'TRFPVPAMDIS 0.03': '10185',
        'TRFPVPAMDIS 0.04': '10186',
        'TRFPVPAMDIS 0.05': '10187',
        'TRFPVPAMDIS 0.06': '10188',
        'TRFPVPAMDIS 0.07': '10189',
        'TRFPVPAMDIS 0.08': '10190',
        'TRFPVPAMDIS 0.09': '10191',
        'TRFPVPAMDIS 0.1': '10192',
        'TRFPVPAMDIS 0.11': '10193',
        'TRFPVPAMDIS 0.12': '10194',
        'TRFPVPAMDIS 0.13': '10195',
        'TRFPVPAMDIS 0.14': '10196',
        'TRFPVPAMDIS 0.15': '10197',
        'TRFPVPAMDIS 0.16': '10198',
        'TRFPVPAMDIS 0.17': '10199',
        'TRFPVPAMDIS 0.18': '10200',
        'TRFPVPAMDIS 0.19': '10201',
        'TRFPVPAMDIS 0.2': '10202',
        'TRFPVPAMDIS 0.21': '10203',
        'TRFPVPAMDIS 0.22': '10204',
        'TRFPVPAMDIS 0.23': '10205',
        'TRFPVPAMDIS 0.24': '10206',
        'TRFPVPAMDIS 0.25': '10207',
        'TRFPVPAMDIS 0.26': '10208',
        'TRFPVPAMDIS 0.27': '10209',
        'TRFPVPAMDIS 0.28': '10210',
        'TRFPVPAMDIS 0.29': '10211',
        'TRFPVPAMDIS 0.3': '10212',
        'TRFPVPAMDIS 0.31': '10213',
        'TRFPVPAMDIS 0.32': '10214',
        'TRFPVPAMDIS 0.33': '10215',
        'TRFPVPAMDIS 0.34': '10216',
        'TRFPVPAMDIS 0.35': '10217',
        'TRFPVPAMDIS 0.36': '10218',
        'TRFPVPAMDIS 0.37': '10219',
        'TRFPVPAMDIS 0.38': '10220',
        'TRFPVPAMDIS 0.39': '10221',
        'TRFPVPAMDIS 0.4': '10222',
        'TRFPVPAMDIS 0.41': '10223',
        'TRFPVPAMDIS 0.42': '10224',
        'TRFPVPAMDIS 0.43': '10225',
        'TRFPVPAMDIS 0.44': '10226',
        'TRFPVPAMDIS 0.45': '10227',
        'TRFPVPAMDIS 0.46': '10228',
        'TRFPVPAMDIS 0.47': '10229',
        'TRFPVPAMDIS 0.48': '10230',
        'TRFPVPAMDIS 0.49': '10231',
        'TRFPVPAMDIS 0.5': '10232',
        # Estrategia TRFPVPPMDIS
        'TRFPVPPMDIS 0.01': '10235',
        'TRFPVPPMDIS 0.02': '10236',
        'TRFPVPPMDIS 0.03': '10237',
        'TRFPVPPMDIS 0.04': '10238',
        'TRFPVPPMDIS 0.05': '10239',
        'TRFPVPPMDIS 0.06': '10240',
        'TRFPVPPMDIS 0.07': '10241',
        'TRFPVPPMDIS 0.08': '10242',
        'TRFPVPPMDIS 0.09': '10243',
        'TRFPVPPMDIS 0.1': '10244',
        'TRFPVPPMDIS 0.11': '10245',
        'TRFPVPPMDIS 0.12': '10246',
        'TRFPVPPMDIS 0.13': '10247',
        'TRFPVPPMDIS 0.14': '10248',
        'TRFPVPPMDIS 0.15': '10249',
        'TRFPVPPMDIS 0.16': '10250',
        'TRFPVPPMDIS 0.17': '10251',
        'TRFPVPPMDIS 0.18': '10252',
        'TRFPVPPMDIS 0.19': '10253',
        'TRFPVPPMDIS 0.2': '10254',
        'TRFPVPPMDIS 0.21': '10255',
        'TRFPVPPMDIS 0.22': '10256',
        'TRFPVPPMDIS 0.23': '10257',
        'TRFPVPPMDIS 0.24': '10258',
        'TRFPVPPMDIS 0.25': '10259',
        'TRFPVPPMDIS 0.26': '10260',
        'TRFPVPPMDIS 0.27': '10261',
        'TRFPVPPMDIS 0.28': '10262',
        'TRFPVPPMDIS 0.29': '10263',
        'TRFPVPPMDIS 0.3': '10264',
        'TRFPVPPMDIS 0.31': '10265',
        'TRFPVPPMDIS 0.32': '10266',
        'TRFPVPPMDIS 0.33': '10267',
        'TRFPVPPMDIS 0.34': '10268',
        'TRFPVPPMDIS 0.35': '10269',
        'TRFPVPPMDIS 0.36': '10270',
        'TRFPVPPMDIS 0.37': '10271',
        'TRFPVPPMDIS 0.38': '10272',
        'TRFPVPPMDIS 0.39': '10273',
        'TRFPVPPMDIS 0.4': '10274',
        'TRFPVPPMDIS 0.41': '10275',
        'TRFPVPPMDIS 0.42': '10276',
        'TRFPVPPMDIS 0.43': '10277',
        'TRFPVPPMDIS 0.44': '10278',
        'TRFPVPPMDIS 0.45': '10279',
        'TRFPVPPMDIS 0.46': '10280',
        'TRFPVPPMDIS 0.47': '10281',
        'TRFPVPPMDIS 0.48': '10282',
        'TRFPVPPMDIS 0.49': '10283',
        'TRFPVPPMDIS 0.5': '10284',
        # Estrategia TRFPVPFDIS
        'TRFPVPFDIS 0.01': '10291',
        'TRFPVPFDIS 0.02': '10292',
        'TRFPVPFDIS 0.03': '10293',
        'TRFPVPFDIS 0.04': '10294',
        'TRFPVPFDIS 0.05': '10295',
        'TRFPVPFDIS 0.06': '10296',
        'TRFPVPFDIS 0.07': '10297',
        'TRFPVPFDIS 0.08': '10298',
        'TRFPVPFDIS 0.09': '10299',
        'TRFPVPFDIS 0.1': '10300',
        'TRFPVPFDIS 0.11': '10301',
        'TRFPVPFDIS 0.12': '10302',
        'TRFPVPFDIS 0.13': '10303',
        'TRFPVPFDIS 0.14': '10304',
        'TRFPVPFDIS 0.15': '10305',
        'TRFPVPFDIS 0.16': '10306',
        'TRFPVPFDIS 0.17': '10307',
        'TRFPVPFDIS 0.18': '10308',
        'TRFPVPFDIS 0.19': '10309',
        'TRFPVPFDIS 0.2': '10310',
        'TRFPVPFDIS 0.21': '10311',
        'TRFPVPFDIS 0.22': '10312',
        'TRFPVPFDIS 0.23': '10313',
        'TRFPVPFDIS 0.24': '10314',
        'TRFPVPFDIS 0.25': '10315',
        'TRFPVPFDIS 0.26': '10316',
        'TRFPVPFDIS 0.27': '10317',
        'TRFPVPFDIS 0.28': '10318',
        'TRFPVPFDIS 0.29': '10319',
        'TRFPVPFDIS 0.3': '10320',
        'TRFPVPFDIS 0.31': '10321',
        'TRFPVPFDIS 0.32': '10322',
        'TRFPVPFDIS 0.33': '10323',
        'TRFPVPFDIS 0.34': '10324',
        'TRFPVPFDIS 0.35': '10325',
        'TRFPVPFDIS 0.36': '10326',
        'TRFPVPFDIS 0.37': '10327',
        'TRFPVPFDIS 0.38': '10328',
        'TRFPVPFDIS 0.39': '10329',
        'TRFPVPFDIS 0.4': '10330',
        'TRFPVPFDIS 0.41': '10331',
        'TRFPVPFDIS 0.42': '10332',
        'TRFPVPFDIS 0.43': '10333',
        'TRFPVPFDIS 0.44': '10334',
        'TRFPVPFDIS 0.45': '10335',
        'TRFPVPFDIS 0.46': '10336',
        'TRFPVPFDIS 0.47': '10337',
        'TRFPVPFDIS 0.48': '10338',
        'TRFPVPFDIS 0.49': '10339',
        'TRFPVPFDIS 0.5': '10340',
        # Estrategia TRFCCFDIS
        'TRFCCFDIS 0.01': '10342',
        'TRFCCFDIS 0.02': '10343',
        'TRFCCFDIS 0.03': '10344',
        'TRFCCFDIS 0.04': '10345',
        'TRFCCFDIS 0.05': '10346',
        'TRFCCFDIS 0.06': '10347',
        'TRFCCFDIS 0.07': '10348',
        'TRFCCFDIS 0.08': '10349',
        'TRFCCFDIS 0.09': '10350',
        'TRFCCFDIS 0.1': '10351',
        'TRFCCFDIS 0.11': '10352',
        'TRFCCFDIS 0.12': '10353',
        'TRFCCFDIS 0.13': '10354',
        'TRFCCFDIS 0.14': '10355',
        'TRFCCFDIS 0.15': '10356',
        'TRFCCFDIS 0.16': '10357',
        'TRFCCFDIS 0.17': '10358',
        'TRFCCFDIS 0.18': '10359',
        'TRFCCFDIS 0.19': '10360',
        'TRFCCFDIS 0.2': '10361',
        'TRFCCFDIS 0.21': '10362',
        'TRFCCFDIS 0.22': '10363',
        'TRFCCFDIS 0.23': '10364',
        'TRFCCFDIS 0.24': '10365',
        'TRFCCFDIS 0.25': '10366',
        'TRFCCFDIS 0.26': '10367',
        'TRFCCFDIS 0.27': '10368',
        'TRFCCFDIS 0.28': '10369',
        'TRFCCFDIS 0.29': '10370',
        'TRFCCFDIS 0.3': '10371',
        'TRFCCFDIS 0.31': '10372',
        'TRFCCFDIS 0.32': '10373',
        'TRFCCFDIS 0.33': '10374',
        'TRFCCFDIS 0.34': '10375',
        'TRFCCFDIS 0.35': '10376',
        'TRFCCFDIS 0.36': '10377',
        'TRFCCFDIS 0.37': '10378',
        'TRFCCFDIS 0.38': '10379',
        'TRFCCFDIS 0.39': '10380',
        'TRFCCFDIS 0.4': '10381',
        'TRFCCFDIS 0.41': '10382',
        'TRFCCFDIS 0.42': '10383',
        'TRFCCFDIS 0.43': '10384',
        'TRFCCFDIS 0.44': '10385',
        'TRFCCFDIS 0.45': '10386',
        'TRFCCFDIS 0.46': '10387',
        'TRFCCFDIS 0.47': '10388',
        'TRFCCFDIS 0.48': '10389',
        'TRFCCFDIS 0.49': '10390',
        'TRFCCFDIS 0.5': '10391',
        # Estrategia TRFF&FDIS
        'TRFF&FDIS 0.01': '10069',
        'TRFF&FDIS 0.02': '10070',
        'TRFF&FDIS 0.03': '10071',
        'TRFF&FDIS 0.04': '10072',
        'TRFF&FDIS 0.05': '10073',
        'TRFF&FDIS 0.06': '10074',
        'TRFF&FDIS 0.07': '10075',
        'TRFF&FDIS 0.08': '10076',
        'TRFF&FDIS 0.09': '10077',
        'TRFF&FDIS 0.1': '10078',
        'TRFF&FDIS 0.11': '10079',
        'TRFF&FDIS 0.12': '10080',
        'TRFF&FDIS 0.13': '10081',
        'TRFF&FDIS 0.14': '10082',
        'TRFF&FDIS 0.15': '10083',
        'TRFF&FDIS 0.16': '10084',
        'TRFF&FDIS 0.17': '10085',
        'TRFF&FDIS 0.18': '10086',
        'TRFF&FDIS 0.19': '10087',
        'TRFF&FDIS 0.2': '10088',
        'TRFF&FDIS 0.21': '10089',
        'TRFF&FDIS 0.22': '10090',
        'TRFF&FDIS 0.23': '10091',
        'TRFF&FDIS 0.24': '10092',
        'TRFF&FDIS 0.25': '10093',
        'TRFF&FDIS 0.26': '10094',
        'TRFF&FDIS 0.27': '10095',
        'TRFF&FDIS 0.28': '10096',
        'TRFF&FDIS 0.29': '10097',
        'TRFF&FDIS 0.3': '10098',
        'TRFF&FDIS 0.31': '10099',
        'TRFF&FDIS 0.32': '10100',
        'TRFF&FDIS 0.33': '10101',
        'TRFF&FDIS 0.34': '10102',
        'TRFF&FDIS 0.35': '10103',
        'TRFF&FDIS 0.36': '10104',
        'TRFF&FDIS 0.37': '10105',
        'TRFF&FDIS 0.38': '10106',
        'TRFF&FDIS 0.39': '10107',
        'TRFF&FDIS 0.4': '10108',
        'TRFF&FDIS 0.41': '10109',
        'TRFF&FDIS 0.42': '10110',
        'TRFF&FDIS 0.43': '10111',
        'TRFF&FDIS 0.44': '10112',
        'TRFF&FDIS 0.45': '10113',
        'TRFF&FDIS 0.46': '10114',
        'TRFF&FDIS 0.47': '10115',
        'TRFF&FDIS 0.48': '10116',
        'TRFF&FDIS 0.49': '10117',
        'TRFF&FDIS 0.5': '10118',
    }
    # Buscamos el ID de la caja
    id_box = menu_box.get(f'{strategy} {discount}', None)
    # Terminamos la función regresando el ID
    return id_box


def edit_box(wait: WebDriverWait) -> tuple[str, str]:
    # Editamos la caja
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//img[@data-qtip="Edit"]'))).click()
    # Obtenemos el nombre de la caja
    block_name = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//div[@id="nombreGrid-body"]')))
    name_box = block_name.find_element(By.XPATH, './div/table/tbody/tr[2]/td[2]/div').text
    # Obtenemos el valor de descuento
    value_box = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@id="valor-inputEl"]'))).get_attribute("value")
    # Terminamos la función regresando los valores
    return name_box, value_box


def apply_discounts(wait: WebDriverWait, strategy: str, discount: float, df: pd.DataFrame,
                    message: str, interval: int, id_box: str, driver: WebDriver,
                    timeout: int) -> tuple[str, list[int], list[int]]:
    # Lista de productos cargados
    ok_product = []
    # Lista de productos no cargados
    error_product = []
    # Editamos la caja de descuento
    name_box, value_box = edit_box(wait)
    if name_box == strategy and value_box == f"{discount*100:.0f}":
        # Comprobamos si tiene productos cargados previamente
        try:
            # Editamos el tiempo de espera
            wait = WebDriverWait(driver, (timeout / 2))
            product_remove = wait.until(ec.visibility_of_all_elements_located(
                (By.XPATH, '//img[@data-qtip="Remove"]')))
            # Eliminamos los productos
            for remove in product_remove:
                remove.click()
                time.sleep(0.2)
            # Volvemos con el tiempo de espera base
            wait = WebDriverWait(driver, timeout)
            # Guardamos los cambios
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//button[@id="guardarCerrar-btnEl"]'))).click()
            # Aceptamos los cambios
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//button[@id="button-1005-btnEl"]'))).click()
            time.sleep(2)
            # Editamos la caja
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//img[@data-qtip="Edit"]'))).click()
        except TimeoutException:
            pass
        # Marca de tiempo guardar y recargar
        nex_interval = datetime.now() + timedelta(minutes=interval)
        # Pasamos por cada uno de los productos
        for _, row in df.iterrows():
            # Comprobamos si pasaron más del tiempo máximo
            if datetime.now() >= nex_interval:
                # Guardamos los cambios
                wait.until(ec.visibility_of_element_located(
                    (By.XPATH, '//button[@id="guardarCerrar-btnEl"]'))).click()
                # Cambiamos el tiempo de espera máximo
                wait = WebDriverWait(driver, (timeout * 4))
                # Aceptamos los cambios
                wait.until(ec.visibility_of_element_located(
                    (By.XPATH, '//button[@id="button-1005-btnEl"]'))).click()
                # Regresamos al tiempo de espera base
                wait = WebDriverWait(driver, timeout)
                # Cerramos la sesión
                wait.until(ec.visibility_of_element_located(
                    (By.XPATH, '//li[@title="User"]'))).click()
                wait.until(ec.visibility_of_element_located(
                    (By.XPATH, '//li[@title="Exit"]'))).click()
                time.sleep(5)
                # Iniciamos sesión nuevamente con azure
                wait.until(ec.visibility_of_element_located(
                    (By.XPATH, '//a[@id="_ctl0_data_holder_LoginAzure"]'))).click()
                # Esperamos a que entre a la intranet
                wait.until(ec.visibility_of_element_located(
                    (By.XPATH, '//input[@id="_ctl0_toolbar_holder_localizador_rapido"]')))
                # Redirigimos a los descuentos
                driver.get('https://www.nexustours.com/Intranet/descuentos/default.aspx')
                # Buscamos la caja nuevamente
                time.sleep(2)
                search_box(wait, id_box, "Inactive")
                # Editamos la caja nuevamente
                time.sleep(2)
                edit_box(wait)
                # Guardamos la nueva marca de tiempo guardar y recargar
                nex_interval = datetime.now() + timedelta(minutes=interval)
            # Desplegamos la lista de tipo de producto
            type_product_container = wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//table[@id="TipoProductoPanel-triggerWrap"]')))
            type_product_container.find_element(By.XPATH, './tbody/tr/td[2]').click()
            # Seleccionamos producto traslados
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//div[@data-qtip="Traslados"]'))).click()
            # Desplegamos la lista de productos
            product_select_container = wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//table[@id="ProductosSeleccionables-triggerWrap"]')))
            product_select_container.find_element(By.XPATH, './tbody/tr/td[2]').click()
            # Buscamos el producto por su id
            try:
                # Cambiamos el tiempo máximo de espera
                wait = WebDriverWait(driver, (timeout / 2))
                wait.until(ec.visibility_of_element_located(
                    (By.CSS_SELECTOR, f'div[data-qtip$=" - {str(int(row["product_id"]))}"'))).click()
                # Regresamos al tiempo de espera base
                wait = WebDriverWait(driver, timeout)
            except TimeoutException:
                # Si no lo encontramos lo agregamos a la lista de error
                error_product.append(int(row["unique_id"]))
                # Saltamos al siguiente producto
                continue
            # Desplegamos la lista de opciones del producto
            option_select_container = wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//table[@id="ContratosServicio-triggerWrap"]')))
            option_select_container.find_element(By.XPATH, './tbody/tr/td[2]').click()
            # Buscamos la opción del producto
            try:
                # Cambiamos el tiempo máximo de espera
                wait = WebDriverWait(driver, (timeout / 2))
                wait.until(ec.visibility_of_element_located(
                    (By.CSS_SELECTOR, f'div[data-qtip^="{str(int(row["option_id"]))} -"'))).click()
                # Regresamos al tiempo de espera base
                wait = WebDriverWait(driver, timeout)
            except TimeoutException:
                # Si no lo encontramos lo agregamos a la lista de error
                error_product.append(int(row["unique_id"]))
                # Saltamos al siguiente producto
                continue
            # Cargamos el producto en la caja
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//div[@id="btnCargarProductos"]'))).click()
            # Agregamos el tour a la lista de cargados correctamente
            ok_product.append(int(row["unique_id"]))
        # Mostramos el resultado
        if len(ok_product) == len(df):
            message += "\t\t\t\tAll products were successfully loaded\n"
        else:
            message += (f"\t\t\t\tSuccessfully loaded: {len(ok_product)}\n"
                        f"\t\t\t\tFailed to load: {len(error_product)}\n"
                        f"\t\t\t\tFailed IDs: {error_product}\n")
        # Sí tenemos minimo un producto cargado
        if len(ok_product) > 0:
            # Cambiamos la fecha máxima de booking
            booking_date = wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//input[@id="FechaReservaHasta-inputEl"]')))
            booking_date.click()
            booking_date.clear()
            booking_date.send_keys((datetime.today() + timedelta(30)).strftime('%d/%m/%Y'))
            time.sleep(1.5)
            # Activamos la caja de descuentos
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//input[@id="DescuentoActivo-inputEl"]'))).click()
            # Guardamos los cambios
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//button[@id="guardarCerrar-btnEl"]'))).click()
            # Aceptamos los cambios
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//span[@id="button-1005-btnInnerEl"]'))).click()
            message += "\t\t\t\t✅ Box activated successfully"
        # Si no tenemos como minimo un producto
        else:
            # Cerramos la caja sin guardar
            wait.until(ec.visibility_of_element_located(
                (By.XPATH, '//button[@id="button-1263-btnEl"]'))).click()
            message += "\t\t\t\t❌ Box activation failed"
    # Terminamos la función
    return message, ok_product, error_product


def run_discount(geckodriver_path: str, timeout: int, headless: bool, strategy: str, df: pd.DataFrame, value: str,
                 discount: float, interval: int, user: str, use_password: str) -> tuple[list[int], list[int]]:
    # Filtramos la base de datos conforme al descuento
    df = df[df[f'{value}_final_discount'] == discount]
    # Declaramos las listas
    ok_product = []
    error_product = []
    # Comprobamos que tengamos descuentos a cargar
    if not df.empty:
        # Obtenemos el ID de la caja de descuento
        id_box = get_id_box(discount, strategy)
        message = f"\t\t\t\tDiscount {discount*100:.0f}% | Box ID {id_box} | Upload: {len(df)} products\n"
        # Obtenemos el driver
        driver, wait = get_driver(geckodriver_path, headless, timeout)
        # Iniciamos sesión
        sing_in(driver, wait, user, use_password)
        # Buscamos la caja de descuento
        search_box(wait, id_box, "Inactive")
        # Aplicamos los descuentos
        message, ok_product, error_product = apply_discounts(wait, strategy, discount, df, message, interval,
                                                             id_box, driver, timeout)
        # Cerramos el driver
        close_driver(driver)
        # Imprimimos el resultado
        print(message)
    # Terminamos la función
    return ok_product, error_product


def save_info(df: pd.DataFrame, ok_: list[int], error_: list[int], db_user: str, db_user_password: str,
              db_host: str, db_port: int, db_name: str) -> None:
    # Verificamos el tipo de dato del dataframe
    df['unique_id'] = df['unique_id'].astype(int)
    # Filtramos el dataframe
    df_ok = df[df['unique_id'].isin(ok_)]
    df_err = df[df['unique_id'].isin(error_)]
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Agregamos el dataframe a la base de datos
    df.to_sql('final_discounts', con=engine, if_exists='replace', index=False)
    df_ok.to_sql('final_discounts_ok', con=engine, if_exists='replace', index=False)
    df_err.to_sql('final_discounts_error', con=engine, if_exists='replace', index=False)
    # Terminamos la función
    return


def run_scraping(df: pd.DataFrame, strategy_list: list[str], timeout: int, headless: bool, interval: int,
                 max_workers: int, user: str, use_password: str, db_user: str, db_user_password: str,
              db_host: str, db_port: int, db_name: str) -> None:
    # Definimos el diccionario de datos
    dict_strategies = {
        # Estrategia de Sunwing
        "SWG": {"name": "TRFSWGDIS", "value": "swg"},
        # Estrategia de PVP
        "PVPAM": {"name": "TRFPVPAMDIS", "value": "pvp"},
        "PVPPM": {"name": "TRFPVPPMDIS", "value": "pvp"},
        "PVP": {"name": "TRFPVPFDIS", "value": "pvp"},
        # Estrategia para CC
        "CC": {"name": "TRFCCFDIS", "value": "pvp"},
        # Estrategia de Friends and Family
        "F&F": {"name": "TRFF&FDIS", "value": "ff"}
    }
    # Comprobamos que el dataframe no este vacío
    if not df.empty:
        # Definimos la ruta del geckodriver
        geckodriver_path = GeckoDriverManager().install()
        # Pasamos por cada estrategia de descuentos
        for strategy in strategy_list:
            print(f"\t\t• Strategy: {strategy}")
            # Filtramos los descuentos a aplicar por estrategia
            df_strategy = df[df[f'{dict_strategies[strategy]["value"]}_aplay'] == 1]
            # Obtenemos los valores únicos de descuentos
            print_unique_discounts = sorted(df_strategy[f"{dict_strategies[strategy]['value']}"
                                                        f"_final_discount"].unique())
            # Convertimos a string para imprimir
            val_str = ", ".join([f"{v * 100:.0f}%" for v in print_unique_discounts])
            print(f"\t\t\tDiscounts to upload: {len(df_strategy)}\n\t\t\tUnique discounts: "
                  f"{len(print_unique_discounts)}\n\t\t\tValues: {val_str}")
            # Declaramos las listas para guardar los ids cargados y no cargados
            final_ok_products = []
            final_error_products = []
            # Desactivamos las cajas de la estrategia
            print(f"\t\t\tScraping to deactivate strategy discounts...")
            run_deactivate(geckodriver_path, timeout, headless, dict_strategies[strategy]['name'], user, use_password)
            # Obtenemos los descuentos unicos ordenados por su frecuencia
            unique_discounts = list(df_strategy[f"{dict_strategies[strategy]['value']}"
                                                f"_final_discount"].value_counts().index)
            val_str_order = ", ".join([f"{v * 100:.0f}%" for v in unique_discounts])
            print(f"\t\t\tOrder: {val_str_order}")
            # Cargamos descuento por descuento
            print(f"\t\t\tScraping to apply discounts...")
            with ProcessPoolExecutor(max_workers) as executor:
                futures = []
                for discount in unique_discounts:
                    futures.append(
                        executor.submit(run_discount,geckodriver_path, timeout, headless,
                                        dict_strategies[strategy]['name'], df_strategy,
                                        dict_strategies[strategy]['value'], discount, interval, user, use_password)
                    )
                # Procesamos los resultados
                for future in as_completed(futures):
                    ok_product, error_product = future.result()
                    if ok_product: final_ok_products.extend(ok_product)
                    if error_product: final_error_products.extend(error_product)
            # Filtramos y guardamos los nuevos csv
            save_info(df_strategy, final_ok_products, final_error_products, db_user, db_user_password, db_host,
                      db_port, db_name)
    # Terminamos la función
    return


# Función main
def main_discounts(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str,
                   strategy_list: list[str], timeout: int, headless: bool, interval: int,
                   max_workers: int, user: str, use_password: str) -> Result:
    print("\t[Discounts Block] Discount application 🚀")
    # Obtenemos los descuentos a cargar
    try:
        df = get_strategies(db_user, db_user_password, db_host, db_port, db_name)
        print(f"\t • Strategies successfully retrieved. Rows loaded: {len(df)}")
    except Exception as e:
        print("\t ❌ Failed to retrieve strategies from database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Aplicamos los descuentos
    try:
        print("\t • Upload process initiated: preparing discounts for upload...")
        run_scraping(df, strategy_list, timeout, headless, interval, max_workers, user, use_password, db_user,
                     db_user_password, db_host, db_port, db_name)
    except Exception as e:
        print("\t ❌ Failed to apply discounts")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Terminamos la función main
    return Result(result=True)