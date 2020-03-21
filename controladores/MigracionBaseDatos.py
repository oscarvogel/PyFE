# coding=utf-8
import logging
import sys
import traceback

from playhouse.migrate import MySQLMigrator, migrate, IntegerField, CharField, TextField

from controladores.ControladorBase import ControladorBase
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.ModeloBase import db
from modelos.ParametrosSistema import ParamSist


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

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 1:
            self.MigrarVersion1()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 2:
            self.MigrarVersion2()

        self.RealizaMigraciones()

        ParamSist.GuardarParametro("VERSION_DB", "2")

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

