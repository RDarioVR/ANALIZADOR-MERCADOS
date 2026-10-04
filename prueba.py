import requests

ACTIVOS = {
    "EURUSD": "EUR/USD",
    "XAUUSD": "ORO"
}

TEMPORALIDADES = {
    "1h": "H1",
    "15m": "M15"
}


def obtener_velas(simbolo, intervalo):
    url = f"https://biquote.io/api/{simbolo}/ohlc"

    parametros = {
        "interval": intervalo,
        "limit": 10
    }

    respuesta = requests.get(
        url,
        params=parametros,
        timeout=15
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    return datos["bars"]


def main():

    print("=" * 60)
    print("PRUEBA DE DATOS DE MERCADO")
    print("=" * 60)

    for simbolo, nombre in ACTIVOS.items():

        print(f"\n### {nombre} ({simbolo})")

        for intervalo, nombre_tf in TEMPORALIDADES.items():

            print(f"\n--- {nombre_tf} ---")

            try:

                velas = obtener_velas(
                    simbolo,
                    intervalo
                )

                # Eliminamos la vela que todavía está abierta
                velas_cerradas = [
                    vela
                    for vela in velas
                    if not vela.get("isOpen", False)
                ]

                print(
                    f"Velas recibidas: "
                    f"{len(velas_cerradas)}"
                )

                # Mostramos las últimas 3
                for vela in velas_cerradas[:3]:

                    print(
                        f"{vela['openTime']} | "
                        f"O: {vela['open']} | "
                        f"H: {vela['high']} | "
                        f"L: {vela['low']} | "
                        f"C: {vela['close']}"
                    )

            except Exception as error:

                print(
                    f"ERROR en {simbolo} "
                    f"{nombre_tf}: {error}"
                )

    print("\n" + "=" * 60)
    print("PRUEBA TERMINADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
