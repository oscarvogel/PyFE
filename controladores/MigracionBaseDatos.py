# coding=utf-8
import csv
import logging
import os
import sys
import traceback

import pymysql
from playhouse.migrate import (MySQLMigrator, SqliteMigrator, migrate,
                             IntegerField, CharField, DecimalField)

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
from modelos.Remitos import DetalleRemito, Remito
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
        # El migrador tiene que ser el del motor. Con MySQLMigrator sobre una
        # base sqlite, cada migracion de esquema era SQL de MySQL y fallaba
        # siempre con 'near "MODIFY"' o 'near "CONSTRAINT"'.
        if str(LeerIni('base') or 'sqlite').strip().lower() == 'mysql':
            self.migrator = MySQLMigrator(database)
        else:
            self.migrator = SqliteMigrator(database)

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

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 6:
            self.MigrarVersion6()

        if int(ParamSist.ObtenerParametro("VERSION_DB") or 0) < 7:
            self.MigrarVersion7()

        # No usa el migrator, y va antes de RealizaMigraciones: es una
        # correccion de DATOS, no de esquema, asi que tiene que correr tambien
        # en una base recien creada, donde las migraciones de esquema fallan
        # todas. El orden con RealizaMigraciones es al reves justamente por
        # eso: no depende de que las de esquema hayan salido bien.
        self.CorregirCondicionIvaReceptor()
        self.CorregirBitsDeMaestros()

        self.RealizaMigraciones()

        # La version solo avanza si no fallo ninguna migracion. Antes se sellaba
        # siempre: una base con la mitad del schema mal migrantado quedaba
        # marcada como al dia y no se volvia a intentar nunca, sin que nada en
        # la app dijera que faltaba.
        if self.migraciones_fallidas:
            logging.warning(
                "VERSION_DB se queda en %s: no se avanza con migraciones "
                "fallidas, y el proximo arranque las reintenta.",
                ParamSist.ObtenerParametro("VERSION_DB") or "0")
        else:
            ParamSist.GuardarParametro("VERSION_DB", "8")

        if getattr(self, "_fk_sin_hacer", False):
            logging.info(
                "No se agregaron claves foraneas: en sqlite no se pueden "
                "agregar con peewee y no se aplican por defecto. No afecta a "
                "las consultas de la app.")

    # -- Migraciones que hacen algo, o nada ---------------------------------
    #
    # Una migracion que ya se aplico no se vuelve a agregar a la lista: si se
    # agrega, corre, y falla. En una base nueva los modelos ya crean el schema
    # final, asi que TODAS las migraciones de esquema son no-ops que fallan.
    # Ahi esta el origen del ruido: no eran migraciones que fallaran, eran
    # migraciones que no tenian nada que hacer.

    def _columnas(self, tabla):
        try:
            return {c.name: c for c in db.get_columns(tabla)}
        except Exception:
            return {}

    def _tipo_de_columna(self, tabla, columna):
        """El tipo tal cual lo declara el motor: 'VARCHAR(100)'.

        NO se saca de get_columns: ese devuelve data_type='VARCHAR', sin el
        largo, y sin el largo no se puede saber si la columna es de 50 o de
        100, que es justo lo que estas migraciones vienen a arreglar.

        PRAGMA table_info en sqlite y SHOW COLUMNS en mysql devuelven el tipo
        completo. Si el motor no responde, se devuelve None y la migracion
        corre: antes es hacer migracion de mas que saltarse una que hace
        falta.
        """
        try:
            if db.__class__.__name__.startswith('MySQL'):
                for fila in db.execute_sql('SHOW COLUMNS FROM `{}`'.format(tabla)):
                    if fila[0] == columna:
                        return str(fila[1]).upper()
                return None
            for fila in db.execute_sql('PRAGMA table_info("{}")'.format(tabla)):
                if fila[1] == columna:
                    return str(fila[2]).upper()
        except Exception as e:
            logging.debug("No se pudo leer el tipo de %s.%s: %s",
                          tabla, columna, e)
        return None

    @staticmethod
    def _tipo_esperado(campo):
        """El tipo tal como lo escribe peewee: 'VARCHAR(100)'.

        Ojo: `campo.field_type` es 'VARCHAR' a secas, el largo NO esta ahi.
        Vive en ddl_datatype(), que necesita un contexto de motor para
        renderizarse, y sin contexto no se puede comparar nada. Por eso el
        tipo se arma aca, con el mismo criterio de peewee: field_type mas el
        largo, si el campo lo tiene.
        """
        tipo = str(getattr(campo, 'field_type', '') or '').upper()
        largo = getattr(campo, 'max_length', None)
        if largo and '(' not in tipo:
            tipo = '{}({})'.format(tipo, largo)
        return tipo

    def _agregar_columna(self, migrator, tabla, columna, campo):
        if columna in self._columnas(tabla):
            return
        self.migraciones.append(migrator.add_column(tabla, columna, campo))

    def _alterar_columna(self, migrator, tabla, columna, campo):
        actual = self._columnas(tabla).get(columna)
        if actual is None:
            # La columna no esta: esto no es un cambio de tipo, es un alta. La
            # deja la migracion que la agrega, si corresponde.
            return
        real = self._tipo_de_columna(tabla, columna)
        if real is not None and real == self._tipo_esperado(campo):
            return
        self.migraciones.append(
            migrator.alter_column_type(tabla, columna, campo))

    def _clave_foranea(self, migrator, tabla, columna, tabla_ref, columna_ref,
                       on_delete=None, on_update=None):
        if isinstance(migrator, SqliteMigrator):
            # sqlite no altera tablas para agregar claves foraneas con peewee, y
            # tampoco las aplica por defecto. Antes se intentaba igual, con SQL
            # de MySQL, y el error se comia. Una vez y basta.
            self._fk_sin_hacer = True
            return
        self.migraciones.append(migrator.add_foreign_key_constraint(
            tabla, columna, tabla_ref, columna_ref,
            on_delete=on_delete, on_update=on_update))

    def MigrarVersion1(self):
        migrator = self.migrator
        colentero = IntegerField(default=1)
        self._agregar_columna(migrator, 'grupos', 'impuesto', colentero)
        self._clave_foranea(migrator, 'grupos', 'impuesto', 'impuestos',
                            'idimpuesto', on_delete=None, on_update='CASCADE')

    def MigrarVersion2(self):
        migrator = self.migrator
        texto = CharField(max_length=100, default='')
        for tabla in ('clientes', 'cabfact'):
            for columna in ('nombre', 'domicilio', 'telefono'):
                self._alterar_columna(migrator, tabla, columna, texto)

    def RealizaMigraciones(self):
        """Corre lo que hay para correr. Devuelve las que fallaron.

        Antes cada error escribia el traceback entero en el log y en la
        consola, y como las migraciones de esquema siempre fallaban en una base
        nueva, instalar la app era imprimir cinco tracebacks. Ahora se corta
        al hecho y el detalle tecnico queda para el log.
        """
        self.migraciones_fallidas = []
        for m in self.migraciones:
            try:
                migrate(m)
            except Exception as e:
                self.migraciones_fallidas.append(
                    "{}: {}".format(type(e).__name__, e))
                ex = traceback.format_exception(*sys.exc_info())
                self.Traceback = ''.join(ex)
                logging.debug("Migracion fallo. Traceback:\n%s", self.Traceback)
                self.error = True

        if self.migraciones_fallidas:
            logging.warning(
                "Fallo %d de %d migraciones. La version NO se avanza, asi que "
                "el proximo arranque las reintenta. Fallos: %s",
                len(self.migraciones_fallidas), len(self.migraciones),
                "; ".join(self.migraciones_fallidas))
        elif self.migraciones:
            logging.info("Se aplicaron %d migraciones.", len(self.migraciones))
        else:
            logging.debug("No hay migraciones pendientes.")

        return self.migraciones_fallidas

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
                    Tiporesp.tipoivaepson, Tiporesp.condicion_iva_receptor_id],
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
        """Carga un CSV de datos maestros.

        Antes: `open(archivo)` y ya. Si el archivo no estaba, la excepcion
        subia y cortaba TODA la siembra en el primer faltante, sin que quedara
        rastro util. Instalando el ejecutable en una maquina nueva eso era lo
        que pasaba siempre, porque data/ no viaja al .exe: la base quedaba
        creada pero vacia, sin alicuotas de IVA, sin tipos de comprobante, sin
        formas de pago. La app arrancaba y no habia forma de emitir nada.

        Ahora cada faltante se avisa y se sigue con el resto, que es lo
        unico razonable: que falte un maestro no puede impedir cargar los
        otros.
        """
        try:
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
        except (IOError, OSError):
            logging.error(
                "No se pudo cargar el maestro %s: el archivo no esta en %s. "
                "Revisar que la carpeta data/ este junto al ejecutable.",
                archivo, os.path.dirname(os.path.abspath(archivo)))
            return 0

        try:
            modelo.insert_many(datos, fields=campos).execute()
        except:
            logging.error("Error:", sys.exc_info()[0])
        return len(datos)

    def CorregirBitsDeMaestros(self):
        """Vuelve a poner los bits de los maestros como dice el CSV.

        Los bits se guardaban mal desde el CSV (ver
        modelos/ModeloBase.py::_a_bit), asi que en toda base creada hasta ahora
        estan en cero. El caso que se ve es tipocomp.exporta, que deja la
        reimpresion de facturas, el Libro IVA Ventas y los RG 3685 con la lista
        vacia aunque haya facturas guardadas.

        Solo toca filas cuyo valor difiere del CSV, no inserta ni borra, y es
        idempotente. Un tipo que no este en el CSV se queda como esta: puede ser
        uno que creo el administrador.
        """
        import csv
        from modelos.ModeloBase import _a_bit

        campos_bit = {
            'tipoiva': None,
        }
        # Un solo maestro por ahora, y a proposito: agregar el segundo cuando
        # se haya encontrado uno que este roto, no antes.
        try:
            from modelos.Tipocomprobantes import TipoComprobante
        except Exception as e:
            logging.debug("No se pudo leer TipoComprobante: %s", e)
            return 0

        ruta = os.path.join('data', 'tipocomprobante.csv')
        if not os.path.isfile(ruta):
            logging.debug("No esta %s, se omite la correccion de bits", ruta)
            return 0

        try:
            with open(ruta, newline='') as archivo:
                filas = list(csv.reader(archivo, delimiter=','))
        except (IOError, OSError) as e:
            logging.debug("No se pudo abrir %s: %s", ruta, e)
            return 0
        del campos_bit

        corregidas = []
        for fila in filas[1:]:
            if not fila or not fila[0].strip() or len(fila) < 5:
                continue
            try:
                codigo = int(fila[0])
                esperado = _a_bit(fila[4])
            except (ValueError, TypeError):
                continue
            tipo = TipoComprobante.get_or_none(TipoComprobante.codigo == codigo)
            if tipo is None or tipo.exporta == esperado:
                continue
            tipo.exporta = esperado
            tipo.save()
            corregidas.append("{} ({}) exporta={}".format(
                tipo.nombre, codigo, esperado))

        if corregidas:
            logging.warning(
                "Se corrigio el bit 'exporta' de estos tipos de comprobante, "
                "que venian en cero por un error al leer el CSV: %s",
                "; ".join(corregidas))
        return len(corregidas)

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
        self._agregar_columna(migrator, 'categoriamono', 'ing_brutos',
                              coldecimal)
        
    def MigrarVersion6(self):
        migrator = self.migrator
        colentero = IntegerField(default=5)
        self._agregar_columna(migrator, 'tiporesp', 'condicion_iva_receptor_id',
                              colentero)
        
    def MigrarVersion7(self):
        try:
            db.create_tables([Remito, DetalleRemito])
        except:
            pass
        try:
            tipo_comprobante = TipoComprobante.get_by_id(92)
        except:
            tipo_comprobante = TipoComprobante.create(
                codigo=92,
                nombre='Proforma',
                abreviatura='PRO',
                lado='',
                exporta=0,
                ultcomp=0,
                letra='X'
            )

    def CorregirCondicionIvaReceptor(self):
        """Arregla la condicion de IVA del receptor de las bases viejas.

        Que esta correccion haga falta
        -----------------------------
        `condicion_iva_receptor_id` se agrego a la tabla con default 5, que es
        'Consumidor Final'. La siembra de data/tiporesp.csv no cargaba la
        columna, asi que en toda base creada hasta ahora las cuatro filas
        quedaron en 5: a un Responsable Inscripto con CUIT se le mandaba
        'Consumidor Final' a ARCA, incompatible con el tipo de documento 80. Y
        el campo es obligatorio desde la RG 5616.

        Que no pise lo que el usuario ya corrigio
        -----------------------------------------
        Solo toca filas que siguen en el default (5) y cuyo tipo no es
        Consumidor Final. Si alguien entro al ABM de tipos de responsable y lo
        cambio a mano, el valor ya no es 5 y queda intacto. Decidir cual de dos
        condiciones es la correcta no se puede desde acá: eso lo tiene que
        decir una persona.

        Corre en cada arranque, no solo en la migracion 8, porque son cuatro
        filas y es idempotente. Asi una base creada por una version vieja se
        arregla sola en el primer arranque posterior, le tenga VERSION_DB = 7
        clavado o no.
        """
        from libs.catalogos import (CONDICION_CONSUMIDOR_FINAL,
                                    CONDICION_IVA_POR_TIPO_RESPONSABLE)

        corregidas = []
        for tipo in Tiporesp.select():
            esperada = CONDICION_IVA_POR_TIPO_RESPONSABLE.get(
                (tipo.nombre or "").strip().upper())
            if esperada is None:
                # Un tipo que el catalogo no conoce se deja como esta: puede
                # ser uno que el usuario haya creado a mano.
                continue
            if tipo.condicion_iva_receptor_id != CONDICION_CONSUMIDOR_FINAL:
                continue
            if esperada == CONDICION_CONSUMIDOR_FINAL:
                continue
            tipo.condicion_iva_receptor_id = esperada
            tipo.save()
            corregidas.append("{}: {} -> {}".format(
                tipo.nombre, CONDICION_CONSUMIDOR_FINAL, esperada))

        if corregidas:
            logging.warning(
                "Se corrigio la condicion de IVA del receptor de estos tipos "
                "de responsable, que venian en el default: %s. Antes se mandaba "
                "'Consumidor Final' a ARCA para clientes que no lo son.",
                "; ".join(corregidas))