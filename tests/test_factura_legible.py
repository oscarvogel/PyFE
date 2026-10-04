"""La factura tiene que ser legible: mira los colores del PDF, no su cabecera.

El sintoma
----------
La factura se emitia, se guardaba y el PDF existia. Y salia con la PAGINA NEGRA
y los textos en cian. Un comprobante ilegible es peor que ninguno: parece valido.

Por que paso
------------
Las plantillas de pyfepdf (factura_qr.csv, factura-fce.csv, remito.csv) traen
en la columna de fondo 65535 (0x00FFFF, cian) y 0 (negro). En fpdf 1.7 esos
valores no se pintaban: eran 'sin relleno'. La plantilla de fpdf2 declara

    background: Optional[int] = None    # None = sin relleno
    if background is None: fill = False
    else:                 fill = True

o sea que CUALQUIER entero se pinta, incluido el 0. El marco exterior de la
hoja ('Cuadro', 200 x 278 mm) quedaba relleno de negro y los textos de cian.

Por que el test anterior no lo agarro
--------------------------------------
Miraba que el archivo empezara con %PDF- y pesara mas de 1000 bytes. Eso dice
que se genero un PDF, no que se pueda leer. Un test que no mira el render no
agarra un problema de render.
"""

import os
import re
import sys
import zlib
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


# -- La regla, que es lo barato de testear ---------------------------------

def _elemento(tipo, fondo):
    return {"type": tipo, "background": fondo}


@pytest.mark.parametrize("fondo", [0, 0x00FFFF, "0", "00FFFF"])
def test_un_texto_con_fondo_heredado_queda_blanco(fondo):
    """Con fpdf2 un texto necesita un fondo de verdad: blanco."""
    from libs.fpdf_compat import normalizar_fondos

    elementos = [_elemento("T", fondo)]
    assert normalizar_fondos(elementos) == 1
    assert elementos[0]["background"] == 0xFFFFFF


@pytest.mark.parametrize("tipo", ["B", "L", "I", "BC", "b", "l"])
@pytest.mark.parametrize("fondo", [0, 0x00FFFF])
def test_un_marco_una_linea_o_una_imagen_quedan_sin_relleno(tipo, fondo):
    """Un marco pintado tapa la pagina entera. Una imagen pintada, la imagen.

    El 'Cuadro' de la plantilla es el marco de 200 x 278 mm: relleno de negro
    tapa la hoja entera. Ese fue el blackness de la pagina negra.
    """
    from libs.fpdf_compat import normalizar_fondos

    elementos = [_elemento(tipo, fondo)]
    assert normalizar_fondos(elementos) == 1
    assert elementos[0]["background"] is None


def test_un_fondo_de_verdad_no_se_toca():
    """Los colores de la plantilla de marca se respetan."""
    from libs.fpdf_compat import normalizar_fondos

    elementos = [_elemento("T", 0x988970), _elemento("B", 0x3359061)]
    assert normalizar_fondos(elementos) == 0
    assert elementos[0]["background"] == 0x988970
    assert elementos[1]["background"] == 0x3359061


def test_sin_fondo_no_inventa_uno():
    from libs.fpdf_compat import normalizar_fondos

    elementos = [_elemento("T", None)]
    assert normalizar_fondos(elementos) == 0
    assert elementos[0]["background"] is None


# -- El PDF de verdad -------------------------------------------------------

def _flujos_de_contenido(ruta):
    datos = open(ruta, "rb").read()
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", datos, re.S):
        crudo = m.group(1)
        try:
            yield zlib.decompress(crudo).decode("latin1", "replace")
        except Exception:
            yield crudo.decode("latin1", "replace")


def _contenido_del_pdf(ruta):
    for flujo in _flujos_de_contenido(ruta):
        if " Tj" in flujo or " re" in flujo:
            return flujo
    return ""


@pytest.fixture(scope="module")
def pdf_generado():
    """Un PDF hecho de verdad, con el FEPDF de verdad y la plantilla real."""
    import shutil
    import subprocess

    carpeta = os.path.join(RAIZ, "_sandbox_prueba", "test_legible")
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta, ignore_errors=True)
    os.makedirs(carpeta)
    shutil.copytree(os.path.join(RAIZ, "plantillas"),
                    os.path.join(carpeta, "plantillas"))

    from libs import fpdf_compat
    from pyafipws.pyfepdf import FEPDF

    fpdf_compat.normalizar_fondos  # que este importado vale

    f = FEPDF()
    f.CUIT = "20345678907"
    f.CargarFormato(os.path.join(carpeta, "plantillas", "factura_qr.csv"))

    # CrearFactura ARMA self.factura, y tanto CrearPlantilla como
    # ProcesarPlantilla la leen. Si va despues, CrearPlantilla ya revienta con
    # KeyError: 'tipo_cbte' y no llega a dibujar nada.
    f.CrearFactura(
        1,                  # concepto: productos
        "96", "11111111",   # tipo y numero de documento del cliente
        6, "0001", "00000001",
        Decimal("121.00"), "0.00", Decimal("100.00"), Decimal("21.00"),
        "0.00", "20260901", "20260901",
        "20260901", "20260901",
        "PES", Decimal("1.000"),
        "71234567890123", "20260911", "",
        "UN CLIENTE", "Una calle 123", 0,
    )

    f.CrearPlantilla("A4", "portrait")
    _alineados, _fuentes, _fondos = fpdf_compat.normalizar_plantilla(f)
    f.ProcesarPlantilla(1, 24, "izq")
    salida = os.path.join(carpeta, "prueba.pdf")
    f.GenerarPDF(salida)
    return salida


def test_el_pdf_no_pinta_la_pagina_entera(pdf_generado):
    """El sintoma exacto: un re B del tamano de la hoja, relleno de negro.

    Con el fondo del marco corregido a None, la operacion de la hoja tiene que
    ser S (solo contorno) y no B (contorno y relleno).
    """
    contenido = _contenido_del_pdf(pdf_generado)
    assert contenido, "el PDF no tiene flujo de contenido"

    # La hoja es el primer rectangulo: algo de 566 x 790 puntos es A4.
    rectangulos = re.findall(r"([\d.-]+ [\d.-]+ [\d.-]+ [\d.-]+) re ([fSbB]*)",
                             contenido)
    assert rectangulos, "no hay rectangulos en el PDF"

    hojas = [r for r in rectangulos
             if abs(float(r[0].split()[2])) > 500
             and abs(float(r[0].split()[3])) > 700]
    for medidas, operador in hojas:
        assert "f" not in operador.lower(), \
            "la pagina se esta rellenando (operador {!r}): sale negra".format(operador)


def test_el_pdf_no_usa_el_cian_heredado(pdf_generado):
    """0x00FFFF era el fondo de 459 campos de texto de la plantilla vieja."""
    contenido = _contenido_del_pdf(pdf_generado)

    assert "0 1 1 rg" not in contenido, \
        "el PDF dibuja en cian (0 1 1): el fondo heredado de la plantilla se sigue pintando"
    assert "0 1 1 RG" not in contenido


def test_el_pdf_dibuja_texto_negro_sobre_blanco(pdf_generado):
    """Lo contrario: tiene que haber texto negro y celdas blancas."""
    contenido = _contenido_del_pdf(pdf_generado)

    assert "0 g" in contenido or "0 0 0 rg" in contenido, \
        "no se dibuja texto negro: el comprobante no se leeria"
    assert "1 1 1 rg" in contenido, \
        "no hay celdas blancas: el texto queda sobre lo que haya detras"

