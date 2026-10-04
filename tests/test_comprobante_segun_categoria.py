"""Que tipo de comprobante elige la app segun la categoria de IVA del emisor.

La regla esta en Facturas.py:132-138:

    cat_iva == 1 (Responsable Inscripto)  ->  A si el cliente es RI, B si no
    cat_iva distinto de 1                 ->  Factura C

O sea que un monotributo emite Factura C, y en ningun camino de esa rama
aparece un 82 (Tique). Confundir esas dos cosas casi hace cambiar una
configuracion real: con cat_iva = 6 en una instalacion nueva, el comprobante
que corresponde es C.

Y al reves tambien: un CUIT que NO es monotributo no puede emitir Factura C, y
con cat_iva = 6 la app la elige igual. Por eso la categoria de IVA no se cambia
a ojo: tiene que coincidir con como esta anotado el CUIT en ARCA.

Como se prueba
--------------
Sobre lo que la app DECIDE, no sobre el combo que muestra. El combo arma sus
items desde la base, con el nombre del tipo de comprobante como dato, y su
setText busca por dato: si el nombre no coincide con lo que hay en la base, se
vacia en silencio y no se puede afirmar nada sobre el texto final. Lo que
importa es cual de los dos textos le pasa la app, y eso se anota interceptando
el setText del combo.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


class _Falso(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


def _cliente(tiporesp_id, nombre="UN CLIENTE"):
    return _Falso(
        idcliente=1,
        nombre=nombre,
        domicilio="Una calle 123",   # lo lee CargaDatosCliente
        cuit="20345678907",
        dni=11111111,
        tiporesp_id=tiporesp_id,
        tiporesp=_Falso(idtiporesp=tiporesp_id, nombre="RESP. INSCRIPTO",
                         condicion_iva_receptor_id=1),
        localidad=_Falso(nombre="CAPITAL", provincia="CABA"),
        percepcion=_Falso(detalle="IIBB"),
    )


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _que_comprobante_elige(cat_iva, cliente, monkeypatch):
    """Lo que la app le pasa al combo, sin ARCA ni base de por medio."""
    import controladores.Facturas as FAC

    # NO se cambia de carpeta aca. El controlador se construye con los combos
    # ya cargados desde la base de la maquina, y un chdir a una carpeta vacia
    # hace que peewee enganche ahi y reviente con 'no such table: tiporesp'.
    # El sistema.ini no hace falta tocarlo: LeerIni va parcheado.

    # Facturas.py hace 'from libs.Utiles import LeerIni', asi que tiene su
    # propia referencia. Parchear libs.Utiles.LeerIni no la toca, y el test
    # terminaria leyendo el sistema.ini de verdad.
    monkeypatch.setattr(FAC, "LeerIni",
                        lambda clave=None, key=None, carpeta="": (
                            str(cat_iva) if clave == "cat_iva" else ""))

    # La consulta real es Cliente.select().where(...).get(), no un get_by_id.
    # Un doble con get_by_id no se llega a usar: la excepcion se come el error
    # de firma y CargaDatosCliente sale por el except sin elegir nada.
    class _Consulta(object):
        def __init__(self, cliente):
            self._cliente = cliente

        def where(self, *args, **kwargs):
            return self

        def get(self):
            return self._cliente

    class ClienteFalso(object):
        # Se usa como Cliente.idcliente del lado derecho del where.
        idcliente = "idcliente_falso"

        # El codigo tiene 'except Cliente.DoesNotExist'. Python evalua esa
        # clausula SOLO si hubo una excepcion, y sin este atributo el
        # AttributeError del eval tapa el error real. Con el atributo falso,
        # la excepcion original queda a la vista.
        class DoesNotExist(Exception):
            pass

        @staticmethod
        def select():
            return _Consulta(cliente)

    monkeypatch.setattr(FAC, "Cliente", ClienteFalso)
    monkeypatch.setattr(FAC, "ParamSist",
                        _Falso(ObtenerParametro=lambda clave: None))
    # ObtieneNumeroFactura llama a ARCA. No es lo que se prueba.
    monkeypatch.setattr(FAC.FEv1, "UltimoComprobante",
                        lambda self, tipo=None, ptovta=None: 0)

    c = FAC.FacturaController()
    c.view.Cerrar = lambda: None

    # Sin esto, CargaDatosCliente sale en la primera linea: es un metodo que
    # carga los datos DEL cliente que ya este elegido, y si no hay ninguno
    # elegido no hay nada que cargar. Es una guarda, no un fallo.
    c.view.validaCliente.setText(str(cliente.idcliente))

    # Se anota lo que se le pasa, en vez de leer el combo: ver la nota de
    # arriba sobre por que el texto del combo no sirve para afirmar.
    elegido = []
    c.view.cboComprobante.setText = lambda texto: elegido.append(texto)

    try:
        c.CargaDatosCliente()
    except Exception as e:
        return "<error: {}: {}>".format(type(e).__name__, e)

    return elegido[0] if elegido else "<no eligio nada>"


@pytest.mark.parametrize("cat_iva", ["6", "5", "13", "4", "8", "9", "16"])
def test_cualquier_categoria_que_no_sea_1_emite_factura_c(
        qt, monkeypatch, cat_iva):
    """Monotributo (6) emite C, y tambien las demas que no son RI.

    Ninguna de estas produce un 82 (Tique): el Tique no aparece en esta rama.
    """
    elegido = _que_comprobante_elige(cat_iva, _cliente(2), monkeypatch)

    assert elegido == "Factura C", \
        "con cat_iva = {} la app eligio {!r}".format(cat_iva, elegido)


def test_responsable_inscripto_manda_factura_a_a_un_ri(qt, monkeypatch):
    elegido = _que_comprobante_elige("1", _cliente(2), monkeypatch)

    assert elegido == "Factura A"


@pytest.mark.parametrize("tipo_cliente", [1, 3, 4])
def test_responsable_inscripto_manda_factura_b_a_un_no_ri(
        qt, monkeypatch, tipo_cliente):
    """Cliente monotributo, consumidor final o exento: va B."""
    elegido = _que_comprobante_elige("1", _cliente(tipo_cliente), monkeypatch)

    assert elegido == "Factura B"


def test_una_categoria_vacia_cae_en_responsable_inscripto(qt, monkeypatch):
    """Un cat_iva vacio se trata como Responsable Inscripto, no como 'no se'.

    Se suponia lo contrario: que vacio fuera 'no es 1' y por lo tanto Factura
    C. Lo que hace es a_entero(LeerIni(...), 1), y a_entero devuelve 1 cuando
    no puede leer un numero, o sea que el valor por defecto ES 1.

    O sea que una categoria faltante no se detecta como faltante: sale una
    Factura A como si la empresa fuera RI. Si en realidad es monotributo, ARCA
    la rechaza. Por eso el chequeo de 'listo para facturar' avisa cuando la
    categoria esta vacia, y no solo cuando esta mal.
    """
    elegido = _que_comprobante_elige("", _cliente(2), monkeypatch)

    assert elegido == "Factura A"


def test_una_categoria_no_numerica_tambien_cae_en_ri(qt, monkeypatch):
    """Lo mismo con basura en vez de vacio: a_entero no puede leerla."""
    elegido = _que_comprobante_elige("no soy un numero", _cliente(2),
                                     monkeypatch)

    assert elegido == "Factura A"
