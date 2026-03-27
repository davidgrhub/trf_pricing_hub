from concurrent.futures import ProcessPoolExecutor, as_completed
from selenium.webdriver.support import expected_conditions as ec
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from sqlalchemy import create_engine, text
from dataclasses import dataclass
from selenium import webdriver
from datetime import datetime
import pandas as pd
import platform
import warnings
import shutil
import time
import os


# Clase para el resultado del bloque
@dataclass
class Result:
    result: bool
    error: str | None = None


# Funciones auxiliares
def get_paths() -> tuple[str, str]:
    # Definimos la ruta principal
    folder_path = os.getcwd()
    # Definimos la ruta de las descargas
    downloads_path = os.path.join(folder_path, 'downloads')
    # Definimos la ruta del geckodriver
    geckodriver_path = GeckoDriverManager().install()
    # Terminamos la función regresando los paths
    return geckodriver_path, downloads_path


def recreate_folder(path: str) -> None:
    # Comprobamos si existe la carpeta
    if os.path.exists(path):
        # Eliminamos la carpeta
        shutil.rmtree(path)
    # Creamos la carpeta
    os.mkdir(path)
    # Terminamos la función
    return


def get_activate_delegations(db_user: str, db_user_password: str, db_host: str, db_port: int,
                             db_name: str) -> tuple[dict[int, str], list[str]]:
    # Cadena de conexión
    connection_string = f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}"
    # Creamos el engine
    engine = create_engine(connection_string)
    # Creamos la cadena de petición
    query = text("SELECT delegation_id, delegation_name FROM delegations WHERE is_active = 1")
    # Creamos el diccionario y la lista final
    delegations_dict = {}
    delegation_list = []
    # Creamos la conexión
    with engine.connect() as conn:
        result = conn.execute(query).fetchall()
    # Creamos el diccionario y la lista con el resultado
    for delegation_id, delegation_name in result:
        delegations_dict[delegation_name] = delegation_id
        delegation_list.append(delegation_name)
    # Terminamos la función regresando el diccionario y la lista de nombres
    return delegations_dict, delegation_list


# Funciones para scraping
def get_driver(geckodriver_path: str, headless: bool, downloads_path: str, delegation: str,
               timeout: int) -> tuple[webdriver, WebDriverWait]:
    # Declaramos si el sistema operativo es windows
    is_windows = platform.system() == "Windows"
    # Declaramos el servicio del driver
    service = Service(geckodriver_path)
    # Configuramos las opciones
    options = webdriver.FirefoxOptions()
    options.set_preference("intl.accept_languages", "en-US,en")
    options.add_argument("-private-window")
    # firefox_exe = "/usr/bin/firefox-esr" if not is_windows else r"C:\Program Files\Mozilla Firefox\firefox.exe"
    # options.binary_location = firefox_exe
    # Configuramos el headless
    if not (is_windows and headless is False):
        options.add_argument("--headless")
    # Opciones de descarga
    temp_path = os.path.join(downloads_path, delegation)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", temp_path)
    options.set_preference("browser.download.useDownloadDir", True)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    # Iniciamos el driver
    driver = webdriver.Firefox(options=options, service=service)
    # Ingresamos el tiempo de espera
    wait = WebDriverWait(driver, timeout)
    # Terminamos la función regresando driver y wait
    return driver, wait


def sing_in(wait: WebDriverWait, user_mail: str, user_password: str) -> None:
    # Ingresamos el correo
    mail = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@id="email"]')))
    mail.click()
    mail.send_keys(user_mail)
    time.sleep(1.5)
    # Seleccionamos submit
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//button[@id="submitBtn"]'))).click()
    # Ingresamos la contraseña
    password = wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="password"]')))
    password.click()
    password.send_keys(user_password)
    time.sleep(1.5)
    # Seleccionamos iniciar sesión
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="submit"]'))).click()
    # Mantenemos la sesión iniciada
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//input[@type="submit"]'))).click()
    # Terminamos la función
    return


def filter_delegation(driver: webdriver, timeout: int, delegation: str) -> bool:
    # Cambiamos el tiempo de espera en este bloque
    wait = WebDriverWait(driver, (timeout * 10))
    # Desplegamos la lista de delegaciones
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, '//i[@class="dropdown-chevron powervisuals-glyph chevron-down"]'))).click()
    # Contador auxiliar
    aux_count = 1
    # Listado auxiliar de delegaciones
    aux_delegation_list = []
    # Variable de control
    flag = False
    # Repasamos las delegaciones del filtro
    while True:
        # Guardamos en una variable temporal
        temp_element = wait.until(ec.visibility_of_element_located(
            (By.XPATH, f'(//span[@class="slicerText"])[{aux_count}]')))
        # Comprobamos que no este la delegación en la lista
        if not temp_element.text in aux_delegation_list:
            # Agregamos a la lista
            aux_delegation_list.append(temp_element.text)
            # Si la delegación es la que buscamos
            if temp_element.text == delegation:
                # Obtenemos el estado de la opción
                val = wait.until(ec.visibility_of_element_located(
                    (By.XPATH, f'(//div[@class="slicerItemContainer"][@title="{temp_element.text}"])')))
                # Comprobamos que no este seleccionada la opción
                if val.get_attribute('aria-selected') == 'false' or val.get_attribute('aria-checked') == 'false':
                    # Seleccionamos la delegación
                    wait.until(ec.visibility_of_element_located(
                        (By.XPATH, f'(//span[@class="slicerText"])[{aux_count}]'))).click()
                # Salimos del while
                flag = True
                break
            # Si la delegación no es la que buscamos
            else:
                # Pasamos a la siguiente opción
                webdriver.ActionChains(driver).send_keys(Keys.DOWN).perform()
                time.sleep(1.2)
                # Sumamos el contador como máximo 10 y lo mantenemos asi
                if aux_count < 7:
                    aux_count += 1
        # Si la opción ya se encuentra en la lista
        elif temp_element.text in aux_delegation_list:
            # Cerramos el ciclo while
            break
    # Cerramos los filtros
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//div[@aria-label="Power BI Report"]'))).click()
    # Terminamos la función regresando la bandera
    return flag


def download_data(driver: webdriver, timeout: int) -> None:
    # Declaramos el tiempo máximo de espera del bloque
    wait = WebDriverWait(driver, timeout)
    # Seleccionamos más opciones
    more_options = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//button[@data-testid="visual-more-options-btn"]')))
    driver.execute_script("arguments[0].click();", more_options)
    # Seleccionamos exportar datos
    export_data = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//button[@data-testid="pbimenu-item.Export data"]')))
    driver.execute_script("arguments[0].click();", export_data)
    # Seleccionamos exportar
    export = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//button[@data-testid="export-btn"]')))
    driver.execute_script("arguments[0].click();", export)
    # Cambiamos el tiempo máximo de espera
    wait = WebDriverWait(driver, (timeout * 10))
    # Esperamos a que se descargue el archivo
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//h2[@data-testid="toast-notification-title" and '
                   f'normalize-space(text())="Successful export"]')))
    time.sleep(2)
    # Terminamos la función
    return


def refactor_data(downloads_path: str, path_delegation: str, new_name: str, deleted_temp: bool) -> bool:
    # Declaramos las rutas
    data_path = os.path.join(downloads_path, path_delegation, 'data.xlsx')
    refactor_path = os.path.join(downloads_path, f'{new_name}.xlsx')
    time.sleep(10)
    # Comprobamos que el archivo exista
    if os.path.exists(data_path):
        # Renombramos y reubicamos el archivo
        os.rename(data_path, refactor_path)
        if deleted_temp:
            # Eliminamos la carpeta temporal
            shutil.rmtree(os.path.join(downloads_path, path_delegation))
        # Terminamos la función regresando el booleano
        return True
    else:
        # Terminamos la función regresando el booleano
        return False


def run_scraping_contracts(delegation: str, geckodriver_path: str, headless: bool, downloads_path: str,
                 timeout: int, user_mail: str, user_password: str) -> None:
    # Iniciamos el log
    print_value = f"\t\t{delegation}:"
    # Inicializamos el driver
    driver, wait = get_driver(geckodriver_path, headless, downloads_path, delegation, timeout)
    # Manejo de error para cerrar el driver
    try:
        # Ingresamos a la url del dash
        driver.get('https://app.powerbi.com/links/E3XWJznNTp?ctid=34b7220f-ddb0-49fb-b389-f4b8d3e1ec9a&pbi_source='
                   'linkShare&bookmarkGuid=da90d0e9-4fc0-433f-a486-eacf4b77d50d')
        # Iniciamos sesión en BI
        sing_in(wait, user_mail, user_password)
        print_value += "\n\t\t\tLogged in successfully"
        # Filtramos la delegacion
        if filter_delegation(driver, timeout, delegation):
            print_value += "\n\t\t\tDelegation was found"
            # Descargamos los contratos de la delegación
            download_data(driver, timeout)
            print_value += "\n\t\t\tReport exported successfully"
            # Movemos el archivo descargado y lo renombramos
            if refactor_data(downloads_path, delegation, delegation, True):
                print_value += "\n\t\t\t✅ Data was refactored successfully"
            # Si no encontramos el archivo descargado
            else:
                print_value += "\n\t\t\t⚠️ No data found"
            # Salimos del scraping
            driver.close()
            driver.quit()
        # Si no encontramos la delegacion
        else:
            print_value += "\n\t\t\t⚠️ Delegation was not found"
            # Salimos del scraping
            driver.close()
            driver.quit()
    except TimeoutError:
        # Salimos de nuestro scraping cerrando el driver y salimos
        driver.close()
        driver.quit()
        print_value += "\n\t\t\t❌ Scraping failed"
    # Imprimimos le resultado
    print(print_value)
    # Terminamos la función
    return


def download_table(driver: webdriver, wait: WebDriverWait, value: int, timeout: int) -> None:
    # Seleccionamos la tabla
    table = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'(//div[@class="vcBody themableBackgroundColor themableBorderColorSolid sub-selectable '
                   f'ng-star-inserted"])[{value}]')))
    driver.execute_script("arguments[0].click();", table)
    # Seleccionamos las opciones
    options = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'(//button[@data-testid="visual-more-options-btn"])[1]')))
    driver.execute_script("arguments[0].click();", options)
    # Seleccionamos las opciones de exportar
    export_options = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'(//button[@data-testid="pbimenu-item.Export data"])[1]')))
    driver.execute_script("arguments[0].click();", export_options)
    # Exportamos
    export = wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'(//button[@data-testid="export-btn"])[1]')))
    driver.execute_script("arguments[0].click();", export)
    # Cambiamos el tiempo máximo de espera
    wait = WebDriverWait(driver, (timeout * 10))
    # Esperamos a que se descargue el archivo
    wait.until(ec.visibility_of_element_located(
        (By.XPATH, f'//h2[@data-testid="toast-notification-title" and '
                   f'normalize-space(text())="Successful export"]')))
    time.sleep(2)
    # Terminamos la función
    return


def run_scraping_percentile(geckodriver_path: str, headless: bool, downloads_path: str, timeout: int,
                            user_mail: str, user_password: str) -> None:
    # Inicializamos el driver
    driver, wait = get_driver(geckodriver_path, headless, downloads_path, "Percentile", timeout + 60)
    # Manejo de error para cerrar el driver
    try:
        # Ingresamos a la url del dash
        driver.get('https://app.powerbi.com/links/bk3CytVy-l?ctid=34b7220f-ddb0-49fb-b389-f4b8d3e1ec9a&'
                   'pbi_source=linkShare&bookmarkGuid=e8e0997d-4f39-47e1-a06a-cc3f4e3e2465')
        # Iniciamos sesión en BI
        sing_in(wait, user_mail, user_password)
        print("\t\tLogged in successfully")
        # Lista de percentiles
        percentile_list = ['Percentile_7', 'Percentile_30', 'Percentile_110']
        # Procesamos cada una de las tablas
        for i, percentile in enumerate(percentile_list):
            print(f"\t\t • {percentile}:")
            # Descargamos la tabla correspondiente
            download_table(driver, wait, i + 1, timeout)
            print("\t\t\tReport exported successfully")
            # Movemos el archivo descargado y lo renombramos
            if refactor_data(downloads_path, f"Percentile", percentile, i + 1 == len(percentile_list)):
                print("\t\t\t✅ Data was refactored successfully")
            # Si no encontramos el archivo descargado
            else:
                print("\t\t\t⚠️ No data found")
        # Salimos del scraping
        driver.close()
        driver.quit()
    except TimeoutError:
        # Salimos de nuestro scraping cerrando el driver y salimos
        driver.close()
        driver.quit()
        print("\t\t❌ Scraping failed")
    # Terminamos la función
    return


# Funciones de procesado
def compute_unique_id(row: pd.Series) -> int:
    # Máximo valor de un int
    max_int = np.iinfo(int).max
    srt = int(row['id_srt'])
    ops = int(row['id_ops'])
    if srt == ops:
        return srt
    try:
        val = int(f"{srt}{ops}")
    except (ValueError, OverflowError):
        return np.nan
    return val if val <= max_int else np.nan


def clean_percentile(df: pd.DataFrame) -> pd.DataFrame:
        # Eliminamos las filas que no son datos
        df = df.iloc[:-3]
        # Convertimos a numérico
        df['id_srt'] = pd.to_numeric(df['id_srt'], errors='coerce')
        df['id_ops'] = pd.to_numeric(df['id_ops'], errors='coerce')
        # Eliminamos las filas NaN
        df = df.dropna(subset=['id_srt', 'id_ops']).copy()
        # Aplicamos, eliminamos filas inválidas y convertimos a int64
        df['unique_id_percentile'] = df.apply(compute_unique_id, axis=1)
        df = df.dropna(subset=['unique_id_percentile']).copy()
        df['unique_id_percentile'] = df['unique_id_percentile'].astype(int)
        # Regresamos el dataframe
        return df


def get_percentile_data(downloads_path: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Leemos el archivo de percentil de 7 dias
    df_7 = pd.read_excel(os.path.join(downloads_path, 'Percentile_7.xlsx'))
    # Leemos el archivo de percentil de 30 dias
    df_30 = pd.read_excel(os.path.join(downloads_path, 'Percentile_30.xlsx'))
    # Leemos el archivo de percentil de 110 dias
    df_110 = pd.read_excel(os.path.join(downloads_path, 'Percentile_110.xlsx'))
    # Limpiamos los df
    df_7 = clean_percentile(df_7)
    df_30 = clean_percentile(df_30)
    df_110 = clean_percentile(df_110)
    # Terminamos la función regresando los dataframes de percentiles
    return df_7, df_30, df_110


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # Convertimos los nombres de columnas a nombres válidos
    df.columns = (
        df.columns
        .str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        .str.replace(r'\s+', '_', regex=True).str.replace(r'[^\w]', '', regex=True)
    )
    # Eliminamos las últimas dos filas
    df = df.iloc[:-2]
    # Creamos una columna de ids unicos
    df['unique_id'] = df['product_id'].astype(int).astype(str) + df['option_id'].astype(int).astype(str)
    # Filtramos los servicios
    df = df[df['contract_suplement'] == 'Service']
    # Obtenemos la fecha actual
    current_date = datetime.now()
    # Filtramos los datos con fecha de contrato de servicio válidos
    df = df[((df['fechainisc'] <= current_date) & (df['fechafinsc'] >= current_date))]
    # Filtramos por exclusion de nombres de producto
    exclusions = ['OFF', 'INACTIVO', 'INACTIVADO', 'Interzone', 'Interhotel', 'Grupos', 'Groups', 'Upgrade',
                  'Open Service', 'Interzonas', 'Ports', 'Insurance', 'Special', 'Disposal', 'Interzona', 'TEST',
                  'Disposition', 'Ferry', 'Uso Operativo', 'Travelers Assistance']
    mask = ~df['product_name'].str.contains('|'.join(map(re.escape, exclusions)), case=False, na=False)
    df = df[mask]
    # Mapeo de valores para reemplazar en la columna id_unico
    map_ids = {
        # Cancún
        "1043736360": "1042936256",
        # Jamaica
        "1103841064": "36068276", "1103841065": "36068277", "1103841063": "36068275", "1103841066": "36068278",
        "1103841067": "36068279", "699522377": "23217262", "699622386": "23417256", "699522371": "232943",
        "699622380": "234942", "699522372": "232951", "699622381": "234960", "699522373": "232955",
        "699622382": "234962", "699522374": "232961", "699622383": "234965", "699522375": "232963",
        "699622384": "234966", "699522376": "232964", "699622385": "234967"
    }
    # Reemplazamos los valores en la columna id_unico utilizando el mapeo
    data['unique_id'] = data['unique_id'].replace(map_ids)
    # Ordenamos los datos por "unique_id"
    df = df.sort_values('unique_id', ascending=True)
    # Terminamos la función regresando el dataframe
    return df


def generate_final_contracts(df: pd.DataFrame, df_7: pd.DataFrame, df_30: pd.DataFrame, df_110: pd.DataFrame,
                             delegations_dict: dict[int, str]) -> pd.DataFrame:
    # Preparación de Mapas de Percentiles
    map7_usd = df_7.set_index('unique_id_percentile')['Percentil_Cost_USD'].to_dict()
    map7_pax = df_7.set_index('unique_id_percentile')['Percentil_costo_x_pax'].to_dict()
    map30_usd = df_30.set_index('unique_id_percentile')['Percentil_Cost_USD'].to_dict()
    map30_pax = df_30.set_index('unique_id_percentile')['Percentil_costo_x_pax'].to_dict()
    map110_usd = df_110.set_index('unique_id_percentile')['Percentil_Cost_USD'].to_dict()
    map110_pax = df_110.set_index('unique_id_percentile')['Percentil_costo_x_pax'].to_dict()
    def lookup_with_fallback(uid, *maps):
        for key_ in (int(uid), str(uid)):
            for m in maps:
                if key_ in m: return m[key_]
        return np.nan
    # Lista de filas
    rows = []
    # Procesamiento por ID Único
    for unique_id in df['unique_id'].unique():
        is_data = df[df['unique_id'] == unique_id]
        # Logica del contrato pvp
        is_pvp = is_data[is_data['contract_type'] == 'PVP'].sort_values('rango_minpax').reset_index(drop=True)
        # Si no tenemos saltamos
        if is_pvp.empty:
            continue
        # Obtenemos la primera fila
        first_row = is_pvp.iloc[0]
        # Determinamos si usamos Base o Adult
        key = None
        if pd.notna(first_row['sale_base_usd']) and pd.notna(first_row['cost_base_usd']):
            key = 'base'
        elif pd.notna(first_row['sale_adu_usd']) and pd.notna(first_row['cost_adu_usd']):
            key = 'adu'
        # Si tenemos precios no validos saltamos
        if not key:
            continue
        # Obtenemos el costo y el precio de venta
        cost_contract = round(first_row[f'cost_{key}_usd'], 2)
        sale_pvp = round(first_row[f'sale_{key}_usd'], 2)
        # Si es 'Shared', buscamos en mapas de PAX, si no, en USD
        if 'Shared' in str(first_row['service_type']):
            cost_pct = lookup_with_fallback(unique_id, map7_pax, map30_pax, map110_pax)
        else:
            cost_pct = lookup_with_fallback(unique_id, map7_usd, map30_usd, map110_usd)
        # Redondeamos el costo percentil
        cost_pct = round(cost_pct, 2) if pd.notna(cost_pct) else np.nan
        # El costo final es el percentil, si no existe, el del contrato
        final_cost = cost_pct if pd.notna(cost_pct) else cost_contract
        margin = round((sale_pvp - final_cost) / sale_pvp, 2) if sale_pvp != 0 else 0
        # Logica para contratos SWG/VEX
        is_swg = is_data[is_data['contract_type'] == 'SWG/VEX']
        sale_swg = np.nan
        # Si tenemos contratos SWG/VEX
        if not is_swg.empty:
            is_swg = is_swg.sort_values(
                by=['rango_minpax', 'sale_base_usd', 'sale_adu_usd'],
                ascending=[True, False, False]
            ).reset_index(drop=True)
            # Seleccionamos la primera fila de los contratos SWG
            row_swg = is_swg.iloc[0]
            # Intentamos obtener precio de venta SWG
            if pd.notna(row_swg['sale_base_usd']):
                sale_swg = round(row_swg['sale_base_usd'], 2)
            elif pd.notna(row_swg['sale_adu_usd']):
                sale_swg = round(row_swg['sale_adu_usd'], 2)
        # Construcción de la nueva fila
        rows.append({
            'unique_id': int(unique_id),
            'delegation_id': delegations_dict.get(first_row['delegation']),
            'delegation_name': first_row['delegation'],
            'service_type': first_row['service_type'],
            'supplier': first_row['supplier'],
            'product_id': int(first_row['product_id']),
            'product_name': first_row['product_name'],
            'option_id': first_row['option_id'],
            'option_name': first_row['option_name'],
            'rango_minpax': first_row['rango_minpax'],
            'rango_maxpax': first_row['rango_maxpax'],
            'base_or_adult': key.upper(),
            'cost_contract': cost_contract,
            'cost_percentile': cost_pct,
            'final_cost': final_cost,
            'sale_swg': sale_swg,
            'sale_pvp': sale_pvp,
            'margin': margin
        })
    # Terminamos la funcion regresando las filas en un Dataframe
    return pd.DataFrame(rows)


def process_data(delegation_list: list[str], downloads_paths: str,
                 delegations_dict: dict[int, str]) -> pd.Dataframe:
    # Ignoramos Warnings
    warnings.filterwarnings("ignore")
    # Lista de dataframes
    all_dfs = []
    # Leemos y procesamos la data de los percentiles
    df_7, df_30, df_110 = get_percentile_data(downloads_paths)
    # Procesamos cada una de las delegaciones
    for delegation in delegation_list:
        # Creamos el path del archivo
        excel_path = os.path.join(downloads_paths, f"{delegation}.xlsx")
        # Comprobamos si existe el archivo
        if os.path.exists(excel_path):
            # Leemos el archivo
            df = pd.read_excel(os.path.join(downloads_paths, f'{delegation}.xlsx'))
            # Limpiamos los contratos
            df = clean_data(df)
            # Reestructura de contratos
            df = get_final_contracts(df, delegations_dict, df_7, df_30, df_110)
            # Guardamos en la lista de dfs
            all_dfs.append(df)
        else:
            print(f"\t\tFile not found for delegation {delegation}")
    # Unimos todos en un dataframe final
    final_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    # Terminamos la función regresando el dataframe final
    return final_df


# Función para subir la data
def upload_data(df: pd.DataFrame, db_user: str, db_user_password: str, db_host: str, db_port: int,
                db_name: str) -> None:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Agregamos el dataframe a la base de datos
    df.to_sql('final_contracts', con=engine, if_exists='replace', index=False)
    # Terminamos la función
    return


# Función main
def main_contracts(db_user: str, db_user_password: str, db_host: str, db_port: str, db_name: str,
                   headless: bool, timeout: int, user_mail: str, user_password: str, max_workers: int) -> Result:
    print("\t[Contracts Block] Scraping & Processing 📝")
    # Obtenemos los paths a usar
    try:
        geckodriver_path, downloads_path = get_paths()
        print(f"\t • Block paths:\n"
              f"\t\t🦎 geckodriver: {geckodriver_path}\n"
              f"\t\t📥 downloads: {downloads_path}")
    except Exception as e:
        print("\t ❌ Failed to retrieve block paths")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Recreamos la carpeta de descargas
    try:
        recreate_folder(downloads_path)
        print(f"\t • Downloads folder recreated successfully")
    except Exception as e:
        print(f"\t ❌ Failed to recreate downloads folder")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Obtenemos la lista de delegaciones activas y su diccionario
    try:
        delegations_dict, delegation_list = get_activate_delegations(db_user, db_user_password, db_host, db_port,
                                                                     db_name)
        print(f"\t • Delegations loaded successfully ({len(delegation_list)})")
    except Exception as e:
        print(f"\t ❌ Failed to get delegation list")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Iniciamos el scraping de las delegaciones
    try:
        print("\t • Starting delegations scraping")
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(run_scraping_contracts, delegation, geckodriver_path, headless, downloads_path,
                                timeout, user_mail, user_password)
                for delegation in delegation_list
            ]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    print(f"\t\t❌ Worker failed: {type(e).__name__}: {e}")
    except Exception as e:
        print("\t ❌ Failed to perform scraping for contract download")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Iniciamos el scraping de los percentiles
    try:
        print("\t • Starting percentile scraping")
        run_scraping_percentile(geckodriver_path, headless, downloads_path, timeout, user_mail, user_password)
    except Exception as e:
        print("\t ❌ Failed to perform scraping for percentile download")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Iniciamos el procesado de las delegaciones
    try:
        print("\t • Starting delegations processing")
        final_contracts = process_data(delegation_list, downloads_path, delegations_dict)
        print("\t\tFinal contracts generated successfully")
    except Exception as e:
        print("\t ❌ Failed to generate final contracts")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Iniciamos el proceso para subir la data en la base de datos
    try:
        print("\t • Uploading final contracts to database")
        upload_data(final_contracts, db_user, db_user_password, db_host, db_port, db_name)
        print("\t\tData uploaded successfully")
    except Exception as e:
        print("\t ❌ Failed to upload data to database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Terminamos la función regresando el resultado
    return Result(result=True)