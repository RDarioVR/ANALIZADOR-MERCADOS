import os
import json
import requests
from datetime import datetime, timezone


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


# ============================================================
# OBTENER VELAS DE BIQUOTE
# ============================================================

def obtener_velas(symbol, interval, limit=BARS_LIMIT):

    url = f"{BIQUOTE_BASE}/{symbol}/ohlc"

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

    bars = data.get("bars", [])

    velas_cerradas = [
        b for b in bars
        if not b.get("isOpen", False)
    ]

    if len(velas_cerradas) < 50:
        raise RuntimeError(
            f"{symbol} {interval}: pocas velas cerradas "
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
                f"Descargando {symbol} {nombre_tf}..."
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

def analizar_con_openai(mercado):

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
                    + json.dumps(
                        mercado,
                        ensure_ascii=False
                    )
                )
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    print("Enviando datos a OpenAI...")

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    data = response.json()

    texto = data.get("output_text", "")

    if not texto:

        # Compatibilidad por si la respuesta viene
        # en la estructura completa de output.
        partes = []

        for item in data.get("output", []):

            for content in item.get("content", []):

                if content.get("type") == "output_text":

                    partes.append(
                        content.get("text", "")
                    )

        texto = "".join(partes)

    if not texto:
        raise RuntimeError(
            "OpenAI no devolvió texto."
        )

    print("\nRespuesta de OpenAI:")
    print(texto)

    # Limpiar posibles bloques Markdown
    texto = texto.strip()

    if texto.startswith("```"):
        texto = texto.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

    try:

        resultado = json.loads(texto)

    except json.JSONDecodeError as e:

        print(
            "ERROR: No se pudo interpretar "
            "el JSON de Gemini/OpenAI."
        )

        print(texto)

        raise e

    return resultado


# ============================================================
# CREAR RESUMEN PARA GITHUB
# ============================================================

def generar_resumen(resultado):

    lineas = []

    lineas.append(
        "# 📊 ANÁLISIS DE MERCADO"
    )

    lineas.append(
        "_Análisis automático mediante OpenAI_"
    )

    lineas.append("")

    for item in resultado.get("analisis", []):

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
                f"🟦 **Entrada:** `{entrada}`"
            )

            lineas.append(
                f"🟥 **SL:** `{sl}`"
            )

            lineas.append(
                f"🟩 **TP:** `{tp}`"
            )

        lineas.append(
            f"📈 **Confianza:** {confianza}%"
        )

        lineas.append(
            f"📝 **Razón:** {razon}"
        )

        lineas.append("")

    return "\n".join(lineas)


# ============================================================
# GUARDAR RESUMEN EN GITHUB ACTIONS
# ============================================================

def guardar_resumen_github(resumen):

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

        f.write(resumen)

        f.write("\n")


# ============================================================
# FORMATO PARA WHATSAPP
# ============================================================

def formato_whatsapp(resultado):

    ahora = datetime.now(
        timezone.utc
    ).strftime(
        "%d/%m/%Y %H:%M UTC"
    )

    mensajes = []

    mensajes.append(
        "📊 *ANÁLISIS DE MERCADO*"
    )

    mensajes.append(
        f"🕐 {ahora}"
    )

    mensajes.append("")

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

        mensajes.append(
            f"*{symbol}*"
        )

        if direccion == "NO OPERAR":

            mensajes.append(
                "⬜ *NO OPERAR*"
            )

        else:

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
                f"🟦 *Entrada:* {entrada}"
            )

            mensajes.append(
                f"🟥 *SL:* {sl}"
            )

            mensajes.append(
                f"🟩 *TP:* {tp}"
            )

        mensajes.append(
            f"📈 *Confianza:* {confianza}%"
        )

        mensajes.append(
            f"📝 {razon}"
        )

        mensajes.append("")

    mensajes.append(
        "_Análisis automático_"
    )

    return "\n".join(mensajes)


# ============================================================
# ENVIAR MENSAJE A WHATSAPP
# ============================================================

def enviar_whatsapp(mensaje):

    url = (
        "https://graph.facebook.com/v25.0/"
        f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": (
            f"Bearer {WHATSAPP_ACCESS_TOKEN}"
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_TO,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": mensaje
        }
    }

    print(
        "\nEnviando análisis a WhatsApp..."
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
        "✅ Mensaje enviado a WhatsApp."
    )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 60)

    print(
        "ANALIZADOR AUTOMÁTICO DE MERCADOS"
    )

    print("=" * 60)

    print(
        "Mercados: EURUSD + XAUUSD"
    )

    print(
        "Timeframes: H1 + M15"
    )

    print("")

    # 1. Descargar mercado
    mercado = preparar_datos()

    # 2. Analizar con OpenAI
    resultado = analizar_con_openai(
        mercado
    )

    # 3. Mostrar JSON
    print("\nRESULTADO FINAL:")

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        )
    )

    # 4. Crear resumen GitHub
    resumen = generar_resumen(
        resultado
    )

    guardar_resumen_github(
        resumen
    )

    # 5. Crear mensaje WhatsApp
    mensaje = formato_whatsapp(
        resultado
    )

    print(
        "\nMENSAJE WHATSAPP:"
    )

    print(mensaje)

    # 6. Enviar WhatsApp
    enviar_whatsapp(
        mensaje
    )

    print("")
    print(
        "✅ PROCESO COMPLETADO"
    )


if __name__ == "__main__":

    main()
