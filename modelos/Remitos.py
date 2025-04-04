from email.policy import default
import peewee
from modelos.ModeloBase import ModeloBase
from modelos.Articulos import Articulo
from modelos.Clientes import Cliente
from modelos.Formaspago import Formapago
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipoiva import Tipoiva


class Remito(ModeloBase):
    
    idremito = peewee.AutoField(db_column='idremito')
    cliente = peewee.ForeignKeyField(Cliente)
    fecha = peewee.DateField(default=peewee.fn.now())
    ptovta = peewee.IntegerField(default=1)
    numero = peewee.IntegerField(default=0)
    forma_pago = peewee.ForeignKeyField(Formapago, default=1)
    tipo_comprobante = peewee.ForeignKeyField(TipoComprobante, default=92)
    estado = peewee.CharField(max_length=1)
    observaciones = peewee.TextField()
    
    class Meta:
        table_name = 'remito'
    
    @property
    def total(self):
        return DetalleRemito.select(peewee.fn.Sum(DetalleRemito.cantidad * DetalleRemito.precio)).where(DetalleRemito.remito == self).scalar() or 0

class DetalleRemito(ModeloBase):
    
    iddetalleremito = peewee.AutoField(db_column='iddetalleremito')
    remito = peewee.ForeignKeyField(Remito)
    producto = peewee.ForeignKeyField(Articulo)
    detalle = peewee.TextField(default='')
    cantidad = peewee.DecimalField(decimal_places=2, default=0)
    precio = peewee.DecimalField(decimal_places=2, default=0)
    tipo_iva = peewee.ForeignKeyField(Tipoiva, default=1)
    
    class Meta:
        table_name = 'detalleremito'    