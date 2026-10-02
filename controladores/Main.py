# coding=utf-8
"""Controlador principal: arma la base y maneja la navegacion.

Como funciona la navegacion
---------------------------
La vista (vistas/Main.py) declara SECCIONES, una lista de acciones con su
clave. Este controlador tiene que tener un destino para cada clave, en
DESTINOS. La vista avisa una clave y el controller abre lo que corresponda.

Eso sustituye al patron anterior, donde cada boton abria un QMenu pegado a la
posicion del cursor y comparaba el QAction devuelto con una cadena de if/elif.
Con el mapa:

  * agregar una accion es agregar una linea en la vista y otra aca
  * una accion sin destino es un error visible, y hay un test que la busca
  * las acciones de Compras, que estaban escritas pero no conectadas a nada,
    quedan expuestas al usuario

Nota: el codigo de la base (CreaTablas, Migraciones, respaldo) no cambio. Lo
que cambio es como se llega a cada pantalla.
"""

import logging
import os
import traceback
from shutil import copyfile

import peewee
import pymysql
from PyQt5.QtWidgets import QApplication

from controladores.ABMCategoriasMonotributo import ABMCategoriaMonoController
from controladores.ABMGrupos import ABMGruposController
from controladores.ABMImpuestos import ABMImpuestoController
from controladores.ABMParametrosSistema import ABMParamSistController
from controladores.ABMTipoDocumentos import ABMTipoDocumentoController
from controladores.ABMTipoResponsable import ABMTipoResponsableController
from controladores.Articulos import ArticulosController
from controladores.CargaFacturasProveedor import CargaFacturaProveedorController
from controladores.CentroCostos import CentroCostoController
from controladores.Clientes import ClientesController
from controladores.Configuracion import ConfiguracionController
from controladores.ConstatacionComprobantes import ConstatacionComprobantesController
from controladores.ConsultaCAE import ConsultaCAEController
from controladores.ConsultaCtaCte import ConsultaCtaCteController
from controladores.ConsultaPadronAfip import ConsultaPadronAfipController
from controladores.ControladorBase import ControladorBase
from controladores.DiagnosticoAfip import DiagnosticoAfip
from controladores.EmiteRecibo import EmiteReciboController
from controladores.EnvioEmail import EnvioEmailController
from controladores.Facturas import FacturaController
from controladores.FirmaCorreoElectronico import FirmaCorreoElectronicoController
from controladores.GeneraCertificados import GeneraCertificadosController
from controladores.ImportacionAFIP import ImportaAFIPController
from controladores.InformeRecategorizacionMonotributo import InfRecMonotributoController
from controladores.InformeVentasPorGrupo import InformeVentasPorGrupoController
from controladores.IVACompras import IVAComprasController
from controladores.IVAVentas import IVAVentasController
from controladores.Localidades import LocalidadesController
from controladores.MigracionBaseDatos import MigracionBaseDatos
from controladores.Proveedores import ProveedoresController
from controladores.RG3685Compras import RG3685ComprasController
from controladores.RG3685Ventas import RG3685VentasController
from controladores.ReImprimeFactura import ReImprimeFacturaController
from controladores.ReImprimeRemito import ReImprimeRemitoController
from controladores.Remitos import RemitoController
from controladores.RindeCAEAIndividual import RindeCAEAIndividualController
from controladores.TipoComprobantes import TipoComprobantesController
from controladores.Resguardo import ResguardoController
from controladores.VentaSimple import VentaSimpleController
from libs import Ventanas
from libs.Utiles import (FechaMysql, GrabarIni, LeerIni,
                         inicializar_y_capturar_excepciones)
from modelos.Clientes import FichaCliente
from modelos.ModeloBase import ModeloBase
from modelos.ParametrosSistema import ParamSist
from vistas.Main import MainView


class Main(ControladorBase):

    def __init__(self):
        super(Main, self).__init__()
        if LeerIni("base") == "sqlite":
            # pongo todo en un try para que en caso de que no exista aun la
            # base de datos continue de todas formas
            try:
                copyfile("sistema.db", "sistema-res.db")
            except Exception:
                pass
        self.view = MainView()
        self.view.initUi()
        self.model = ModeloBase()
        self.model.getDb()
        if not LeerIni("ultima_copia"):
            GrabarIni(clave='ultima_copia', key='param', valor='00000000')
        ult = LeerIni("ultima_copia")
        if LeerIni("base") == "sqlite":
            if ult < FechaMysql():
                resguardo = ResguardoController()
                resguardo.Cargar("sistema-res.db")
                resguardo.Cargar("sistema.ini")
                GrabarIni(clave='ultima_copia', key='param', valor=FechaMysql())
        self.CreaTablas()
        self.Migraciones()
        self.conectarWidgets()
        self.initUi()

    def initUi(self):
        """La vista lee sola la configuracion del encabezado y la barra de estado.

        Aca solo se refresca, para que quede al dia si algo cambio desde la
        ultima vez que se abrio la ventana.
        """
        self.view.refrescar_datos()

    def conectarWidgets(self):
        self.view.navegar.connect(self.onNavegar)

    # -- Navegacion --------------------------------------------------------
    def onNavegar(self, clave):
        """Abre la pantalla de la clave. Si no hay destino, lo dice."""
        destino = self.DESTINOS().get(clave)
        if destino is None:
            # No deberia pasar: hay un test que revisa que todas las claves de
            # la vista tengan destino. Si aparece, se ve en vez de fallar en
            # silencio con un AttributeError.
            Ventanas.showAlert("Sistema",
                               "La acción '{}' todavía no tiene destino.".format(clave))
            return
        self.view.marcar_activo(clave)
        try:
            destino()
        except Exception as e:
            # Esto corre dentro de un slot de Qt. Si algo falla al construir o
            # abrir una pantalla, la excepcion se pierde: el ejecutable esta
            # compilado con -w (sin consola), asi que no se ve por ningun lado
            # y el usuario solo ve que "no pasa nada" al hacer clic. Se muestra
            # y se loguea.
            self.Traceback = traceback.format_exc()
            logging.error("No se pudo abrir %r: %s", clave, e)
            logging.error(self.Traceback)
            Ventanas.showAlert(
                "Sistema",
                "No se pudo abrir '{}'.\n\n{}: {}".format(clave, type(e).__name__, e))

    def _abrir(self, controlador, usar_exec=True):
        """Instancia un controlador y abre su ventana.

        Un mismo constructor se comporta distinto segun el tipo de pantalla:
        unos son QDialog (se abren con exec_) y otros QWidget (se muestran con
        show()). El metodo se llama distinto segun el caso, asi que se centraliza
        la decision en un helper con un nombre explicito por pantalla.
        """
        ventana = controlador()
        if usar_exec:
            ventana.exec_()
        else:
            ventana.view.exec_()
        return ventana

    def DESTINOS(self):
        """Mapa clave -> accion. Se arma por metodo porque usa self."""
        return {
            # -- Facturacion
            "nueva-venta": lambda: self._abrir(VentaSimpleController),
            "comprobantes": lambda: self._abrir(FacturaController),
            "remitos": lambda: self._abrir(RemitoController, usar_exec=False),
            "recibos": lambda: self._abrir(EmiteReciboController),
            "reimprimir-factura": lambda: self._abrir(ReImprimeFacturaController),
            "reimprimir-remito": lambda: self._abrir(ReImprimeRemitoController),

            # -- Compras: los cinco estaban escritos y no conectados a nada
            "proveedores": lambda: self._abrir(ProveedoresController, usar_exec=False),
            "centro-costos": lambda: self._abrir(CentroCostoController),
            "carga-facturas": lambda: self._abrir(CargaFacturaProveedorController,
                                                 usar_exec=False),
            "iva-compras": lambda: self._abrir(IVAComprasController, usar_exec=False),
            "rg3685-compras": lambda: self._abrir(RG3685ComprasController),

            # -- Fiscal
            "iva-ventas": lambda: self._abrir(IVAVentasController),
            "rg3685-ventas": lambda: self._abrir(RG3685VentasController),
            "importar": lambda: self._abrir(ImportaAFIPController),

            # -- Clientes
            "clientes": lambda: self._abrir(ClientesController),
            "cuenta-corriente": lambda: self._abrir(ConsultaCtaCteController),
            "enviar-email": lambda: self._abrir(EnvioEmailController),

            # -- Stock
            "productos": lambda: self._abrir(ArticulosController, usar_exec=False),
            "grupos": lambda: self._abrir(ABMGruposController),
            "impuestos": lambda: self._abrir(ABMImpuestoController),
            "informe-ventas-grupo": lambda: self._abrir(InformeVentasPorGrupoController,
                                                        usar_exec=False),

            # -- ARCA / AFIP
            "diagnostico": self.diagnostico_arca,
            "consulta-cuit": lambda: self._abrir(ConsultaPadronAfipController,
                                                 usar_exec=False),
            "constatacion": lambda: self._abrir(ConstatacionComprobantesController,
                                               usar_exec=False),
            "consulta-cae": lambda: self._abrir(ConsultaCAEController),
            "rinde-caea": lambda: self._abrir(RindeCAEAIndividualController),

            # -- Monotributo
            "categorias-mono": lambda: self._abrir(ABMCategoriaMonoController),
            "informe-recategorizacion": lambda: self._abrir(InfRecMonotributoController),

            # -- Catalogos
            "localidades": lambda: self._abrir(LocalidadesController),
            "tipo-comprobantes": lambda: self._abrir(TipoComprobantesController,
                                                     usar_exec=False),
            "tipo-documentos": lambda: self._abrir(ABMTipoDocumentoController),
            "tipo-responsable": lambda: self._abrir(ABMTipoResponsableController),

            # -- Configuracion
            "configuracion": lambda: self._abrir(ConfiguracionController,
                                                usar_exec=False),
            "parametros": lambda: self._abrir(ABMParamSistController),
            "firma-email": lambda: self._abrir(FirmaCorreoElectronicoController),
            "certificados": lambda: self._abrir(GeneraCertificadosController),
        }

    def diagnostico_arca(self):
        diagnostico = DiagnosticoAfip()
        pasos = diagnostico.ejecutar()
        Ventanas.showAlert(LeerIni("nombre_sistema"), diagnostico.formatear(pasos))

    # -- Base de datos -----------------------------------------------------
    @inicializar_y_capturar_excepciones
    def CreaTablas(self, *args, **kwargs):
        if LeerIni("base") == "mysql":  # en caso de que sea mysql y no este creada la base la crea
            basedatos = LeerIni("basedatos")
            user = LeerIni("usuario")
            # El resolver entiende las tres formas de guardar el secreto
            # (dpapi:v1:, fernet:v1: y el esquema viejo), asi que aca no se
            # descifra a mano y no se rompe cuando el valor ya migro.
            from libs.secretos import resolver_password_base
            password = resolver_password_base()
            if not password:
                print("No se pudo obtener el password de la base, no se crea.")
                return
            host = LeerIni("host")
            conn = pymysql.connect(host=host, user=user, password=password)
            conn.cursor().execute('CREATE DATABASE IF NOT EXISTS {}'.format(basedatos))
            conn.close()

        try:
            ParamSist.create_table(safe=True)
        except peewee.InternalError:
            Ventanas.showAlert("Sistema", "Verifique que la base de datos este creada en {}".format(
                LeerIni("host")
            ))

        try:
            FichaCliente.create_table()
        except peewee.InternalError:
            Ventanas.showAlert("Sistema", "Verifique que la base de datos este creada en {}".format(
                LeerIni("host")
            ))

    def Migraciones(self):
        migracion = MigracionBaseDatos()
        migracion.Migrar()
