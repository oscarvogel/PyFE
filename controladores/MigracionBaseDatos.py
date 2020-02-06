# coding=utf-8
import logging
import sys
import traceback

from playhouse.migrate import MySQLMigrator, migrate, IntegerField

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


        self.RealizaMigraciones()

        if not self.error:
            ParamSist.GuardarParametro("VERSION_DB", "1")

    def MigrarVersion1(self):
        migrator = self.migrator
        colentero = IntegerField(default=1)
        self.migraciones.append(migrator.add_column('grupos', 'impuesto', colentero))
        self.migraciones.append(migrator.add_foreign_key_constraint('grupos', 'impuesto', 'impuestos', 'idimpuesto',
                                   on_delete=None, on_update='CASCADE'))

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

