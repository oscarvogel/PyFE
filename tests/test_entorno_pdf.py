# coding=utf-8
"""Que la librería de PDF que se importa sea la que dice requirements.txt.

Por que existe este archivo
---------------------------
El código se migró a `fpdf2`: hay `libs/fpdf_compat.py` entero para compensar
diferencias de fpdf2 con las plantillas viejas, y `probar_pdf.py` recorre la
cadena completa con fpdf2. Pero `requirements.txt` seguía pidiendo
`fpdf==1.7.2`, la versión de 2016, y no pedía fpdf2.

O sea: **el entorno que se probó no era el que el requirements describe**. En
una máquina nueva, `pip install -r requirements.txt` instala la librería de
2016 contra la que nadie probó este código, y el shim de compatibilidad queda
al revés de lo que existe para hacer funcionar. Acá pasaba inadvertido
porque en la máquina de desarrollo estaban las dos instaladas y ganaba fpdf2.

Dos cosas que no son evidentes y que por eso conviene que las mire un test:

1. `fpdf` y `fpdf2` **instalan en la misma carpeta** `site-packages/fpdf/`. Se
   pisan entre sí: desinstalar uno borra archivos del otro. Se comprobó
   desinstalando el `fpdf` viejo, y `fpdf.__version__` desapareció de la
   instalada de fpdf2. Se arregla reinstalando fpdf2.
2. Cuál de las dos gana el import depende del orden de instalación. Con las dos
   presente, el resultado no es una propiedad del código sino del estado de la
   máquina.
"""

import os
import re
import sys
from importlib import metadata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Las dos comparten el nombre de import (`fpdf`), y por eso el archivo se llama
# `fpdf` y no `fpdf2`.
PAQUETES = ("fpdf", "fpdf2")

PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;#]+)")


def _version_instalada(paquete):
    try:
        return metadata.version(paquete)
    except metadata.PackageNotFoundError:
        return None


def _instaladas():
    return {p: v for p, v in ((p, _version_instalada(p)) for p in PAQUETES) if v}


def _pins_de_requirements():
    """Los `paquete==version` de requirements.txt, en un diccionario."""
    ruta = os.path.join(RAIZ, "requirements.txt")
    with open(ruta, "r", encoding="utf-8") as f:
        texto = f.read()
    pins = {}
    for linea in texto.splitlines():
        linea = linea.split("#")[0].strip()
        if not linea:
            continue
        encontrado = PIN.match(linea)
        if encontrado:
            pins[encontrado.group(1).lower()] = encontrado.group(2)
    return {p: v for p, v in pins.items() if p.lower() in PAQUETES}


def test_no_conviven_las_dos_bibliotecas_de_pdf():
    """Tener las dos instaladas no es "tener una de más".

    Se pisan en la misma carpeta y el import queda a merced del orden de
    instalación. Además cada corrida tira el aviso queACA de fpdf2, que es la
    señal de que algo se esta accommodating sin querer.
    """
    instaladas = _instaladas()
    assert len(instaladas) <= 1, (
        "estan instaladas {} a la vez ({}). Se pisan en la misma carpeta y cual "
        "gana el import depende del orden de instalacion. Se deja una sola: "
        "pip uninstall fpdf".format(
            " y ".join(sorted(instaladas)),
            ", ".join("{}=={}".format(k, v) for k, v in sorted(instaladas.items()))))


def test_el_pin_de_requirements_es_el_que_se_importa():
    """El requirements tiene que describir la librería contra la que se probó.

    No alcanza con que funcione acá: si el pin no coincide con lo que se
    importa, el que instala en una máquina nueva recibe otra cosa, y el código
    se entera recién cuando genera una factura.
    """
    import fpdf

    version = getattr(fpdf, "__version__", None)
    assert version, (
        "fpdf.__version__ no existe, asi que el modulo importado no es fpdf2. "
        "Con fpdf y fpdf2 instalados a la vez se pisan en la misma carpeta.")

    pins = _pins_de_requirements()
    assert len(pins) == 1, (
        "requirements.txt deberia declarar una sola libreria de PDF, "
        "declara {}: {}".format(len(pins), pins))

    (paquete, version_pineada), = pins.items()
    assert version == version_pineada, (
        "requirements.txt pide {}=={} pero lo que se importa es fpdf {} "
        "({}). El codigo esta probado contra la que se importa, no contra la "
        "que dice el pin.".format(paquete, version_pineada, version, fpdf.__file__))
