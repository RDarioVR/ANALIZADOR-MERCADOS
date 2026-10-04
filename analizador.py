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
