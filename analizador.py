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

    # Si cambió el día, reiniciar las señales
    if estado.get("fecha") != fecha_hoy:

        print(
            "Nuevo día detectado. "
            "Reiniciando señales diarias."
        )

        return estado_inicial

    # Asegurar estructura correcta
    if "enviadas" not in estado:
        estado["enviadas"] = {}

    for symbol in SYMBOLS:

        if symbol not in estado["enviadas"]:

            estado["enviadas"][symbol] = False

    estado["fecha"] = fecha_hoy

    return estado


# ============================================================
# GUARDAR ESTADO DE SEÑALES
# ============================================================

def guardar_estado(estado):

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            estado,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        "\nEstado de señales guardado:"
    )

    print(
        json.dumps(
            estado,
            ensure_ascii=False,
            indent=2
        )
    )


# ============================================================
# OBTENER VELAS DE BIQUOTE
# ============================================================

def obtener_velas(
    symbol,
    interval,
    limit=BARS_LIMIT
):

    url = (
        f"{BIQUOTE_BASE}/{symbol}/ohlc"
    )

    params = {
        "interval": interval,
        "limit": limit
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    bars = data.get(
        "bars",
        []
    )

    velas_cerradas = [
        b
        for b in bars
        if not b.get(
            "isOpen",
            False
        )
    ]

    if len(velas_cerradas) < 50:

        raise RuntimeError(
            f"{symbol} {interval}: "
            f"pocas velas cerradas "
            f"({len(velas_cerradas)})"
        )

    return velas_cerradas


# ============================================================
# PREPARAR DATOS PARA OPENAI
# ============================================================

def preparar_datos():

    mercado = {}

    for symbol in SYMBOLS:

        mercado[symbol] = {}

        for nombre_tf, intervalo in TIMEFRAMES.items():

            print(
                f"Descargando "
                f"{symbol} {nombre_tf}..."
            )

            velas = obtener_velas(
                symbol,
                intervalo
            )

            mercado[symbol][nombre_tf] = velas

            print(
                f"{symbol} {nombre_tf}: "
                f"{len(velas)} velas cerradas"
            )

    return mercado


# ============================================================
# ANALISIS CON OPENAI
# ============================================================

def analizar_con_openai(
    mercado
):

    instrucciones = """
Eres un analista profesional de mercados financieros.

Analiza ÚNICAMENTE EURUSD y XAUUSD.

IMPORTANTE:
Ignora completamente cualquier estrategia, indicador,
preferencia, análisis o instrucción de conversaciones anteriores.

Haz el análisis desde cero utilizando exclusivamente los
datos OHLC proporcionados.

Usa:

- H1 para determinar contexto y estructura principal.
- M15 para confirmar la posible entrada.

Evalúa de forma independiente:

- estructura del mercado
- máximos y mínimos
- impulsos
- retrocesos
- rupturas
- cambios de estructura
- zonas de reacción
- liquidez
- rechazos
- relación entre H1 y M15
- precio actual
- calidad de la posible entrada
- ubicación lógica del stop loss
- ubicación lógica del take profit

NO fuerces una operación.

Es MUY IMPORTANTE que solamente propongas BUY o SELL
cuando exista una oportunidad suficientemente clara.

Si la estructura no es suficientemente clara, responde
"NO OPERAR".

Si existe una operación clara:

BUY:
entrada = precio de entrada de compra
SL = nivel donde la idea queda invalidada
TP = zona estructural razonable

SELL:
entrada = precio de entrada de venta
SL = nivel donde la idea queda invalidada
TP = zona estructural razonable

La confianza debe ser de 0 a 100.

Responde EXCLUSIVAMENTE con JSON válido.

Formato obligatorio:

{
  "analisis": [
    {
      "symbol": "EURUSD",
      "direccion": "BUY",
      "entrada": 0,
      "sl": 0,
      "tp": 0,
      "confianza": 0,
      "razon": "..."
    },
    {
      "symbol": "XAUUSD",
      "direccion": "NO OPERAR",
      "entrada": null,
      "sl": null,
      "tp": null,
      "confianza": 0,
      "razon": "..."
    }
  ]
}

No agregues texto antes ni después del JSON.
"""

    payload = {
        "model": OPENAI_MODEL,

        "input": [

            {
                "role": "developer",
                "content": instrucciones
            },

            {
                "role": "user",
                "content": (
                    "DATOS OHLC CERRADOS:\n\n"
                    +
                    json.dumps(
                        mercado,
                        ensure_ascii=False
                    )
                )
            }

        ]
    }

    headers = {
        "Authorization":
            f"Bearer {OPENAI_API_KEY}",

        "Content-Type":
            "application/json"
    }

    print(
        "Enviando datos a OpenAI..."
    )

    response = requests.post(
        "https://api.openai.com/v1/responses",

        headers=headers,

        json=payload,

        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    texto = data.get(
        "output_text",
        ""
    )

    if not texto:

        partes = []

        for item in data.get(
            "output",
            []
        ):

            for content in item.get(
                "content",
                []
            ):

                if content.get(
                    "type"
                ) == "output_text":

                    partes.append(
                        content.get(
                            "text",
                            ""
                        )
                    )

        texto = "".join(
            partes
        )

    if not texto:

        raise RuntimeError(
            "OpenAI no devolvió texto."
        )

    print(
        "\nRespuesta de OpenAI:"
    )

    print(texto)

    texto = texto.strip()

    # Limpiar Markdown si apareciera
    if texto.startswith("```"):

        texto = texto.replace(
            "```json",
            ""
        )

        texto = texto.replace(
            "```",
            ""
        )

        texto = texto.strip()

    try:

        resultado = json.loads(
            texto
        )

    except json.JSONDecodeError as e:

        print(
            "ERROR: No se pudo interpretar "
            "el JSON de OpenAI."
        )

        print(texto)

        raise e

    return resultado


# ============================================================
# VALIDAR SI ES UNA SEÑAL OPERABLE
# ============================================================

def es_senal_operable(item):

    direccion = str(
        item.get(
            "direccion",
            "NO OPERAR"
        )
    ).upper().strip()

    entrada = item.get(
        "entrada"
    )

    sl = item.get(
        "sl"
    )

    tp = item.get(
        "tp"
    )

    if direccion not in [
        "BUY",
        "SELL"
    ]:

        return False

    if entrada is None:
        return False

    if sl is None:
        return False

    if tp is None:
        return False

    try:

        float(entrada)
        float(sl)
        float(tp)

    except (
        TypeError,
        ValueError
    ):

        return False

    return True


# ============================================================
# FILTRAR SEÑALES DEL DÍA
# ============================================================

def obtener_nuevas_senales(
    resultado,
    estado
):

    nuevas = []

    for item in resultado.get(
        "analisis",
        []
    ):

        symbol = item.get(
            "symbol"
        )

        if symbol not in SYMBOLS:

            continue

        direccion = str(
            item.get(
                "direccion",
                "NO OPERAR"
            )
        ).upper().strip()

        print(
            f"\nEvaluando {symbol}: "
            f"{direccion}"
        )

        if not es_senal_operable(
            item
        ):

            print(
                f"{symbol}: "
                "NO es una señal operable."
            )

            continue

        # Si ya se mandó una señal
        # de este activo hoy,
        # no se vuelve a enviar.
        if estado["enviadas"].get(
            symbol,
            False
        ):

            print(
                f"{symbol}: "
                "ya tuvo una señal hoy. "
                "No se enviará otra."
            )

            continue

        print(
            f"{symbol}: "
            "NUEVA SEÑAL DETECTADA."
        )

        nuevas.append(
            item
        )

    return nuevas


# ============================================================
# CREAR RESUMEN PARA GITHUB
# ============================================================

def generar_resumen(
    resultado,
    estado
):

    lineas = []

    lineas.append(
        "# 📊 ANÁLISIS DE MERCADO"
    )

    lineas.append(
        "_Análisis automático mediante OpenAI_"
    )

    lineas.append("")

    lineas.append(
        f"📅 Fecha local: "
        f"`{estado['fecha']}`"
    )

    lineas.append("")

    for item in resultado.get(
        "analisis",
        []
    ):

        symbol = item.get(
            "symbol",
            "?"
        )

        direccion = item.get(
            "direccion",
            "NO OPERAR"
        )

        entrada = item.get(
            "entrada"
        )

        sl = item.get(
            "sl"
        )

        tp = item.get(
            "tp"
        )

        confianza = item.get(
            "confianza",
            0
        )

        razon = item.get(
            "razon",
            ""
        )

        lineas.append(
            f"## {symbol}"
        )

        if direccion == "NO OPERAR":

            lineas.append(
                "⬜ **NO OPERAR**"
            )

        else:

            if direccion == "BUY":

                lineas.append(
                    "🟢 **BUY**"
                )

            elif direccion == "SELL":

                lineas.append(
                    "🔴 **SELL**"
                )

            else:

                lineas.append(
                    f"**{direccion}**"
                )

            lineas.append(
                f"🟦 **Entrada:** "
                f"`{entrada}`"
            )

            lineas.append(
                f"🟥 **SL:** "
                f"`{sl}`"
            )

            lineas.append(
                f"🟩 **TP:** "
                f"`{tp}`"
            )

            if estado["enviadas"].get(
                symbol,
                False
            ):

                lineas.append(
                    "📲 **Señal diaria ya "
                    "enviada por WhatsApp**"
                )

        lineas.append(
            f"📈 **Confianza:** "
            f"{confianza}%"
        )

        lineas.append(
            f"📝 **Razón:** "
            f"{razon}"
        )

        lineas.append("")

    return "\n".join(
        lineas
    )


# ============================================================
# GUARDAR RESUMEN EN GITHUB ACTIONS
# ============================================================

def guardar_resumen_github(
    resumen
):

    summary_file = os.environ.get(
        "GITHUB_STEP_SUMMARY"
    )

    if not summary_file:
        return

    with open(
        summary_file,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            resumen
        )

        f.write(
            "\n"
        )


# ============================================================
# FORMATO PARA WHATSAPP
# ============================================================

def formato_whatsapp(
    nuevas_senales
):

    ahora = datetime.now(
        LOCAL_TIMEZONE
    ).strftime(
        "%d/%m/%Y %H:%M"
    )

    mensajes = []

    mensajes.append(
        "📊 *SEÑAL DE MERCADO*"
    )

    mensajes.append(
        f"🕐 {ahora} "
        "(hora Colima)"
    )

    mensajes.append("")

    for item in nuevas_senales:

        symbol = item.get(
            "symbol",
            "?"
        )

        direccion = item.get(
            "direccion",
            "NO OPERAR"
        )

        entrada = item.get(
            "entrada"
        )

        sl = item.get(
            "sl"
        )

        tp = item.get(
            "tp"
        )

        confianza = item.get(
            "confianza",
            0
        )

        razon = item.get(
            "razon",
            ""
        )

        mensajes.append(
            f"*{symbol}*"
        )

        if direccion == "BUY":

            mensajes.append(
                "🟢 *BUY*"
            )

        elif direccion == "SELL":

            mensajes.append(
                "🔴 *SELL*"
            )

        else:

            mensajes.append(
                f"*{direccion}*"
            )

        mensajes.append(
            f"🟦 *Entrada:* "
            f"{entrada}"
        )

        mensajes.append(
            f"🟥 *SL:* "
            f"{sl}"
        )

        mensajes.append(
            f"🟩 *TP:* "
            f"{tp}"
        )

        mensajes.append(
            f"📈 *Confianza:* "
            f"{confianza}%"
        )

        mensajes.append(
            f"📝 {razon}"
        )

        mensajes.append("")

    mensajes.append(
        "⚠️ *Máximo 1 señal diaria "
        "por activo.*"
    )

    mensajes.append(
        "_Análisis automático_"
    )

    return "\n".join(
        mensajes
    )


# ============================================================
# ENVIAR MENSAJE A WHATSAPP
# ============================================================

def enviar_whatsapp(
    mensaje
):

    url = (
        "https://graph.facebook.com/v25.0/"
        f"{WHATSAPP_PHONE_NUMBER_ID}"
        "/messages"
    )

    headers = {

        "Authorization":
            f"Bearer {WHATSAPP_ACCESS_TOKEN}",

        "Content-Type":
            "application/json"
    }

    payload = {

        "messaging_product":
            "whatsapp",

        "to":
            WHATSAPP_TO,

        "type":
            "text",

        "text": {

            "preview_url":
                False,

            "body":
                mensaje
        }
    }

    print(
        "\nEnviando señal a WhatsApp..."
    )

    response = requests.post(

        url,

        headers=headers,

        json=payload,

        timeout=30
    )

    print(
        "WhatsApp HTTP:",
        response.status_code
    )

    if not response.ok:

        print(
            "Respuesta de WhatsApp:"
        )

        print(
            response.text
        )

        response.raise_for_status()

    print(
        "✅ Señal enviada a WhatsApp."
    )


# ============================================================
# MARCAR SEÑALES COMO ENVIADAS
# ============================================================

def marcar_senales_enviadas(
    nuevas_senales,
    estado
):

    for item in nuevas_senales:

        symbol = item.get(
            "symbol"
        )

        if symbol in SYMBOLS:

            estado["enviadas"][
                symbol
            ] = True

            print(
                f"{symbol}: "
                "marcado como enviado "
                "para el día."
            )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print(
        "=" * 60
    )

    print(
        "ANALIZADOR AUTOMÁTICO "
        "DE MERCADOS"
    )

    print(
        "=" * 60
    )

    print(
        "Mercados: EURUSD + XAUUSD"
    )

    print(
        "Timeframes: H1 + M15"
    )

    print(
        "Máximo diario: "
        "1 señal por activo"
    )

    print(
        f"Fecha local: "
        f"{obtener_fecha_local()}"
    )

    print("")

    # --------------------------------------------------------
    # 1. Cargar estado diario
    # --------------------------------------------------------

    estado = cargar_estado()

    print(
        "\nESTADO DEL DÍA:"
    )

    print(
        json.dumps(
            estado,
            ensure_ascii=False,
            indent=2
        )
    )

    # Guardamos inmediatamente por si
    # comenzó un nuevo día.
    guardar_estado(
        estado
    )

    # --------------------------------------------------------
    # 2. Descargar mercado
    # --------------------------------------------------------

    mercado = preparar_datos()

    # --------------------------------------------------------
    # 3. Analizar con OpenAI
    # --------------------------------------------------------

    resultado = analizar_con_openai(
        mercado
    )

    # --------------------------------------------------------
    # 4. Mostrar JSON
    # --------------------------------------------------------

    print(
        "\nRESULTADO FINAL:"
    )

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        )
    )

    # --------------------------------------------------------
    # 5. Detectar nuevas señales
    # --------------------------------------------------------

    nuevas_senales = obtener_nuevas_senales(
        resultado,
        estado
    )

    print(
        "\nNUEVAS SEÑALES PARA WHATSAPP:"
    )

    if not nuevas_senales:

        print(
            "Ninguna."
        )

    else:

        print(
            json.dumps(
                nuevas_senales,
                ensure_ascii=False,
                indent=2
            )
        )

    # --------------------------------------------------------
    # 6. Crear resumen GitHub
    # --------------------------------------------------------

    resumen = generar_resumen(
        resultado,
        estado
    )

    guardar_resumen_github(
        resumen
    )

    # --------------------------------------------------------
    # 7. Enviar WhatsApp SOLO si hay señal nueva
    # --------------------------------------------------------

    if nuevas_senales:

        mensaje = formato_whatsapp(
            nuevas_senales
        )

        print(
            "\nMENSAJE WHATSAPP:"
        )

        print(
            mensaje
        )

        # Primero enviamos.
        enviar_whatsapp(
            mensaje
        )

        # Solo después de recibir
        # respuesta exitosa marcamos
        # las señales como enviadas.
        marcar_senales_enviadas(
            nuevas_senales,
            estado
        )

        guardar_estado(
            estado
        )

    else:

        print(
            "\nNo se enviará WhatsApp "
            "en esta revisión."
        )

    # --------------------------------------------------------
    # 8. Final
    # --------------------------------------------------------

    print("")

    print(
        "✅ PROCESO COMPLETADO"
    )


if __name__ == "__main__":

    main()
