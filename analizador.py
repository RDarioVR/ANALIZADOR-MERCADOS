import os
import json
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN
# ============================================================

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

WHATSAPP_ACCESS_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
WHATSAPP_PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
WHATSAPP_TO = os.environ["WHATSAPP_TO"]

OPENAI_MODEL = "gpt-6-luna"

BIQUOTE_BASE = "https://biquote.io/api"

SYMBOLS = ["EURUSD", "XAUUSD"]

TIMEFRAMES = {
    "H1": "1h",
    "M15": "15m"
}

BARS_LIMIT = 300

# Zona horaria de Colima / Ciudad de México
LOCAL_TIMEZONE = ZoneInfo("America/Mexico_City")

# Archivo que guarda las señales ya enviadas durante el día
STATE_FILE = "estado_senales.json"


# ============================================================
# OBTENER FECHA LOCAL
# ============================================================

def obtener_fecha_local():

    ahora = datetime.now(
        LOCAL_TIMEZONE
    )

    return ahora.strftime(
        "%Y-%m-%d"
    )


# ============================================================
# CARGAR ESTADO DE SEÑALES
# ============================================================

def cargar_estado():

    fecha_hoy = obtener_fecha_local()

    estado_inicial = {
        "fecha": fecha_hoy,
        "enviadas": {
            "EURUSD": False,
            "XAUUSD": False
        }
    }

    if not os.path.exists(STATE_FILE):

        print(
            "No existe estado de señales. "
            "Se creará uno nuevo."
        )

        return estado_inicial

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            estado = json.load(f)

    except Exception as e:

        print(
            "No se pudo leer el estado anterior:"
        )

        print(e)

        return estado_inicial
