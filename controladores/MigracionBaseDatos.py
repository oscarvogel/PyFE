# coding=utf-8
import csv
import logging
import sys
import traceback

import pymysql
from playhouse.migrate import MySQLMigrator, migrate, IntegerField, CharField, DecimalField

from controladores.ControladorBase import ControladorBase
from libs.Utiles import inicializar_y_capturar_excepciones, desencriptar, LeerIni
from modelos.Articulos import Articulo
from modelos.CabFacProv import CabFactProv
from modelos.Cabfact import Cabfact
from modelos.Cajeros import Cajero
from modelos.CategoriasMonotributo import CategoriaMono
from modelos.CentroCostos import CentroCosto
from modelos.Clientes import Cliente
from modelos.CorreosEnviados import CorreoEnviado
from modelos.CpbteRelacionado import CpbteRel
from modelos.Ctacte import CtaCte
from modelos.DetFactProv import DetFactProv
from modelos.Detfact import Detfact
from modelos.Emailcliente import EmailCliente
from modelos.Formaspago import Formapago
from modelos.Grupos import Grupo
from modelos.Impuestos import Impuesto
from modelos.Localidades import Localidad
from modelos.ModeloBase import db
from modelos.ParametrosSistema import ParamSist
from modelos.PercepcionesDGR import PercepDGR
from modelos.Proveedores import Proveedor
from modelos.Provincias import Provincia
from modelos.Tipocomprobantes import TipoComprobante
from modelos.Tipodoc import Tipodoc
from modelos.Tipoiva import Tipoiva
from modelos.Tiporesp import Tiporesp
from modelos.Unidades import Unidad


class MigracionBaseDatos(ControladorBase):

    migraciones = []
    error = False

    def __init__(self):
        super().__init__()
        self.conectarWidgets()

    @inicializar_y_capturar_excepciones
    def Migrar(self, *args, **kwargs):
        database = db
        self.migraciones = []
        self.migrator = MySQLMigrator(database)

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) <= 0:
            self.MigrarVersion0()
            self.InsertaDatosBasicos()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 1:
            self.MigrarVersion1()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 2:
            self.MigrarVersion2()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 3:
            self.MigrarVersion3()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 4:
            self.MigrarVersion4()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 5:
            self.MigrarVersion5()

        self.RealizaMigraciones()

        ParamSist.GuardarParametro("VERSION_DB", "5")

    def MigrarVersion1(self):
        migrator = self.migrator
        colentero = IntegerField(default=1)
        self.migraciones.append(migrator.add_column('grupos', 'impuesto', colentero))
        self.migraciones.append(migrator.add_foreign_key_constraint('grupos', 'impuesto', 'impuestos', 'idimpuesto',
                                            on_delete=None, on_update='CASCADE'))

    def MigrarVersion2(self):
        migrator = self.migrator
        self.migraciones.append(migrator.alter_column_type(
            'clientes', 'nombre', CharField(max_length=100, default='')
        ))
        self.migraciones.append(migrator.alter_column_type(
            'clientes', 'domicilio', CharField(max_length=100, default='')
        ))
        self.migraciones.append(migrator.alter_column_type(
            'clientes', 'telefono', CharField(max_length=100, default='')
        ))
        self.migraciones.append(migrator.alter_column_type(
            'cabfact', 'nombre', CharField(max_length=100, default='')
        ))
        self.migraciones.append(migrator.alter_column_type(
            'cabfact', 'domicilio', CharField(max_length=100, default='')
        ))

    def RealizaMigraciones(self):
        for m in self.migraciones:
            try:
                migrate(m)
            except Exception as e:
                ex = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
                self.Traceback = ''.join(ex)
                logging.debug(self.Traceback)
                print(self.Traceback)
                self.error = True

    def MigrarVersion0(self):

        try:
            db.create_tables([Tipodoc, Tipoiva, Tiporesp, Unidad, CentroCosto, Grupo, Impuesto, Localidad, Provincia,
                              TipoComprobante, Articulo, Formapago, Cliente, Cajero, Cabfact, Detfact, CpbteRel,
                              Proveedor, CabFactProv, DetFactProv, PercepDGR, CtaCte, EmailCliente])
        except:
            logging.error("Error:", sys.exc_info()[0])

    def InsertaDatosBasicos(self):
        self.cargar_csv(
            archivo='data/tipodoc.csv',
            modelo=Tipodoc,
            campos=[Tipodoc.codigo, Tipodoc.tipo, Tipodoc.nombre]
        )
        self.cargar_csv(
            archivo='data/provincias.csv',
            campos=[Provincia.codjur, Provincia.nombre],
            modelo=Provincia
        )
        self.cargar_csv(
            archivo='data/tipocomprobante.csv',
            campos=[TipoComprobante.codigo, TipoComprobante.nombre, TipoComprobante.abreviatura,
                    TipoComprobante.lado, TipoComprobante.exporta, TipoComprobante.ultcomp, TipoComprobante.letra],
            modelo=TipoComprobante
        )
        self.cargar_csv(
            archivo='data/tipoiva.csv',
            campos=[Tipoiva.codigo, Tipoiva.descrip, Tipoiva.iva],
            modelo=Tipoiva
        )
        self.cargar_csv(
            archivo='data/tiporesp.csv',
            campos=[Tiporesp.idtiporesp, Tiporesp.nombre, Tiporesp.discrimina, Tiporesp.tipoiva,
                    Tiporesp.obligacuit, Tiporesp.factura, Tiporesp.notacredito, Tiporesp.notadebito,
                    Tiporesp.tipoivaepson],
            modelo=Tiporesp
        )
        self.cargar_csv(
            archivo='data/unidad.csv',
            campos=[Unidad.unidad, Unidad.descripcion],
            modelo=Unidad
        )
        self.cargar_csv(
            archivo='data/centrocostos.csv',
            campos=[CentroCosto.idctrocosto, CentroCosto.nombre],
            modelo=CentroCosto
        )
        self.cargar_csv(
            archivo='data/impuestos.csv',
            campos=[Impuesto.idimpuesto, Impuesto.detalle, Impuesto.porcentaje, Impuesto.minimo],
            modelo=Impuesto
        )
        self.cargar_csv(
            archivo='data/grupos.csv',
            campos=[Grupo.idgrupo, Grupo.nombre, Grupo.impuesto],
            modelo=Grupo
        )
        self.cargar_csv(
            archivo='data/localidades.csv',
            campos=[Localidad.idlocalidad, Localidad.nombre, Localidad.provincia, Localidad.nacion],
            modelo=Localidad
        )
        self.cargar_csv(
            archivo='data/formapago.csv',
            campos=[Formapago.idformapago, Formapago.detalle, Formapago.ctacte, Formapago.descuento,
                    Formapago.recargo, Formapago.mensual, Formapago.tarjeta],
            modelo=Formapago
        )
        self.cargar_csv(
            archivo='data/clientes.csv',
            campos=[Cliente.idcliente, Cliente.nombre, Cliente.domicilio, Cliente.telefono, Cliente.localidad,
                    Cliente.cuit, Cliente.dni, Cliente.tipodocu, Cliente.tiporesp, Cliente.percepcion],
            modelo=Cliente
        )
        self.cargar_csv(
            archivo='data/proveedores.csv',
            campos=[
                Proveedor.idproveedor, Proveedor.nombre, Proveedor.domicilio,
                Proveedor.telefono, Proveedor.cuit, Proveedor.tiporesp, Proveedor.idlocalidad
            ],
            modelo=Proveedor
        )
        self.cargar_csv(
            archivo='data/articulos.csv',
            campos=[Articulo.idarticulo, Articulo.nombre, Articulo.nombreticket, Articulo.unidad,
                    Articulo.grupo, Articulo.costo, Articulo.provppal, Articulo.tipoiva, Articulo.modificaprecios,
                    Articulo.preciopub, Articulo.concepto, Articulo.codbarra],
            modelo=Articulo
        )
        self.cargar_csv(
            archivo='data/cajeros.csv',
            campos=[Cajero.idcajero, Cajero.nombre, Cajero.telefono, Cajero.activo],
            modelo=Cajero
        )

    def cargar_csv(self, archivo='', campos=None, modelo=None):
        with open(archivo) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            datos = []
            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                else:
                    datos.append(tuple([x for x in row]))
                    line_count += 1
            try:
                modelo.insert_many(datos, fields=campos).execute()
            except:
                logging.error("Error:", sys.exc_info()[0])

    def MigrarVersion3(self):
        correos = CorreoEnviado()
        try:
            correos.create_table()
        except:
            pass

    def MigrarVersion4(self):
        categorias = CategoriaMono()
        try:
            categorias.create_table()
        except:
            pass

    def MigrarVersion5(self):
        migrator = self.migrator
        coldecimal = DecimalField(default=0, max_digits=12, decimal_places=2)
        self.migraciones.append(migrator.add_column('categoriamono', 'ing_brutos', coldecimal))