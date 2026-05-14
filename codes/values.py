from dotenv import load_dotenv
import os


# Función auxiliar
def strtobool(value: str) -> bool:
    # Tomamos la variable y la estandarizamos
    v = value.strip().lower()
    # Si es una variable positiva
    if v in ("y", "yes", "t", "true", "on", "1"):
        # Terminamos la función regresando True
        return True
    # Si es una variable negativa
    if v in ("n", "no", "f", "false", "off", "0"):
        # Terminamos la función regresando False
        return False
    # En caso de error
    raise ValueError(f"Invalid truth value: {value}")


# Cargamos el archivo .env
load_dotenv()

# Cargamos las variables para python
contracts = strtobool(os.getenv("CONTRACTS"))
strategies = strtobool(os.getenv("STRATEGIES"))
discounts = strtobool(os.getenv("DISCOUNTS"))
competitiveness = strtobool(os.getenv("COMPETITIVENESS"))

headless = strtobool(os.getenv("HEADLESS"))
timeout = int(os.getenv("TIMEOUT"))
interval = int(os.getenv("INTERVAL"))
max_workers_contracts = int(os.getenv("MAX_WORKERS_CONTRACTS"))
max_workers_competitiveness = int(os.getenv("MAX_WORKERS_COMPETITIVENESS"))
max_workers_discounts = int(os.getenv("MAX_WORKERS_DISCOUNTS"))

strategy_list = list(map(str, os.getenv("STRATEGY_LIST").split(",")))
pvp_min_margin = float(os.getenv("PVP_MIN_MARGIN"))
pvp_max_discount = float(os.getenv("PVP_MAX_DISCOUNT"))
ff_min_margin = float(os.getenv("FF_MIN_MARGIN"))
ff_max_discount = float(os.getenv("FF_MAX_DISCOUNT"))

db_user = os.getenv("DB_USER")
db_user_password = os.getenv("DB_USER_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = int(os.getenv("DB_PORT"))
db_name = os.getenv("DB_NAME")

user_mail = os.getenv("USER_MAIL")
user_password = os.getenv("USER_PASSWORD")