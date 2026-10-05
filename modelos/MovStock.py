# coding=utf-8
"""Movimientos de stock.

El stock NO es un numero guardado en el articulo: es la suma de esta tabla.
No hay columna 'stock' en 'articulos' a proposito, y la razon esta en el
docstring de esta clase.

Por que no un numero guardado
-----------------------------
Porque habria dos fuentes de verdad. El numero guardado se actualiza en cada
venta, cada remito, cada compra y cada ajuste, y el dia que una de esas
actualizaciones falla (un error a mitad, una PC que se apaga, un usuario que
anula a mano) el numero queda desfasado y no hay forma de saber cual de las
dos miente. Con suma no hay nada que mantener: el stock es lo que dice la
tabla, siempre.

Por que no se deriva de 'detfact'
--------------------------------
Porque 'detfact' no es la historia del stock. ImportacionAFIP (vistas/ y
controladores/ImportacionAFIP.py) escribe ahi un renglon por comprobante
importado, siempre con idarticulo=1 y cantidad=1, para que los libros de IVA
cuadren. Si el stock fuera un SUM sobre 'detfact', cada factura de un
comprobante emitido en otro sistema bajaria un unidad de un articulo que no
existe.

Ademas, una venta de 2018 no es un movimiento de stock de hoy: son ocho anos
de historia que ya paso. El stock arranca en cero y lo define el inventario
inicial que carga el operador.

Reglas de esta tabla
--------------------
1. Un movimiento NO se edita ni se borra. Nunca. Para corregir uno se escribe
   el movimiento contrario y se lo enlaza con 'anula'. Asi el historico cuenta
   que paso, y no solo como quedo. Lo unico que se le escribe a un movimiento
   ya creado es ese vinculo de anulacion, y nada mas: ni la cantidad, ni el
   articulo, ni el comprobante.
2. 'cantidad' va CON signo: positiva entra, negativa sale. El 'tipo' dice
   como, y es informativo; el signo es el que suma.
3. 'origen' dice que flujo lo produjo (VENTA, REMITO, COMPRA, INICIAL,
   AJUSTE), y las columnas de comprobante dicen cual. Sin origen no se puede
   responder "por que a este articulo le faltan 3".
"""

from datetime import date

from peewee import AutoField, CharField, DateField, DecimalField, ForeignKeyField, TextField

from modelos.Articulos import Articulo
from modelos.CabFacProv import CabFactProv
from modelos.Cabfact import Cabfact
from modelos.ModeloBase import ModeloBase
from modelos.Remitos import Remito


# Valores de 'tipo'. Informativos: el signo de 'cantidad' es el que manda.
TIPO_ENTRADA = 'E'
TIPO_SALIDA = 'S'
TIPO_AJUSTE = 'A'

# Valores de 'origen'. Este es el que dice de donde salio el movimiento, y
# es por donde se filtra cuando se quiere entender una diferencia de stock.
ORIGEN_INICIAL = 'INICIAL'
ORIGEN_VENTA = 'VENTA'
ORIGEN_REMITO = 'REMITO'
ORIGEN_COMPRA = 'COMPRA'
ORIGEN_AJUSTE = 'AJUSTE'

ORIGENES = (
    ORIGEN_INICIAL,
    ORIGEN_VENTA,
    ORIGEN_REMITO,
    ORIGEN_COMPRA,
    ORIGEN_AJUSTE,
)


class MovStock(ModeloBase):

    idmovstock = AutoField()
    fecha = DateField(default=date.today)

    # Con indice, no por prolijidad: todas las consultas de stock son un SUM
    # agrupado por articulo, y sin indice cada una recorre la tabla entera.
    idarticulo = ForeignKeyField(Articulo, backref='movstock', column_name='idarticulo')

    # Con signo: positiva entra, negativa sale. Decimal de 4 decimales como
    # todo lo que se vende, porque los artigos se pesan.
    cantidad = DecimalField(max_digits=12, decimal_places=4)

    tipo = CharField(max_length=1, default=TIPO_AJUSTE)
    origen = CharField(max_length=20, default=ORIGEN_AJUSTE)

    # De cual comprobante salio. A lo sumo uno de los tres: un movimiento es
    # o de una venta o de un remito o de una compra, nunca de dos.
    idcabfact = ForeignKeyField(Cabfact, backref='movstock_venta',
                                column_name='idcabfact', null=True)
    idremito = ForeignKeyField(Remito, backref='movstock_remito',
                               column_name='idremito', null=True)
    idpcabecera = ForeignKeyField(CabFactProv, backref='movstock_compra',
                                  column_name='idpcabecera', null=True)

    # El movimiento contrario que anula a este, si alguno. Es autorreferencia
    # y se deja en null normalmente.
    anula = ForeignKeyField('self', backref='anula_a', column_name='anula', null=True)

    observacion = TextField(default='')

    class Meta:
        table_name = 'movstock'

    @classmethod
    def en_negativo(cls, cantidad):
        return cantidad < 0

    def es_anulacion(self):
        return self.anula is not None
