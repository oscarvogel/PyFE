"""Base en memoria con el catalogo minimo, compartida por los tests de stock.

Por que esta en un archivo y no en cada test
--------------------------------------------
Porque los tests de stock no pueden escribir en `sistema.db`: la base del
sandbox tiene las facturas de desarrollo, y un ajuste de inventario que se
cuele ahi deja el inventario del proyecto corrido sin forma de volver atras.
La base en memoria se arma, se siembra y se devuelve sola, y todo queda en su
lugar aunque el test falle.

Los tests de `libs/stock.py` y los de la emision arman su propia base porque
ya lo hacen y funcionan; este archivo es para los que se agreguen. Si en
alguna momento se unifican, este es el que queda.

La siembra va campo por campo porque peewee pone los defaults en Python y no
en el CREATE TABLE: una columna NOT NULL sin default hay que pasarla, y
adivinarla tira un IntegrityError que habla de una tabla de maestro y no del
stock.

Como usarlo
-----------

    from ayuda_stock import base_memoria

    def test_algo(base_memoria):
        ...
"""

import contextlib

import peewee

from modelos.Articulos import Articulo
from modelos.CabFacProv import CabFactProv
from modelos.Cabfact import Cabfact
from modelos.Cajeros import Cajero
from modelos.CentroCostos import CentroCosto
from modelos.Clientes import Cliente
from modelos.CpbteRelacionado import CpbteRel
from modelos.DetFactProv import DetFactProv
from modelos.Detfact import Detfact
from modelos.Formaspago import Formapago
from modelos.Grupos import Grupo
from modelos.Impuestos import Impuesto
from modelos.Localidades import Localidad
from modelos.MovStock import MovStock
from modelos.Proveedores import Proveedor
from modelos.Remitos import DetalleRemito, Remito
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipodoc import Tipodoc
from modelos.Tipoiva import Tipoiva
from modelos.Tiporesp import Tiporesp
from modelos.Unidades import Unidad
from modelos.CuotasPago import CuotaPago

# Los que se atan a la base. Los demas no hacen falta para el stock y no se
# crean: menos tablas y menos nombres de columnas que pueden cambiar sin que
# se note.
MODELOS = (Articulo, MovStock, Grupo, Proveedor, Tipoiva, Unidad, Impuesto,
           Cliente, Localidad, Tipodoc, Tiporesp, Formapago, CuotaPago,
           TipoComprobante, Cajero, Cabfact, Detfact, CpbteRel, Remito,
           DetalleRemito, CentroCosto, CabFactProv, DetFactProv)


def _siembra(memoria):
    """Datos de partida: dos articulos (uno controlado y uno servicio)."""
    Tipoiva.insert_many([
        {"codigo": "01", "descrip": "IVA GENERAL", "iva": 21},
        {"codigo": "02", "descrip": "10.5", "iva": 10.5},
    ]).execute()
    TipoComprobante.insert_many([
        {"codigo": 6, "nombre": "FACTURA B", "abreviatura": "B", "lado": "D",
         "exporta": 0, "ultcomp": 0, "letra": "B"},
        {"codigo": 8, "nombre": "NOTA CREDITO B", "abreviatura": "NCB",
         "lado": "H", "exporta": 0, "ultcomp": 0, "letra": "B"},
        {"codigo": 92, "nombre": "Proforma", "abreviatura": "PRO", "lado": "",
         "exporta": 0, "ultcomp": 0, "letra": "X"},
    ]).execute()
    Formapago.insert_many([{"idformapago": 1, "detalle": "EFECTIVO"}]).execute()
    Impuesto.insert_many([{"idimpuesto": 1, "detalle": "SIN PERCEPCION"}]).execute()
    Grupo.insert_many([{"idgrupo": 1, "nombre": "VARIOS", "impuesto": 1}]).execute()
    Localidad.insert_many([{"idlocalidad": 1, "nombre": "x", "provincia": "x",
                            "nacion": "ARGENTINA"}]).execute()
    Tipodoc.insert_many([{"codigo": 0, "tipo": "2", "nombre": "DNI"}]).execute()
    Tiporesp.insert_many([{"idtiporesp": 1, "nombre": "CONSUMIDOR FINAL",
                           "factura": 6, "notacredito": 8, "notadebito": 7,
                           "condicion_iva_receptor_id": 5}]).execute()
    Unidad.insert_many([{"unidad": "UN", "descripcion": "UNIDAD"}]).execute()
    Proveedor.insert_many([{"idproveedor": 1, "nombre": "SIN PROVEEDOR",
                            "tiporesp": 1, "idlocalidad": 1}]).execute()
    Cajero.insert_many([{"idcajero": 1, "nombre": "CAJERO"}]).execute()
    CentroCosto.insert_many([{"idctrocosto": 1, "nombre": "GENERAL"}]).execute()
    Cliente.insert_many([{"idcliente": 1, "nombre": "CONSUMIDOR FINAL",
                          "domicilio": "S/N", "localidad": 1, "dni": 11111111,
                          "tipodocu": 0, "tiporesp": 1, "formapago": 1,
                          "percepcion": 1}]).execute()
    Articulo.insert_many([
        {"idarticulo": 1, "nombre": "GASOLINA", "controlastock": True,
         "stockminimo": 5, "preciopub": 100, "costo": 80, "unidad": "UN",
         "grupo": 1, "provppal": 1, "tipoiva": "01", "concepto": "1"},
        # El servicio: controlastock en False. Es el que reminds que en el
        # catalogo conviven productos y cosas que no se inventan.
        {"idarticulo": 2, "nombre": "MANTENIMIENTO", "controlastock": False,
         "stockminimo": 0, "preciopub": 5000, "costo": 0, "unidad": "UN",
         "grupo": 1, "provppal": 1, "tipoiva": "01", "concepto": "2"},
    ]).execute()

    assert Articulo.select().count() == 2, "no entraron los articulos"


@contextlib.contextmanager
def base_memoria():
    """Base sqlite en memoria, sembrada, y todo vuelve a su base al final.

    Los modelos se atan a la memoria y se desatan al salir, incluso si el test
    falla: un modelo que queda apuntando a una base en memoria cerrada hace
    fallar los tests SIGUIENTES con un error de "no such table" que no
    pertenece a ninguno.
    """
    anteriores = [(modelo, modelo._meta.database) for modelo in MODELOS]

    memoria = peewee.SqliteDatabase(":memory:")
    for modelo in MODELOS:
        modelo.bind(memoria)
    memoria.connect()
    # create_tables ordena solo segun las dependencias.
    memoria.create_tables(MODELOS, safe=True)
    _siembra(memoria)

    try:
        yield memoria
    finally:
        memoria.close()
        for modelo, anterior in anteriores:
            modelo.bind(anterior)
