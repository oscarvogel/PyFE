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
que paso.

Por eso se abre con el navegador. No es el programa que el sistema tenga
asociado, pero todos los Windows vienen con uno, todos abren un PDF, y todos
abren una ventana nueva en vez de quedarse con la que ya estaba.

Si el navegador no se puede lanzar (una maquina sin navegador configurado) se
cae al visor del sistema, porque peor es abrir con lo que haya que no abrir
nada. Y si tampoco, se devuelve None para que quien llame pueda avisar en vez
de dejar al operador creyendo que salio.
"""
import logging
import os
import webbrowser
from urllib.parse import urljoin
from urllib.request import pathname2url


def url_de_archivo(ruta):
    """La URL file:// de un archivo local.

    `pathname2url` en Windows ya devuelve `///C:/...`, con las tres barras. Si
    se le pone `file:///` adelante quedan seis, y esa URL no la entiende
    cualquiera. `urljoin` une las dos partes y sale bien.
    """
    return urljoin("file:", pathname2url(os.path.abspath(ruta)))


def abrir_pdf(ruta, imprimir=False):
    """Abre un PDF. Devuelve 'navegador', 'sistema' o None si no se pudo.

    Con `imprimir` se va derecho al visor del sistema con el verbo de
    impresion: el navegador no se puede mandar a la impresora de forma
    confiable, y mandar a la impresora equivocada es peor que no mandar.
    """
    if not ruta or not os.path.isfile(ruta):
        logging.error("no hay PDF para abrir: %r", ruta)
        return None

    if not imprimir:
        try:
            if webbrowser.open(url_de_archivo(ruta), new=2):
                return 'navegador'
        except Exception as error:  # pragma: no cover - depende del sistema
            logging.debug("el navegador no abrio %s: %s", ruta, error)

    try:
        os.startfile(ruta, 'print' if imprimir else '')
        return 'sistema'
    except Exception as error:
        logging.error("no se pudo abrir %s con el visor del sistema: %s",
                      ruta, error)
        return None
