"""El seed de stock tiene que dejar el stock que declara.

Que esta comprobando
--------------------
Que `tools/sembrar_stock.py` produce el estado final que dice en su catalogo,
y sobre todo que la regla del remito siga valiendo con los datos puestos.

Por que el seed necesita tests
------------------------------
El seed existe para probar el modulo a mano, y un seed que produces datos
plausibles pero incorrectos es peor que no tener seed: el operador los usa para
creer que algo anda bien. Si el seed dice "las pilas quedan en 5" y en realidad
quedan en -5 porque el remito se cobro dos veces, la prueba manual pasa y
esconde justo el bug mas caro del modulo.

Como se prueba
--------------
Con la base en memoria de `ayuda_stock`, no con el sandbox: el seed no tiene
que dejar rastro en ningun lado para estar probado. Y se corre el `sembrar()`
real, el mismo que corre el script, en vez de una copia de la logica.

Lo que NO comprueba
-------------------
Que los datos sean lindos. Nadie necesita un tornillo de verdad.
"""

import contextlib
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(RAIZ, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(RAIZ, "tools"))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)


@contextlib.contextmanager
def _base_limpia():
    """La base en memoria, sin los dos articulos de la siembra de test.

    GASOLINA y MANTENIMIENTO quedan de `ayuda_stock` y no son del catalogo del
    seed. Si se dejaran, el `verificar()` los seguiria mostrando y el ruido
    taparia el producto que de verdad esta roto.
    """
    from ayuda_stock import base_memoria
    from modelos.Articulos import Articulo
    from modelos.MovStock import MovStock

    with base_memoria():
        Articulo.delete().execute()
        MovStock.delete().execute()
        yield


def test_el_seed_deja_el_stock_que_declara():
    """El mismo chequeo que corre el script, como test.

    El script ya verifica y sale con codigo 1 si algo no da. Acá se corre esa
    misma funcion y se mira la lista de diferencias, para que un numero mal
    quede registrado como fallo de test y no solo como texto en consola.
    """
    import sembrar_stock

    with _base_limpia():
        sembrar_stock.sembrar()

        diferencias = sembrar_stock.verificar(silencioso=True)

        assert diferencias == [], \
            "el seed no dejo el stock que declara:\n  " + "\n  ".join(
                diferencias)


def test_el_remito_se_cobra_una_sola_vez():
    """La regla mas cara del modulo, guardada en los datos.

    El remito de las pilas descuenta 10. La factura de ese remito lleva
    `idremito` puesto, y por eso NO tiene que descontar otra vez: esa
    mercaderia ya salio del deposito.

    Si la regla se rompe, PILA-AA queda en -5 en vez de 5, y no se ve en
    ninguna pantalla: el total de la factura esta bien, el comprobante esta
    bien, y el stock queda mal. Por eso el numero va fijo en el catalogo del
    seed.
    """
    import sembrar_stock
    from libs import stock
    from modelos.Articulos import Articulo
    from modelos.MovStock import MovStock

    with _base_limpia():
        sembrar_stock.sembrar()

        # `get_by_id` es para claves primarias. Buscar por codigo de barras es
        # un `get`, y `get_by_id` con una condicion explota adentro de peewee.
        pilas = Articulo.get(Articulo.codbarra == "PILA-AA")

        assert stock.stock_de(pilas.idarticulo) == 5, \
            "las pilas tienen que quedar en 5 (30 de conteo, menos 10 del " \
            "remito, menos 15 de venta). Quedaron en {}. Si esto es -5, el " \
            "remito se esta cobrando dos veces.".format(
                stock.stock_de(pilas.idarticulo))

        # Y que no exista ningun movimiento de VENTA colgado de la factura del
        # remito, que es como se ve el doble descuento en la tabla.
        del_remito = (MovStock
                      .select()
                      .where(MovStock.idarticulo == pilas.idarticulo)
                      .where(MovStock.origen == stock.ORIGEN_REMITO)
                      .count())
        assert del_remito == 1, \
            "tiene que haber un solo movimiento de remito, hay {}".format(
                del_remito)

        factura_del_remito = (MovStock
                              .select()
                              .where(MovStock.idarticulo == pilas.idarticulo)
                              .where(MovStock.origen == stock.ORIGEN_VENTA)
                              .where(MovStock.idremito.is_null(True))
                              .count())
        assert factura_del_remito == 1, \
            "las pilas tienen una sola venta propia (la de la venta 47), no " \
            "una mas de la factura del remito. Hay {} sin idremito.".format(
                factura_del_remito)


def test_correr_el_seed_dos_veces_no_duplica_los_maestros():
    """El seed tiene que poder volver a correrse sin ensuciar.

    El cliente y el proveedor se buscan por nombre antes de crearse. Sin eso,
    la segunda corrida dejaria dos "CORRALON LA BAHIA" y las facturas de
    prueba quedarian repartidas entre los dos.
    """
    import sembrar_stock
    from modelos.Clientes import Cliente
    from modelos.Proveedores import Proveedor

    with _base_limpia():
        sembrar_stock.sembrar()
        clientes_primera = Cliente.select().count()
        proveedores_primera = Proveedor.select().count()

        # Los articulos se borran para no chocar con los de la primera corrida,
        # que es lo que hace `--rehacer`.
        sembrar_stock._deshacer()

        sembrar_stock.sembrar()

        # Se comparan los numeros de antes y despues, y no un numero fijo:
        # `ayuda_stock` ya deja un proveedor ("SIN PROVEEDOR"), asi que la
        # cantidad absoluta depende de la siembra de los tests.
        assert Cliente.select().count() == clientes_primera, \
            "la segunda corrida duplico clientes: {} eran {} antes".format(
                Cliente.select().count(), clientes_primera)
        assert Proveedor.select().count() == proveedores_primera, \
            "la segunda corrida duplico proveedores: {} eran {} antes".format(
                Proveedor.select().count(), proveedores_primera)


def test_la_semilla_cubre_todos_los_estados_de_la_pantalla():
    """Si el seed no tiene los cinco estados, probar a mano no sirve de mucho.

    La columna "Estado" de la pantalla tiene cinco valores y son cinco
    caminos distintos del operador: OK (nada que hacer), Falta (hay que
    comprar), Sin stock (se agoto), Negativo (algo quedo mal antes) y Sin
    controlar (falta marcarlo). Un seed con tres de los cinco deja al que
    prueba sin caso para dos.
    """
    import sembrar_stock
    from controladores.Stock import estado_de
    from libs import stock
    from modelos.Articulos import Articulo

    with _base_limpia():
        sembrar_stock.sembrar()

        estados = set()
        for fila in sembrar_stock.CATALOGO:
            articulo = Articulo.get(Articulo.codbarra == fila["codbarra"])
            estados.add(estado_de(articulo,
                                 stock.stock_de(articulo.idarticulo)))

        esperados = {"OK", "Falta", "Sin stock", "Negativo", "Sin controlar"}
        assert estados == esperados, \
            "el catalogo del seed no cubre todos los estados. Faltan: {}".format(
                esperados - estados)


def test_el_seed_no_escribe_en_la_base_de_trabajo():
    """La proteccion que hace que el seed se pueda correr sin miedo.

    La base de trabajo es la del cliente: ventas, compras, el historial entero.
    Ya una vez una migracion de prueba corrio ahi y perdio 37 ventas. Este test
    comprueba que el seed se niega, y no que "no deberia" negarse.
    """
    import pytest

    import sembrar_stock

    with pytest.raises(SystemExit) as excepcion:
        sembrar_stock.verificar_destino(sembrar_stock.ORIGEN)

    assert "base de trabajo" in str(excepcion.value)

    # Y tambien la carpeta de datos del usuario, que es donde cae la app
    # instalada.
    usuario = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Asiento")
    if os.path.isdir(usuario):
        with pytest.raises(SystemExit):
            sembrar_stock.verificar_destino(usuario)

    # Y que una carpeta cualquiera si se acepte.
    assert sembrar_stock.verificar_destino(
        os.path.join(RAIZ, "_sandbox_prueba"))