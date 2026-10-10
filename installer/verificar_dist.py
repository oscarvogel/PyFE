# coding=utf-8
"""Chequea que la carpeta dist tenga todo lo que la app necesita.

Sirve porque los datos (imagenes, conf) tienen que estar SUELTOS al lado
del .exe: el sistema.ini los referencia con rutas relativas, asi que si
no viajan sueltos la app arranca y falla al mostrar una pantalla.

Uso:  python installer\verificar_dist.py [carpeta]
"""

import os
import sys

CARPETAS_ESPERADAS = {
    "conf": ["afip_ca_info.crt"],
    "imagenes": None,          # cualquiera, pero tiene que haber
    "temas": ["pyfe.css"],     # sin esto la app arranca sin ningun estilo
    "plantillas": None,
    "certificados": None,      # vacia esta bien: la llena el asistente
    "excel": None,
    # Los datos maestros se cargan al crear la base. Sin esta carpeta, una
    # instalacion nueva queda con la base VACIA: sin alicuotas de IVA, sin
    # tipos de comprobante y sin formas de pago, o sea, sin poder facturar.
    "data": ["tipoiva.csv", "tipodoc.csv", "tiporesp.csv", "tipocomprobante.csv",
             "formapago.csv", "cuotaspago.csv", "provincias.csv", "localidades.csv",
             "unidad.csv", "impuestos.csv", "centrocostos.csv", "grupos.csv"],
}

ARCHIVOS_ESPERADOS = [
    "main.exe",
    "sistema.ini.example",
    # PyInstaller mete este archivo DENTRO del .exe (--version-file), pero la
    # app lo lee en tiempo de ejecucion buscando el archivo suelto en las
    # carpetas de la instalacion. Si falta este, la barra de estado y Acerca de
    # muestran la version vacia y no da ningun error.
    "version.txt",
]

# Archivos que el tema necesita para verse bien. Los dibuja
# tools/generar_recursos_tema.py y van dentro de temas/recursos/.
RECURSOS_TEMA = [
    os.path.join("temas", "recursos", "chevron-abajo.png"),
    os.path.join("temas", "recursos", "chevron-derecha.png"),
    os.path.join("temas", "recursos", "buscar.png"),
]


# Los archivos que el codigo pide en tiempo de ejecucion. Si falta alguno, la
# app arranca, autoriza y guarda, pero NO genera el PDF. Son el papel de la
# factura: sin esto no hay documento para entregar.
ARCHIVOS_QUE_SI_SI_SE_USAN = [
    "plantillas/factura_qr.csv",     # formato por defecto (Facturas.py)
    "plantillas/factura_moderna.html",  # formato HTML alternativo
    "plantillas/factura-fce.csv",    # comprobantes electronicos (FCE)
    "plantillas/logo.png",           # logo del emisor impreso
    "plantillas/remito.csv",         # remitos
]


def verificar(dist):
    problemas, avisos = [], []

    for nombre in ARCHIVOS_ESPERADOS:
        ruta = os.path.join(dist, nombre)
        if not os.path.exists(ruta):
            problemas.append("falta {}".format(nombre))

    for carpeta, requeridos in CARPETAS_ESPERADAS.items():
        ruta = os.path.join(dist, carpeta)
        if not os.path.isdir(ruta):
            problemas.append("falta la carpeta {}/".format(carpeta))
            continue
        archivos = [f for f in os.listdir(ruta)
                    if os.path.isfile(os.path.join(ruta, f))]
        if requeridos:
            for r in requeridos:
                if r not in archivos:
                    problemas.append("falta {}/{}".format(carpeta, r))
        elif not archivos and carpeta not in ("certificados", "excel"):
            avisos.append("{}/ esta vacia".format(carpeta))

    # Los graficos del tema van dentro de temas/recursos/: si faltan, los
    # controles se ven igual pero sin flecha en los desplegables, y eso es
    # un detalle que nadie detecta hasta que un cliente lo ve.
    for relativo in RECURSOS_TEMA:
        if not os.path.isfile(os.path.join(dist, relativo)):
            problemas.append("falta el recurso del tema {}".format(relativo.replace("\\", "/")))

    # Las plantillas de la factura. Estas NO son un detalle: sin ellas la app
    # autoriza y guarda el comprobante pero no genera el PDF, y el cliente se
    # queda sin documento. Pasaron meses sin que nada las pidiera.
    for relativo in ARCHIVOS_QUE_SI_SI_SE_USAN:
        if not os.path.isfile(os.path.join(dist, relativo.replace("/", os.sep))):
            problemas.append(
                "falta {}: sin esta plantilla la factura se autoriza y se "
                "guarda pero NO se imprime".format(relativo))

    return problemas, avisos


def main():
    dist = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

    print("Revisando:", dist)
    if not os.path.isdir(dist):
        print("ERROR: no existe. Corrir compila.bat primero.")
        return 1

    problemas, avisos = verificar(dist)

    for a in avisos:
        print("  aviso  :", a)
    for p in problemas:
        print("  FALTA  :", p)

    if problemas:
        print("\nLa distribucion esta incompleta. No empaquetar asi.")
        return 1
    print("\nDistribucion completa: se puede generar el instalador.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
