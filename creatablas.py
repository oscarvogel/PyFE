# coding=utf-8
import sys

from modelos.Articulos import Articulo
from modelos.CabFacProv import CabFactProv
from modelos.Cabfact import Cabfact
from modelos.Cajeros import Cajero
from modelos.CentroCostos import CentroCosto
from modelos.Clientes import Cliente
from modelos.CpbteRelacionado import CpbteRel
from modelos.Ctacte import CtaCte
from modelos.DetFactProv import DetFactProv
from modelos.Detfact import Detfact
from modelos.Emailcliente import EmailCliente
from modelos.Formaspago import Formapago
from modelos.Grupos import Grupo
from modelos.Impuestos import Impuesto
from modelos.Localidades import Localidad
from modelos.Proveedores import Proveedor
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipodoc import Tipodoc
from modelos.Tipoiva import Tipoiva
from modelos.Tiporesp import Tiporesp
from modelos.Unidades import Unidad

if 'drop' in sys.argv:
    CpbteRel().drop_table()
    CtaCte().drop_table()
    Detfact().drop_table()
    Cabfact().drop_table()
    CabFactProv().drop_table()
    DetFactProv().drop_table()
    EmailCliente().drop_table()
    Cliente().drop_table()
    Articulo().drop_table()
    Proveedor().drop_table()
    Unidad().drop_table()
    Grupo().drop_table()
    Impuesto().drop_table()
    Formapago().drop_table()
    Tiporesp().drop_table()
    Tipodoc().drop_table()
    Localidad().drop_table()
    Tipoiva().drop_table()
    Cajero().drop_table()
    TipoComprobante().drop_table()
    CentroCosto().drop_table()

Grupo().create_table()
grupo = [
    {'idgrupo':1, 'nombre':'VARIOS'}
]
Grupo().insert(grupo).execute()

Unidad().create_table()
# unidad = [
#     {'unidad':'UN', 'descripcion':'UNIDAD'}
# ]
# Unidad().insert(unidad).execute()

Formapago().create_table()
formapago = [
    {'detalle': 'EFECTIVO'},
    {'detalle': 'CUENTA CORRIENTE', 'recargo': 10, 'ctacte':b'\01'},
    ]
Formapago().insert(formapago).execute()

tiporesp = [
    {'idtiporesp':1,'nombre':'MONOTRIBUTO',	'tipoiva':'M','obligacuit':b'\01','factura':82, 'notacredito':13,'notadebito':12},
    {'idtiporesp':2,'nombre':'RESP. INSCRIPTO','discrimina':b'\01','tipoiva':'I','obligacuit':b'\01','factura':81, 'notacredito':13,'notadebito':12},
    {'idtiporesp':3,'nombre':'CONSUMIDOR FINAL','tipoiva':'F','factura':82, 'notacredito':13,'notadebito':12},
    {'idtiporesp':4,'nombre':'EXENTO','tipoiva':'X','obligacuit':b'\01','factura':82, 'notacredito':13,'notadebito':12},
]
Tiporesp().create_table()
Tiporesp().insert(tiporesp).execute()

Tipodoc().create_table()
tipodoc = [
    {'codigo':0,'tipo':2,'nombre':'D.N.I.'},
    {'codigo':1,'tipo':4,'nombre':'CEDULA DE IDENTIDAD'},
    {'codigo':2,'tipo':0,'nombre':'LIBRETA ENROLAMIENTO'},
    {'codigo':3,'tipo':1,'nombre':'LIBRETA CIVICA'},
    {'codigo':4,'tipo':3,'nombre':'PASAPORTE'},
]
Tipodoc().insert(tipodoc).execute()

Localidad().create_table()
localidades = [
    {'idlocalidad':'1', 'nombre':'GARUHAPE', 'provincia':'MISIONES', 'nacion':'ARGENTINA'},
    {'idlocalidad':'2', 'nombre':'PUERTO RICO', 'provincia':'MISIONES', 'nacion':'ARGENTINA'},
    {'idlocalidad':'3', 'nombre':'CAPIOVY', 'provincia':'MISIONES', 'nacion':'ARGENTINA'},
]
Localidad().insert(localidades).execute()

TipoComprobante().create_table()
tipocomp = [
    {'codigo':0,'nombre':'EFECTIVO','abreviatura':'EFE', 'exporta':b'\00'},
    {'codigo':1,'nombre':'FACTURA A','abreviatura':'A', 'exporta':b'\01','letra':'A','lado':'D'},
    {'codigo':2,'nombre':'NOTA DEBITO A','abreviatura':'NDA', 'exporta':b'\01','letra':'A','lado':'D'},
    {'codigo':3,'nombre':'NOTA CREDITO A','abreviatura':'NCA', 'exporta':b'\01','letra':'A','lado':'H'},
    {'codigo': 6, 'nombre': 'FACTURA B', 'abreviatura': 'B', 'exporta': b'\01', 'letra': 'B', 'lado': 'D'},
    {'codigo': 7, 'nombre': 'NOTA DEBITO B', 'abreviatura': 'NCB', 'exporta': b'\01', 'letra': 'B', 'lado': 'D'},
    {'codigo': 8, 'nombre': 'NOTA CREDITO B', 'abreviatura': 'NCB', 'exporta': b'\01', 'letra': 'B', 'lado': 'H'},
    {'codigo': 11, 'nombre': 'FACTURA C', 'abreviatura': 'C', 'exporta': b'\01', 'letra': 'C', 'lado': 'D'},
    {'codigo': 12, 'nombre': 'NOTA DEBITO C', 'abreviatura': 'NCC', 'exporta': b'\01', 'letra': 'C', 'lado': 'D'},
    {'codigo': 13, 'nombre': 'NOTA CREDITO C', 'abreviatura': 'NCC', 'exporta': b'\01', 'letra': 'C', 'lado': 'H'},
    {'codigo': 81, 'nombre': 'TIQUE FACTURA A', 'abreviatura': '', 'exporta': b'\01', 'letra': 'A', 'lado': 'D'},
    {'codigo': 82, 'nombre': 'TIQUE FACTURA B', 'abreviatura': '', 'exporta': b'\01', 'letra': 'B', 'lado': 'D'},
    {'codigo': 83, 'nombre': 'TIQUE', 'abreviatura': '', 'exporta': b'\01', 'letra': 'B', 'lado': 'D'},
    {'codigo': 42, 'nombre': 'RECIBO X', 'abreviatura': 'RCX', 'exporta': b'\00', 'letra': ' ', 'lado': 'H'},
]
TipoComprobante().insert(tipocomp).execute()

Impuesto().create_table()
impuestos = [
    {'idimpuesto':1, 'detalle':'SIN PERCEPCION'},
    {'idimpuesto':2, 'detalle':'DGR', 'porcentaje':3.31}
]
Impuesto().insert(impuestos).execute()

Proveedor().create_table()
proveedor = [
    {'idproveedor':1, 'nombre':'SIN PROVEEDOR','domicilio':'','telefono':'','cuit':'','tiporesp':1,'idLocalidad':1}
]
Proveedor().insert(proveedor).execute()

Cliente().create_table()
cliente = [
    {'idcliente':1, 'nombre':'CONSUMIDOR FINAL', 'domicilio':'S/NOMBRE', 'localidad':1, 'dni':11111111,
     'tiporesp':3, 'tipodocu':0, 'formapago':1, 'percepcion':1}
]
Cliente().insert(cliente).execute()
Tipoiva().create_table()
tipoiva = [
    {'codigo':'01','descrip':'IVA GENERAL','iva':21},
    {'codigo':'02','descrip':'DECRETO 493/01','iva':10.5},
    {'codigo':'50','descrip':'CONCEP. NO GRAVADOS','iva':0}
]
Tipoiva().insert(tipoiva).execute()

EmailCliente().create_table()
Cajero().create_table()
cajero = [
    {'idcajero':1, 'nombre':'CAJERO'}
]
Cajero().insert(cajero).execute()

Articulo.create_table()

Cabfact().create_table()
Detfact().create_table()
CtaCte().create_table()
CpbteRel().create_table()
CentroCosto().create_table()
CabFactProv().create_table()
DetFactProv().create_table()