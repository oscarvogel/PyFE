"""MySQL tiene reglas que sqlite no, y ahi es donde aparecio el bug.

Que esta comprobando
--------------------
Que la lista de modelos de `MigrarVersion0` sirva para armar una base MySQL
vacia. En sqlite da lo mismo con cualquier lista, porque las claves foraneas
no se aplican al crear la tabla; en MySQL, no.

El bug que caza
---------------
`Cabfact` tiene `idremito`, que apunta a `remito`. `remito` la crea
MigrarVersion7, que corre despues. MySQL no crea una tabla que apunte a otra
que todavia no existe, asi que `create_tables` se cortaba al llegar a
`cabfact`, MigrarVersion0 se come el error con un `except` mudo, y la base
quedaba con nueve tablas de veintitres sin version sellada: una instalacion
MySQL desde cero no arrancaba.

No se prueba MySQL aca. Se prueba que la lista tenga lo que MySQL necesita, que
es lo unico que se puede comprobar sin un servidor. La corrida de verdad esta
en tools/probar_stock_mysql.py.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


def _modelos():
    from controladores.MigracionBaseDatos import MigracionBaseDatos
    return MigracionBaseDatos.MODELOS_INICIALES


def test_toda_la_tablas_del_schema_estan_en_la_lista():
    """Si a una tabla le falta estar en la lista, no existe en una base nueva."""
    from modelos.MovStock import MovStock
    from modelos.Articulos import Articulo
    from modelos.CabFacProv import CabFactProv
    from modelos.Cabfact import Cabfact
    from modelos.DetFactProv import DetFactProv
    from modelos.Detfact import Detfact
    from modelos.Remitos import DetalleRemito, Remito

    nombres = {m._meta.table_name for m in _modelos()}
    for modelo in (Articulo, Cabfact, Detfact, Remito, DetalleRemito,
                   CabFactProv, DetFactProv, MovStock):
        if modelo is MovStock:
            # MovStock la crea MigrarVersion9, no MigrarVersion0. Se revisa
            # aparte, mas abajo.
            continue
        assert modelo._meta.table_name in nombres, \
            "{} ({}) no esta en MODELOS_INICIALES: una base nueva no tendria " \
            "esa tabla".format(modelo.__name__, modelo._meta.table_name)


def test_las_tablas_referenciadas_tambien_estan_en_la_lista():
    """peewee ordena la lista por dependencias, pero no inventa lo que falta.

    Este es el bug que caza, y no es de orden sino de presencia: `cabfact`
    tiene `idremito` y `remito` no estaba en la lista. peewee no tiene con que
    ordenar esa referencia, asi que intentaba crear `cabfact` apuntando a una
    tabla que nadie iba a crear, MySQL lo rechazaba, `create_tables` se cortaba
    y MigrarVersion0 se come el error con un `except` mudo.

    El orden de la lista NO importa: peewee lo resuelve solo. Esta asercion
    se escribio primero diciendo que si, y MySQL la desmintio: la lista tiene
    `grupos` antes que `impuestos` y las catorce pruebas pasan igual.
    """
    nombres = {m._meta.table_name for m in _modelos()}

    for tabla, referencia in (("cabfact", "remito"),
                              ("detalleremito", "remito"),
                              ("detfact", "cabfact"),
                              ("detfact", "articulos"),
                              ("articulo", "grupos"),
                              ("grupos", "impuestos"),
                              ("remito", "clientes"),
                              ("clientes", "tiporesp"),
                              ("pdetalle", "pcabecera")):
        if tabla not in nombres:
            continue
        assert referencia in nombres, \
            "{} esta en la lista y apunta a {}, que no esta: MySQL no crea " \
            "una tabla que referencie a otra que no se va a crear, y el " \
            "create_tables se corta ahi sin decir nada".format(tabla, referencia)


def test_movstock_no_esta_en_la_lista_inicial():
    """MovStock la crea MigrarVersion9, y tiene que seguir asi.

    Si alguien la agrega a la lista inicial, la base nueva la tiene desde el
    principio y la migracion 9 no tiene que hacer nada. No rompe, pero deja de
    probarse sola la migracion en una instalacion limpia.
    """
    from modelos.MovStock import MovStock

    assert MovStock._meta.table_name not in {m._meta.table_name for m in _modelos()}, \
        "movstock la crea MigrarVersion9; si esta en la lista inicial, una " \
        "instalacion nueva no ejercita esa migracion"


def test_la_migracion_chequea_que_la_clave_foranea_no_este():
    """Agregar una clave que ya existe rompe la migracion en MySQL.

    En una base nueva, MigrarVersion0 crea las claves foraneas al crear cada
    tabla, y MigrarVersion1 despues intenta volver a ponerlas. MySQL responde
    'Duplicate foreign key constraint name' y la version no se sella.
    """
    import inspect

    from controladores.MigracionBaseDatos import MigracionBaseDatos

    fuente = inspect.getsource(MigracionBaseDatos._clave_foranea)
    assert "_tiene_clave_foranea" in fuente, \
        "_clave_foranea tiene que consultar si la clave ya existe antes de " \
        "agregarla: MySQL no admite duplicadas"
