from pandas.io.formats.format import return_docstring
from sqlalchemy import create_engine
from dataclasses import dataclass
import pandas as pd
import numpy as np
import warnings
import shutil
import os


# Clase para le resultado del bloque
@dataclass
class Result:
    result: bool
    error: str | None = None


# Funciones auxiliares
def get_contracts(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str) -> pd.DataFrame:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Leemos la tabla y la convertimos en DataFrame
    df = pd.read_sql(f"SELECT * FROM final_contracts", con=engine)
    # Terminamos la función regresando el DataFrame
    return df


# Funciones de procesado
def strategy(df: pd.DataFrame, value: str, min_margin: float, max_discount: float,
             competitiveness: str) -> pd.DataFrame:
    # Creamos la tarifa final con respecto al margen minimo
    df[f'{value}_min_sale'] = (df['final_cost'] / (1 - min_margin)).round(2)
    # Comprobación de sale con respecto a la estrategia
    if value == "ff":
        # Para F&F comprobamos que la tarifa minimo sea menor a la tarifa B2C forzosamente
        df[f'{value}_min_sale'] = np.where(df[f'{value}_min_sale'] >= df[competitiveness], df[competitiveness] - 1,
            df[f'{value}_min_sale'])
    # Creamos el descuento correspondiente para esa tarifa
    discount = (df['sale_pvp'] - df[f'{value}_min_sale']) / df['sale_pvp']
    # Redondeamos los descuentos
    df[f'{value}_max_discount'] = discount.apply(lambda x: np.ceil(x * 100) / 100 if x < 0 else np.floor(x * 100) / 100)
    # Comprobación del descuento con respecto a la estrategia
    if value == "ff":
        # Para F&F comprobamos que el descuento menor sea 1%
        df[f'{value}_max_discount'] = np.where(df[f'{value}_max_discount'] <= 0, 0.01, df[f'{value}_max_discount'])
    # Creamos el descuento final validando que no supere el límite permitido
    df[f'{value}_final_discount'] = np.where(df[f'{value}_max_discount'] > max_discount, max_discount,
                                             df[f'{value}_max_discount'])
    # Creamos la tarifa final correspondiente
    df[f'{value}_final_sale'] = (df['sale_pvp'] * (1 - df[f'{value}_final_discount'])).round(2)
    # Creamos el margen final
    df[f'{value}_final_margin'] = ((df[f'{value}_final_sale'] - df['final_cost']) / df[f'{value}_final_sale']).round(2)
    # Creamos la columna que indica que descuentos aplican
    if value == "ff":
        # Para F&F todos los productos sin importar margen o costos aplican
        df[f'{value}_aplay'] = 1
    # Terminamos la función regresando el DataFrame
    return df


def formulation_strategies(df: pd.DataFrame, ff_min_margin: float, ff_max_discount: float) -> pd.DataFrame:
    # Creamos la estrategia para Friends and Family
    df = strategy(df, 'ff', ff_min_margin, ff_max_discount, 'sale_pvp')
    # Terminamos la función regresando el dataframe
    return df


# Función para subir la data
def upload_data(df: pd.DataFrame, db_user: str, db_user_password: str, db_host: str, db_port: int,
                db_name: str) -> None:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Agregamos el dataframe a la base de datos
    df.to_sql('final_strategies', con=engine, if_exists='replace', index=False)
    # Terminamos la función
    return


# Función main
def main_strategies(db_user: str, db_user_password: str, db_host: str, db_port: int, db_name: str,
                    ff_min_margin: float, ff_max_discount: float) -> Result:
    print("\t[Strategies Block] Processing ⚙️")
    # Obtenemos los contratos procesados
    try:
        df = get_contracts(db_user, db_user_password, db_host, db_port, db_name)
        print(f"\t • Contracts successfully retrieved. Rows loaded: {len(df)}")
    except Exception as e:
        print("\t ❌ Failed to retrieve contracts from database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Creamos las estrategias
    try:
        print("\t • Starting strategies processing")
        df = formulation_strategies(df, ff_min_margin, ff_max_discount)
        print("\t\tFinal strategies generated successfully")
    except Exception as e:
        print("\t ❌ Failed to generate final strategies")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Iniciamos el proceso para subir la data en la base de datos
    try:
        print("\t • Uploading final contracts to database")
        upload_data(df, db_user, db_user_password, db_host, db_port, db_name)
        print("\t\tData uploaded successfully")
    except Exception as e:
        print("\t ❌ Failed to upload data to database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Terminamos la función main
    return Result(result=True)