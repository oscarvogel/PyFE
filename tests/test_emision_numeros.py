"""Los numeros que salen de la grilla de la factura.

Que esta comprobando
--------------------
Que `float("500,00")` no reviente la emision. La grilla muestra los importes
con el formato de la app --separador de miles y coma decimal-- y el
controlador los leia con `float()` pelado: al guardar la factura salia un
`ValueError: could not convert string to float: '500,00'` y una ventana de
error que no decia que celda lo habia causado.

Cuando pasa
-----------
Al EDITAR una celda. Al cargarla con `AgregaItem` el numero va aparte del
texto (`UserRole`) y `ObtenerItem` lo devuelve crudo, asi que nunca se
parsea el texto. Pero cuando el operador teclea encima, Qt reemplaza el item
por uno nuevo que solo tiene el texto, y ahi si hay que parsear.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import pytest  # noqa: E402


@pytest.fixture
def a_numero():
    from controladores.Facturas import FacturaController
    return FacturaController._a_numero


@pytest.fixture
def qt():
    from PyQt5.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _controlador_con_una_linea():
    """Un FacturaController de verdad, con una linea de 500 y el IVA puesto.

    Va en un modulo aparte para que el test se lea: `SumaTodo` necesita el
    concepto marcado, el tipo de comprobante y los netos, y si faltan
    calcula cero sin avisar.
    """
    from controladores.Facturas import FacturaController

    class _Percepcion(object):
        porcentaje = 0

    class _Cliente(object):
        percepcion = _Percepcion()

    c = FacturaController()
    c.view.show()
    c.view.checkBoxProductos.setChecked(True)
    c.tipo_cpte = 6
    # Sin cliente, `SumaTodo` vuelve antes de sumar y todos los totales dan
    # cero: el test pasaria por el motivo equivocado.
    c.cliente = _Cliente()
    c.view.gridFactura.setRowCount(0)
    c.view.gridFactura.AgregaItem(items=[1, 1, "GASOLINA", 500, 21, 500])
    return c


@pytest.mark.parametrize("entrado,esperado", [
    (500, 500.0),                    # lo que devuelve ObtenerItem con UserRole
    (500.0, 500.0),
    ("500", 500.0),                   # como lo escribe el operador
    ("500,00", 500.0),                # como lo ve en la pantalla
    ("1.234,56", 1234.56),            # con separador de miles
    ("0", 0.0),
    ("", 0.0),                        # celda vacia
    ("  1.000  ", 1000.0),            # con espacios
])
def test_lee_como_estan_escritos_en_la_pantalla(a_numero, entrado, esperado):
    assert a_numero(entrado) == esperado


def test_un_importe_con_coma_no_revienta_la_emision(a_numero):
    """Este es el error que ve el operador: guardar y que salte la ventana."""
    with pytest.raises(ValueError) as error:
        a_numero("no soy un numero")

    # El mensaje tiene que decir QUE se rompio: un ValueError pelado de
    # `float()` deja sin saber que celda fue.
    assert "no soy un numero" in str(error.value), \
        "el error tiene que decir que valor no se pudo leer: {}".format(
            error.value)


def test_editar_una_celda_no_rompe_el_calculo(qt, monkeypatch):
    """El camino real: editar el precio de una linea y sumar."""
    from controladores import Facturas

    # El total depende de si el emisor es responsable inscripto, y eso sale
    # del sistema.ini de la maquina donde corra el test. Se fija aca: sin esto
    # el test pasa en unas instalaciones y falla en otras, y cuando falla
    # parece que el bug del parseo volvio.
    def leer_ini(*args, **k):
        if k.get("clave") == "cat_iva" and k.get("key") == "WSFEv1":
            return "1"
        return "S"

    monkeypatch.setattr(Facturas, "LeerIni", leer_ini)

    c = _controlador_con_una_linea()

    # Lo que hace Qt cuando el operador teclea encima: un item nuevo con el
    # texto y sin el numero de al lado.
    from PyQt5.QtWidgets import QTableWidgetItem

    columna = c.view.gridFactura.cabeceras.index("Unitario")
    c.view.gridFactura.setItem(0, columna, QTableWidgetItem("500,00"))

    c.SumaTodo()

    # Factura B: el precio unitario INCLUYE el IVA. De los 500 tipeados, 86,777
    # son de IVA y 413,223 de neto. Lo que importa es que la celda editada con
    # coma se leyo: antes decia `float("500,00")` y reventaba antes de llegar
    # aca, con una ventana de error que no decia que celda lo habia causado.
    assert c.view.total_subtotal == 500.0, \
        "el subtotal es la suma de las lineas, dieron {}".format(
            c.view.total_subtotal)
    assert c.view.total_iva == 86.777, \
        "el IVA incluido en los 500 es 86,777, dieron {}".format(
            c.view.total_iva)
    assert c.view.total_final == 500.0, \
        "el total tiene que volver a los 500 que se tipearon, dieron {}".format(
            c.view.total_final)
    c.view.close()
