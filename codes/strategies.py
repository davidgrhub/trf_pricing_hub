from sqlalchemy import create_engine
from dataclasses import dataclass
import pandas as pd
import numpy as np


# Clase para el resultado del bloque
@dataclass
class Result:
    result: bool
    error: str | None = None


# Funciones auxiliares
def get_contracts(db_user: str, db_user_password: str, db_host: str, db_port: int,
                  db_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # Creamos la conexión
    engine = create_engine(f"mysql+pymysql://{db_user}:{db_user_password}@{db_host}:{db_port}/{db_name}")
    # Leemos la tabla y la convertimos en DataFrame
    df = pd.read_sql(f"SELECT * FROM final_contracts", con=engine)
    # Leemos la tabal de competitivad
    df_comp = pd.read_sql(f"SELECT * FROM competitiveness_result", con=engine)
    # Leemos las reglas de competitividad
    df_rules = pd.read_sql(f"SELECT * FROM rules WHERE is_active = 1", con=engine)
    # Terminamos la función regresando el DataFrame
    return df, df_rules, df_comp


# Funciones de procesado
def merge_competitiveness(df_contracts: pd.DataFrame, df_rules: pd.DataFrame, df_comp: pd.DataFrame) -> pd.DataFrame:
    # Usamos solo las columnas necesarias de rules
    df_rules_sub = df_rules[['unique_id', 'expedia_airport_code', 'expedia_hotel_code']]
    df = pd.merge(df_contracts, df_rules_sub, on='unique_id', how='left')
    # Definir el mapeo de servicios
    mapping = {'Shared': 'Shuttle', 'Private': 'Private Minivan', 'Deluxe': 'Suv'}
    # Creamos una columna temporal para saber qué buscar en la tabla de competitividad
    df['search_term'] = df['service_type'].map(mapping)
    # Buscamos el candidato
    def find_cheapest_comp(row):
        # Si no tenemos reglas, regresamos NaN
        if pd.isna(row['expedia_airport_code']) or pd.isna(row['search_term']):
            return np.nan
        # Filtrar tabla de competitividad por códigos de hotel/aeropuerto
        mask = ((df_comp['expedia_airport_code'] == row['expedia_airport_code']) &
                (df_comp['expedia_hotel_code'] == row['expedia_hotel_code']) &
                (df_comp['product'].str.contains(row['search_term'], case=False, na=False)))
        matches = df_comp[mask]
        # Si hay coincidencias, devolvemos la más barata
        if not matches.empty:
            return matches['sale'].min()
        return np.nan
    # Aplicamos la búsqueda fila por fila
    df['sale_comp'] = df.apply(find_cheapest_comp, axis=1)
    # Limpiamos columnas temporales
    df = df.drop(columns=['expedia_airport_code', 'expedia_hotel_code', 'search_term'])
    # Terminamos la funcion regresando el dataframe
    return df


def strategy(df: pd.DataFrame, value: str, min_margin: float, max_discount: float,
             comp_min_margin: float = None) -> pd.DataFrame:
    # Comprovamos la estrategia
    if value == "pvp":
        # Calcualmos la tarifa minima base
        base_sale = (df['final_cost'] / (1 - min_margin)).round(2)
        # Calculamos la tarifa minima de competitividad
        limit_comp_sale = (df['final_cost'] / (1 - comp_min_margin)).round(2)
        # Calculamos la tarifa minima
        df['pvp_min_sale'] = np.where(df['sale_comp'].notna(), np.maximum(df['sale_comp'] - 1, limit_comp_sale),
                                      base_sale)
    elif value == "swg":
        # Calculamos la tarifa minima
        df['swg_min_sale'] = np.where(df['sale_swg'].notna(), np.maximum(df['sale_swg'] + 1, df['pvp_final_sale']),
                                      df['pvp_final_sale'])
    elif value == "ff":
        # Calculamos la tarifa minima
        df ['ff_min_sale'] = np.minimum((df['final_cost'] / (1 - min_margin)).round(2),
                                        (df['pvp_final_sale'] - 1).round(2))
    # Calculamos el descuento correspondiente a la tarifa minima
    raw_discount = (df['sale_pvp'] - df[f'{value}_min_sale']) / df['sale_pvp']
    # Redondeamos el descuento
    df[f'{value}_max_discount'] = (
        raw_discount.apply(lambda x: np.ceil(x * 100) / 100 if x < 0 else np.floor(x * 100) / 100))
    if value == "ff":
        # Forzar al menos un 1% de descuento
        df[f'ff_max_discount'] = np.where(df[f'ff_max_discount'] <= 0, 0.01, df[f'ff_max_discount'])
    # Calculamos el descuento final
    df[f'{value}_final_discount'] = np.clip(df[f'{value}_max_discount'], 0, max_discount)
    # Creamos la tarifa final correspondiente
    df[f'{value}_final_sale'] = (df['sale_pvp'] * (1 - df[f'{value}_final_discount'])).round(2)
    # Creamos el margen final
    df[f'{value}_final_margin'] = ((df[f'{value}_final_sale'] - df['final_cost']) / df[f'{value}_final_sale']).round(2)
    # Descuentos a aplicar
    if value in ["pvp", "swg"]:
        df[f'{value}_aplay'] = ((df[f'{value}_final_discount'] > 0) & (df['final_cost'] >= 1)).astype(int)
    else:
        df[f'{value}_aplay'] = 1
    # Terminamos la función regresando el dataframe
    return df



def formulation_strategies(df: pd.DataFrame, ff_min_margin: float, ff_max_discount: float, pvp_min_margin: float,
                           pvp_max_discount: float, comp_min_margin: float) -> pd.DataFrame:
    # Creamos la estrategia para PVP
    df = strategy(df, 'pvp', pvp_min_margin, pvp_max_discount, comp_min_margin)
    # Creamos la estrategia para sunwing
    df = strategy(df, 'swg', pvp_min_margin, pvp_max_discount)
    # Creamos la estrategia para Friends and Family
    df = strategy(df, 'ff', ff_min_margin, ff_max_discount)
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
                    ff_min_margin: float, ff_max_discount: float, pvp_min_margin: float,
                    pvp_max_discount: float, comp_min_margin: float) -> Result:
    print("\t[Strategies Block] Processing ⚙️")
    # Obtenemos los contratos procesados
    try:
        df, df_rules, df_comp = get_contracts(db_user, db_user_password, db_host, db_port, db_name)
        print(f"\t • Contracts successfully retrieved. Rows loaded: {len(df)}")
        print(f"\t • Rules successfully retrieved. Rows loaded: {len(df_rules)}")
        print(f"\t • Competitivenedd successfully retrieved. Rows loaded: {len(df_comp)}")
    except Exception as e:
        print("\t ❌ Failed to retrieve data from database")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Realizamos el cruce de competitividad
    try:
        print("\t • Matching competitiveness prices")
        df = merge_competitiveness(df, df_rules, df_comp)
    except Exception as e:
        print("\t ❌ Failed to matching competitiveness")
        return Result(result=False, error=f"\t[Error] -> {type(e).__name__}: {e}")
    # Creamos las estrategias
    try:
        print("\t • Starting strategies processing")
        df = formulation_strategies(df, ff_min_margin, ff_max_discount, pvp_min_margin, pvp_max_discount,
                                    comp_min_margin)
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