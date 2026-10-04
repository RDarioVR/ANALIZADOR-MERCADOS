import requests
import json
from datetime import datetime, timezone


# ============================================================
# CONFIGURACIÓN
# ============================================================

OPENAI_API_KEY = None

BIQUOTE_URL = "https://biquote.io/api/{symbol}/ohlc"

SYMBOLS = {
    "EURUSD": "EURUSD",
    "XAUUSD": "XAUUSD"
}

MODEL = "gpt-6-luna"


# ============================================================
# OBTENER VELAS DE BIQUOTE
# ============================================================

def obtener_velas(symbol, interval, limit=300):

    url = BIQUOTE_URL.format(symbol=symbol)

    params = {
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    # Algunos formatos pueden devolver directamente una lista
    if isinstance(data, list):
        velas = data

    elif isinstance(data, dict):
        velas = (
            data.get("data")
            or data.get("candles")
            or data.get("result")
            or []
        )

    else:
        velas = []

    # Nos quedamos únicamente con velas cerradas
    cerradas = []

    for vela in velas:

        if isinstance(vela, dict):

            if vela.get("isOpen") is True:
                continue

            try:
                cerradas.append({
                    "time": vela.get("time") or vela.get("timestamp"),
                    "open": float(vela.get("open")),
                    "high": float(vela.get("high")),
                    "low": float(vela.get("low")),
                    "close": float(vela.get("close"))
                })
            except:
                continue

    # Orden cronológico
    cerradas.sort(key=lambda x: str(x["time"]))

    return cerradas


# ============================================================
# CONVERTIR DATOS A TEXTO
# ============================================================

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


# ============================================================
# LLAMAR A OPENAI
# ============================================================

def analizar_con_openai(datos):

    import os

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        raise Exception(
            "No se encontró OPENAI_API_KEY en las variables de entorno."
        )

    instrucciones = """
Eres un analista profesional de mercados financieros.

Tu tarea es analizar EUR/USD y XAU/USD utilizando EXCLUSIVAMENTE
los datos de velas OHLC que recibirás.

IMPORTANTE:

1. IGNORA cualquier estrategia, indicador, sistema o preferencia
   utilizada anteriormente en esta conversación o proyecto.

2. Haz el análisis completamente desde cero.

3. No asumas que debe existir una operación.

4. Si la estructura del mercado no es suficientemente clara,
   responde NO OPERAR.

5. Utiliza H1 para determinar el contexto principal.

6. Utiliza M15 para buscar la oportunidad concreta de entrada.

7. Analiza acción del precio, estructura, máximos y mínimos,
   impulsos, retrocesos, zonas de reacción, rupturas,
   liquidez y contexto entre H1 y M15 cuando los datos lo permitan.

8. No inventes precios que no sean coherentes con las velas recibidas.

9. La entrada debe estar cerca de una zona técnicamente razonable.

10. El Stop Loss debe quedar en un nivel donde la idea quede
    técnicamente invalidada.

11. El Take Profit debe estar en una zona razonable de recorrido
    según la estructura disponible.

12. Si no existe una relación riesgo/beneficio razonable,
    puedes responder NO OPERAR.

13. No abras operaciones simplemente porque el precio esté subiendo
    o bajando.

14. La prioridad es CALIDAD DE LA OPERACIÓN, no cantidad.

Devuelve únicamente un JSON válido con esta estructura:

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

- direccion solamente puede ser BUY, SELL o NO OPERAR.
- confianza debe ser un número de 0 a 100.
- Si la dirección es NO OPERAR, entrada, sl y tp deben ser null.
- La razón debe ser breve y concreta.
- No escribas Markdown.
- No escribas texto fuera del JSON.
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

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    resultado = response.json()

    # Extraer texto de la respuesta
    texto = resultado.get("output_text")

    if not texto:

        # Compatibilidad con estructura de output
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

    # Quitar posibles bloques Markdown
    if texto.startswith("```"):
        texto = texto.replace("```json", "")
        texto = texto.replace("```", "")
        texto = texto.strip()

    return json.loads(texto)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 60)
    print("ANALIZADOR DE MERCADOS - OPENAI")
    print("=" * 60)

    todos_los_datos = ""

    for nombre, symbol in SYMBOLS.items():

        print(f"\nObteniendo datos de {nombre}...")

        h1 = obtener_velas(symbol, "1h", 300)
        m15 = obtener_velas(symbol, "15m", 300)

        print(f"H1 cerradas:  {len(h1)}")
        print(f"M15 cerradas: {len(m15)}")

        if len(h1) < 50 or len(m15) < 50:
            raise Exception(
                f"No hay suficientes datos para {nombre}."
            )

        todos_los_datos += preparar_datos(
            nombre,
            h1,
            m15
        )

    print("\nEnviando datos a OpenAI...")
    print("Modelo:", MODEL)

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

    print("\n")
    print("Análisis terminado.")


if __name__ == "__main__":
    main()
