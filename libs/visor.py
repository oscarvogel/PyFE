# coding=utf-8
"""Como se abre el PDF de un comprobante.

Por que no alcanza con os.startfile
------------------------------------
`os.startfile` le pasa el archivo al programa que Windows tenga asociado a
`.pdf`, y despues ese programa decide que hacer. Foxit PDF Reader, que es de
lo mas usado, corre como instancia unica: si ya tiene un documento abierto
**ignora el segundo archivo sin avisar nada**. El operador le da Imprimir, no
se abre nada, y no hay forma de saber si fallo la impresion o se quedo colgado
el visor: el PDF se genero y quedo guardado en `facturas/`, que es lo unico
que paso. Cerrar la ventana de Foxit no alcanza, porque el proceso sigue vivo
en la bandeja del sistema.

Por eso se abre con el navegador. No es el programa que el sistema tenga
asociado, pero todos los Windows vienen con uno, todos abren un PDF, y todos
abren una ventana nueva en vez de quedarse con la que ya estaba.

Ojo con `webbrowser.open`: NO sirve para esto. En Windows su
`WindowsDefault.open` es un `os.startfile(url)` envuelto en un try, asi que
abrir una URL `file://` con el termina en el mismo visor de PDF. Devuelve
True y no abria el navegador nunca. Por eso se busca el ejecutable.

Si no hay ningun navegador (una maquina de servidor, una imagen minima) se cae
al visor del sistema, porque peor es abrir con lo que haya que no abrir nada.
Y si tampoco, se devuelve None para que quien llame pueda avisar en vez de
dejar al operador creyendo que salio.
"""
import logging
import os
import subprocess

# (nombre, ruta relativa dentro de Program Files, Program Files (x86) o
# AppData\Local). Chrome y Edge pueden caer en cualquiera de las tres segun
# como se hayan instalado, asi que se buscan en las tres.
NAVEGADORES = (
    ("chrome", os.path.join("Google", "Chrome", "Application", "chrome.exe")),
    ("edge", os.path.join("Microsoft", "Edge", "Application", "msedge.exe")),
    ("firefox", os.path.join("Mozilla Firefox", "firefox.exe")),
)


def ruta_de_navegador():
    """El ejecutable del primer navegador instalado. None si no hay ninguno."""
    bases = (os.environ.get("ProgramFiles"),
             os.environ.get("ProgramFiles(x86)"),
             os.environ.get("LOCALAPPDATA"))
    for _nombre, relativa in NAVEGADORES:
        for base in bases:
            if not base:
                continue
            ruta = os.path.join(base, relativa)
            if os.path.isfile(ruta):
                return ruta
    return None


def abrir_pdf(ruta, imprimir=False):
    """Abre un PDF. Devuelve 'navegador', 'sistema' o None si no se pudo.

    Con `imprimir` se va derecho al visor del sistema con el verbo de
    impresion: el navegador no se puede mandar a la impresora de forma
    confiable, y mandar a la impresora equivocada es peor que no mandar.
    """
    if not ruta or not os.path.isfile(ruta):
        logging.error("no hay PDF para abrir: %r", ruta)
        return None

    ruta = os.path.abspath(ruta)

    if not imprimir:
        navegador = ruta_de_navegador()
        if navegador:
            try:
                subprocess.Popen([navegador, ruta])
                return 'navegador'
            except Exception as error:
                logging.debug("el navegador no abrio %s: %s", ruta, error)

    try:
        os.startfile(ruta, 'print' if imprimir else '')
        return 'sistema'
    except Exception as error:
        logging.error("no se pudo abrir %s con el visor del sistema: %s",
                      ruta, error)
        return None
