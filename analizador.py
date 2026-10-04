import requests
from datetime import datetime, timezone


# ============================================================
# CONFIGURACIÓN
# ============================================================

ACTIVOS = {
    "EURUSD": "EUR/USD",
    "XAUUSD": "ORO"
}

API_BASE = "https://biquote.io/api"

H1_BARRAS = 250
M15_BARRAS = 400


# ============================================================
# OBTENER DATOS
# ============================================================

def obtener_velas(simbolo, intervalo, limite):
    url = f"{API_BASE}/{simbolo}/ohlc"

    respuesta = requests.get(
        url,
        params={
            "interval": intervalo,
            "limit": limite
        },
        timeout=20
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    velas = [
        v for v in datos["bars"]
        if not v.get("isOpen", False)
    ]

    velas.sort(key=lambda x: x["openTime"])

    return velas


# ============================================================
# UTILIDADES
# ============================================================

def cierre(v):
    return float(v["close"])


def maximo(v):
    return float(v["high"])


def minimo(v):
    return float(v["low"])


def promedio(lista):
    if not lista:
        return 0

    return sum(lista) / len(lista)


def calcular_ema(valores, periodo):
    if len(valores) < periodo:
        return None

    multiplicador = 2 / (periodo + 1)

    ema = promedio(valores[:periodo])

    for precio in valores[periodo:]:
        ema = (
            (precio - ema) * multiplicador
        ) + ema

    return ema


def calcular_atr(velas, periodo=14):
    if len(velas) < periodo + 1:
        return None

    trs = []

    for i in range(1, len(velas)):
        actual = velas[i]
        anterior = velas[i - 1]

        high = maximo(actual)
        low = minimo(actual)
        prev_close = cierre(anterior)

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )

        trs.append(tr)

    return promedio(trs[-periodo:])


def redondear(precio, simbolo):
    if simbolo == "XAUUSD":
        return round(precio, 2)

    return round(precio, 5)


# ============================================================
# ESTRUCTURA DE MERCADO
# ============================================================

def detectar_tendencia_h1(velas):
    cierres = [cierre(v) for v in velas]

    ema20 = calcular_ema(cierres, 20)
    ema50 = calcular_ema(cierres, 50)

    if ema20 is None or ema50 is None:
        return "NEUTRAL"

    precio = cierres[-1]

    if precio > ema20 > ema50:
        return "ALCISTA"

    if precio < ema20 < ema50:
        return "BAJISTA"

    return "NEUTRAL"


def rango_reciente(velas, cantidad=20):
    grupo = velas[-cantidad:]

    resistencia = max(maximo(v) for v in grupo)
    soporte = min(minimo(v) for v in grupo)

    return soporte, resistencia


def detectar_estructura_m15(velas):
    if len(velas) < 30:
        return "NEUTRAL"

    ultimas = velas[-25:]

    mitad = len(ultimas) // 2

    primera = ultimas[:mitad]
    segunda = ultimas[mitad:]

    max_primera = max(maximo(v) for v in primera)
    max_segunda = max(maximo(v) for v in segunda)

    min_primera = min(minimo(v) for v in primera)
    min_segunda = min(minimo(v) for v in segunda)

    if max_segunda > max_primera and min_segunda > min_primera:
        return "ALCISTA"

    if max_segunda < max_primera and min_segunda < min_primera:
        return "BAJISTA"

    return "NEUTRAL"


# ============================================================
# CONFIRMACIÓN DE IMPULSO
# ============================================================

def confirmar_impulso(velas, direccion):
    if len(velas) < 5:
        return False

    ultimas = velas[-5:]

    cierres = [cierre(v) for v in ultimas]

    if direccion == "BUY":
        return (
            cierres[-1] > cierres[-2]
            and cierres[-2] >= cierres[-3]
        )

    if direccion == "SELL":
        return (
            cierres[-1] < cierres[-2]
            and cierres[-2] <= cierres[-3]
        )

    return False


# ============================================================
# GENERACIÓN DE SEÑAL
# ============================================================

def analizar_activo(simbolo, nombre):
    print("\n" + "=" * 65)
    print(f"ANÁLISIS: {nombre}")
    print("=" * 65)

    try:
        h1 = obtener_velas(
            simbolo,
            "1h",
            H1_BARRAS
        )

        m15 = obtener_velas(
            simbolo,
            "15m",
            M15_BARRAS
        )

    except Exception as error:
        print(f"ERROR OBTENIENDO DATOS: {error}")

        return {
            "activo": nombre,
            "senal": "ERROR",
            "entrada": None,
            "sl": None,
            "tp": None,
            "razon": str(error)
        }

    if len(h1) < 60 or len(m15) < 60:
        return {
            "activo": nombre,
            "senal": "NO OPERAR",
            "entrada": None,
            "sl": None,
            "tp": None,
            "razon": "Datos insuficientes"
        }

    # --------------------------------------------------------
    # CONTEXTO H1
    # --------------------------------------------------------

    tendencia_h1 = detectar_tendencia_h1(h1)

    # --------------------------------------------------------
    # ESTRUCTURA M15
    # --------------------------------------------------------

    estructura_m15 = detectar_estructura_m15(m15)

    # --------------------------------------------------------
    # PRECIO Y ATR
    # --------------------------------------------------------

    precio = cierre(m15[-1])

    atr = calcular_atr(m15, 14)

    if atr is None or atr <= 0:
        return {
            "activo": nombre,
            "senal": "NO OPERAR",
            "entrada": None,
            "sl": None,
            "tp": None,
            "razon": "ATR no disponible"
        }

    soporte, resistencia = rango_reciente(
        m15,
        20
    )

    # --------------------------------------------------------
    # DECISIÓN
    # --------------------------------------------------------

    direccion = None

    if (
        tendencia_h1 == "ALCISTA"
        and estructura_m15 == "ALCISTA"
        and confirmar_impulso(m15, "BUY")
    ):
        direccion = "BUY"

    elif (
        tendencia_h1 == "BAJISTA"
        and estructura_m15 == "BAJISTA"
        and confirmar_impulso(m15, "SELL")
    ):
        direccion = "SELL"

    # --------------------------------------------------------
    # SIN CONFIGURACIÓN
    # --------------------------------------------------------

    if direccion is None:
        print("SEÑAL: NO OPERAR")
        print(f"H1: {tendencia_h1}")
        print(f"M15: {estructura_m15}")
        print(f"Precio: {precio}")

        return {
            "activo": nombre,
            "senal": "NO OPERAR",
            "entrada": precio,
            "sl": None,
            "tp": None,
            "razon": (
                f"H1={tendencia_h1}, "
                f"M15={estructura_m15}"
            )
        }

    # --------------------------------------------------------
    # STOP LOSS
    # --------------------------------------------------------

    if direccion == "BUY":

        sl = min(
            soporte,
            precio - atr * 1.2
        )

        riesgo = precio - sl

        if riesgo <= 0:
            return {
                "activo": nombre,
                "senal": "NO OPERAR",
                "entrada": precio,
                "sl": None,
                "tp": None,
                "razon": "SL inválido"
            }

        tp = precio + riesgo * 2.5

    else:

        sl = max(
            resistencia,
            precio + atr * 1.2
        )

        riesgo = sl - precio

        if riesgo <= 0:
            return {
                "activo": nombre,
                "senal": "NO OPERAR",
                "entrada": precio,
                "sl": None,
                "tp": None,
                "razon": "SL inválido"
            }

        tp = precio - riesgo * 2.5

    entrada = redondear(precio, simbolo)
    sl = redondear(sl, simbolo)
    tp = redondear(tp, simbolo)

    print(f"SEÑAL: {direccion}")
    print(f"H1: {tendencia_h1}")
    print(f"M15: {estructura_m15}")
    print(f"Entrada: {entrada}")
    print(f"Stop Loss: {sl}")
    print(f"Take Profit: {tp}")

    return {
        "activo": nombre,
        "senal": direccion,
        "entrada": entrada,
        "sl": sl,
        "tp": tp,
        "razon": (
            f"H1={tendencia_h1}, "
            f"M15={estructura_m15}, "
            f"ATR={round(atr, 6)}"
        )
    }


# ============================================================
# RESUMEN
# ============================================================

def main():

    ahora = datetime.now(timezone.utc)

    print("\n")
    print("############################################################")
    print("#          ANALIZADOR AUTOMÁTICO DE MERCADOS              #")
    print("############################################################")

    print(
        f"Hora UTC: {ahora.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    resultados = []

    for simbolo, nombre in ACTIVOS.items():

        resultado = analizar_activo(
            simbolo,
            nombre
        )

        resultados.append(resultado)

    # --------------------------------------------------------
    # TABLA FINAL
    # --------------------------------------------------------

    print("\n")
    print("############################################################")
    print("#                     RESULTADO FINAL                     #")
    print("############################################################")

    print(
        f"{'ACTIVO':<12}"
        f"{'SEÑAL':<12}"
        f"{'ENTRADA':<14}"
        f"{'SL':<14}"
        f"{'TP':<14}"
    )

    print("-" * 66)

    for resultado in resultados:

        print(
            f"{resultado['activo']:<12}"
            f"{resultado['senal']:<12}"
            f"{str(resultado['entrada']):<14}"
            f"{str(resultado['sl']):<14}"
            f"{str(resultado['tp']):<14}"
        )

    print("\nANÁLISIS TERMINADO.")


if __name__ == "__main__":
    main()
