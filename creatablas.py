# coding=utf-8
import sys

from modelos.Clientes import Cliente
from modelos.Formaspago import Formapago
from modelos.Impuestos import Impuesto
from modelos.Localidades import Localidad
from modelos.Tipodoc import Tipodoc
from modelos.Tiporesp import Tiporesp

if 'drop' in sys.argv:
    Cliente().drop_table()
    Impuesto().drop_table()
    Formapago().drop_table()
    Tiporesp().drop_table()
    Tipodoc().drop_table()
    Localidad().drop_table()

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

Impuesto().create_table()
impuestos = [
    {'idimpuesto':1, 'detalle':'SIN PERCEPCION'},
    {'idimpuesto':2, 'detalle':'DGR', 'porcentaje':3.31}
]
Impuesto().insert(impuestos).execute()

Cliente().create_table()
cliente = [
    {'idcliente':1, 'nombre':'CONSUMIDOR FINAL', 'domicilio':'S/NOMBRE', 'localidad':1, 'dni':11111111,
     'tiporesp':3, 'tipodocu':0, 'formapago':1, 'percepcion':1}
]
Cliente().insert(cliente).execute()