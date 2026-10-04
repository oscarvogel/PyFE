"""El parseo de la sincronizacion de alicuotas, sin tocar ARCA ni la base.

La parte que importa testear sin red es el parseo: si se mezcla el orden de las
columnas, cada alicuota queda con el codigo de otra y el error aparece al
emitir, con la factura a medias. Por eso se prueba con respuestas falsas que se
ven exactamente como las que devuelve ParamGetTiposIva, que es un
'id|descripcion|fchDesde|fchHasta'.
"""

import os
import sys
from decimal import Decimal

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import importlib.util  # noqa: E402

import pytest  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "sincronizar_alicuotas",
    os.path.join(RAIZ, "tools", "sincronizar_alicuotas.py"))
sa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sa)


# Una respuesta con la forma que devuelve pyafepdf: cuatro columnas separadas
# por "|", con la ultima vacia cuando no hay fecha de hasta.
RESPUESTA = [
    "01|IVA General|2010-09-17|",
    "02|Decreto 493/01|2010-09-17|",
    "03|IVA 27%|2010-09-17|",
    "04|IVA 10,5%|2010-09-17|",
    "05|IVA 5%|2010-09-17|",
    "06|IVA 2,5%|2010-09-17|",
    "07|Exento|2010-09-17|",
    "08|No gravado|2010-09-17|",
    "09|Ventas a tasa especial|2010-09-17|",
    "50|Conceptos no gravados|2010-09-17|",
]


def test_el_parseo_saca_cuatro_campos():
    filas = sa._parsear(RESPUESTA)

    assert filas[0] == ("01", "IVA General", "2010-09-17", "")


def test_una_linea_con_menos_de_cuatro_campos_no_rompe():
    """Si ARCA agrega una linea raro, no tiene que reventar la sincronizacion."""
    filas = sa._parsear(["01|IVA General"])

    assert filas == [("01", "IVA General", "", "")]


def test_el_porcentaje_se_saca_cuando_la_descripcion_lo_dice():
    assert sa._porcentaje_explicito("IVA 27%") == Decimal("27")
    assert sa._porcentaje_explicito("IVA 10,5%") == Decimal("10.5")
    assert sa._porcentaje_explicito("IVA 2,5%") == Decimal("2.5")


def test_una_descripcion_sin_porcentaje_no_inventa_el_valor():
    """"IVA General" es el 21% y "Decreto 493/01" el 10,5%, pero ninguno de los
    dos nombres lo dice. Adivinar ahi es escribir 0 en una alicuota del 21%:
    un renglon al 21% pasaría a informar 0%, y eso no se ve hasta que hay una
    factura de un cliente.

    Por eso se devuelve None, no un numero.
    """
    assert sa._porcentaje_explicito("IVA General") is None
    assert sa._porcentaje_explicito("Decreto 493/01") is None
    assert sa._porcentaje_explicito("Exento") is None
    assert sa._porcentaje_explicito("") is None


def test_una_respuesta_vacia_avisa_en_vez_de_silbar():
    """Si ARCA no devuelve nada, hay que decirlo, no dejar la base como estaba
    sin avisar."""
    class _FeVacio(object):
        def ParamGetTiposIva(self, sep="|"):
            return []

    with pytest.raises(RuntimeError) as excepcion:
        sa.sincronizar(_FeVacio())

    assert "certificado" in str(excepcion.value).lower() or \
        "alicuota" in str(excepcion.value).lower()


def test_la_sincronizacion_no_borra_nada():
    """Agrega y actualiza, nunca borra.

    Si el administrador cargo una alicuota propia, se queda. Borrar filas de un
    maestro que el usuario edito es la forma rapida de perder trabajo.
    """
    from peewee import SqliteDatabase
    from modelos.Tipoiva import Tipoiva

    db = SqliteDatabase(":memory:")
    Tipoiva._meta.set_database(db)
    db.create_tables([Tipoiva])
    Tipoiva.create(codigo="01", descrip="IVA General", iva=Decimal("21"))
    Tipoiva.create(codigo="99", descrip="ALICUOTA DEL USUARIO",
                   iva=Decimal("13"))

    class _Fe(object):
        def ParamGetTiposIva(self, sep="|"):
            return ["01|IVA General|2010-09-17|", "03|IVA 27%|2010-09-17|"]

    resumen = sa.sincronizar(_Fe())

    assert resumen["altas"] == 1, "deberia agregar solo la 27"
    assert resumen["sin_porcentaje"] == []
    assert Tipoiva.get_or_none(Tipoiva.codigo == "99") is not None, \
        "borro una alicuota que cargo el usuario"
    assert Tipoiva.get(Tipoiva.codigo == "03").iva == Decimal("27")


def test_los_codigos_entran_en_el_largo_de_la_columna():
    """codigo es VARCHAR(2): un codigo de tres caracteres lo rompe."""
    from peewee import SqliteDatabase
    from modelos.Tipoiva import Tipoiva

    db = SqliteDatabase(":memory:")
    Tipoiva._meta.set_database(db)
    db.create_tables([Tipoiva])

    class _Fe(object):
        def ParamGetTiposIva(self, sep="|"):
            return ["001|IVA RARO|2010-09-17|"]

    resumen = sa.sincronizar(_Fe())

    # Truncar "001" a dos caracteres lo convertiria en "00", que es otro
    # codigo, y meteria una fila silenciosamente equivocada. Se descarta.
    assert resumen["codigos_malos"] == [("001", "IVA RARO")]
    assert Tipoiva.get_or_none(Tipoiva.codigo == "00") is None
    assert Tipoiva.get_or_none(Tipoiva.codigo == "01") is None
