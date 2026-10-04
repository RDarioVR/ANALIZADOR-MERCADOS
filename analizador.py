import requests
import json
import os

BIQUOTE_URL = "https://biquote.io/api/{symbol}/ohlc"

SYMBOLS = {
    "EURUSD": "EURUSD",
    "XAUUSD": "XAUUSD"
}

MODEL = "gpt-6-luna"


def obtener_velas(symbol, interval, limit=300):
    url = BIQUOTE_URL.format(symbol=symbol)

    params = {
        "interval": interval,
        "limit": limit
    }

    print(f"Consultando {symbol} {interval}...")

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    bars = data.get("bars", [])

    cerradas = []

    for vela in bars:

        if vela.get("isOpen") is True:
            continue

        try:

            cerradas.append({
                "time": vela.get("openTime"),
                "open": float(vela.get("open")),
                "high": float(vela.get("high")),
                "low": float(vela.get("low")),
                "close": float(vela.get("close"))
            })

        except (TypeError, ValueError):
            continue

    cerradas.sort(
        key=lambda x: str(x["time"])
    )

    return cerradas


def preparar_datos(symbol, h1, m15):

    texto = f"\n\n===== {symbol} =====\n"

    texto += "\n--- H1 ---\n"

    for vela in h1:

        texto += (
            f'{vela["time"]} | '
            f'O={vela["open"]} '
            f'H={vela["high"]} '
            f'L={vela["low"]} '
            f'C={vela["close"]}\n'
        )

    texto += "\n--- M15 ---\n"

    for vela in m15:

        texto += (
            f'{vela["time"]} | '
            f'O={vela["open"]} '
            f'H={vela["high"]} '
            f'L={vela["low"]} '
            f'C={vela["close"]}\n'
        )

    return texto


def analizar_con_openai(datos):

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise Exception(
            "No se encontró OPENAI_API_KEY."
        )

    instrucciones = """

Eres un analista profesional de mercados financieros.

Analiza EUR/USD y XAU/USD desde cero utilizando únicamente
los datos OHLC proporcionados.

IMPORTANTE:

- IGNORA cualquier estrategia anterior.
- IGNORA indicadores o sistemas utilizados anteriormente.
- No reutilices reglas previas del proyecto.
- Haz el análisis de forma independiente.
- No estás obligado a generar una operación.
- Si la estructura no es clara, responde NO OPERAR.

Usa:

H1:
Para determinar el contexto general, estructura, tendencia,
máximos, mínimos, zonas importantes y dirección predominante.

M15:
Para buscar una posible entrada concreta y confirmar si existe
una oportunidad operable.

Analiza cuando sea posible:

- estructura de mercado
- máximos y mínimos
- rupturas
- cambios de estructura
- impulsos
- retrocesos
- zonas de reacción
- liquidez
- rechazo de precios
- relación entre H1 y M15
- ubicación actual del precio

La entrada debe ser técnicamente razonable.

El Stop Loss debe colocarse donde la idea quede invalidada.

El Take Profit debe estar en una zona razonable según la
estructura del mercado.

NO inventes datos que no aparezcan en las velas.

Si la operación no presenta suficiente claridad,
responde NO OPERAR.

La prioridad es calidad y protección del capital,
no generar operaciones por obligación.

Devuelve ÚNICAMENTE JSON válido.

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

Reglas:

direccion solamente puede ser:

BUY
SELL
NO OPERAR

confianza debe ser un número entre 0 y 100.

Si direccion = NO OPERAR:

entrada = null
sl = null
tp = null

La razón debe ser breve y concreta.

No escribas Markdown.

No escribas texto fuera del JSON.

"""


    payload = {
        "model": MODEL,
        "instructions": instrucciones,
        "input": datos
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print("\nEnviando datos a OpenAI...")
    print("Modelo:", MODEL)

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    resultado = response.json()

    texto = resultado.get("output_text")

    if not texto:

        for item in resultado.get("output", []):

            if item.get("type") == "message":

                for contenido in item.get("content", []):

                    if contenido.get("type") == "output_text":

                        texto = contenido.get("text")

                        break

            if texto:
                break

    if not texto:
        raise Exception(
            "OpenAI no devolvió texto interpretable."
        )

    texto = texto.strip()

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

    return json.loads(texto)


def generar_resumen(resultado):

    lineas = []

    lineas.append("# 📊 ANÁLISIS DE MERCADO")
    lineas.append("")
    lineas.append(
        "_Análisis automático mediante OpenAI_"
    )
    lineas.append("")

    for item in resultado.get("analisis", []):

        symbol = item.get("symbol", "")
        direccion = item.get("direccion", "")
        entrada = item.get("entrada")
        sl = item.get("sl")
        tp = item.get("tp")
        confianza = item.get("confianza")
        razon = item.get("razon", "")

        lineas.append(
            f"## {symbol}"
        )

        if direccion == "NO OPERAR":

            lineas.append(
                "⬜ **NO OPERAR**"
            )

            lineas.append(
                f"**Confianza:** {confianza}%"
            )

        else:

            if direccion == "BUY":
                señal = "🟢 **BUY**"
            else:
                señal = "🔴 **SELL**"

            lineas.append(
                f"**Señal:** {señal}"
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
                f"**Confianza:** {confianza}%"
            )

        lineas.append(
            f"**Razón:** {razon}"
        )

        lineas.append("")
        lineas.append("---")
        lineas.append("")

    return "\n".join(lineas)


def guardar_resumen_github(resumen):

    ruta = os.environ.get(
        "GITHUB_STEP_SUMMARY"
    )

    if not ruta:
        return

    with open(
        ruta,
        "a",
        encoding="utf-8"
    ) as archivo:

        archivo.write(resumen)

        archivo.write("\n")


def main():

    print("=" * 60)
    print(
        "ANALIZADOR DE MERCADOS - OPENAI"
    )
    print("=" * 60)

    todos_los_datos = ""

    for nombre, symbol in SYMBOLS.items():

        print("\n========================================")
        print(
            f"OBTENIENDO DATOS DE {nombre}"
        )
        print("========================================")

        h1 = obtener_velas(
            symbol,
            "1h",
            300
        )

        m15 = obtener_velas(
            symbol,
            "15m",
            300
        )

        print(
            f"H1 cerradas: {len(h1)}"
        )

        print(
            f"M15 cerradas: {len(m15)}"
        )

        if len(h1) < 50:

            raise Exception(
                f"No hay suficientes datos H1 para {nombre}."
            )

        if len(m15) < 50:

            raise Exception(
                f"No hay suficientes datos M15 para {nombre}."
            )

        todos_los_datos += preparar_datos(
            nombre,
            h1,
            m15
        )

    resultado = analizar_con_openai(
        todos_los_datos
    )

    print("\n")
    print("=" * 60)
    print("RESULTADO DEL ANÁLISIS")
    print("=" * 60)

    print(
        json.dumps(
            resultado,
            indent=2,
            ensure_ascii=False
        )
    )

    resumen = generar_resumen(
        resultado
    )

    guardar_resumen_github(
        resumen
    )

    print("\n")
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)

    print(resumen)

    print(
        "\nAnálisis terminado correctamente."
    )


if __name__ == "__main__":
    main()
