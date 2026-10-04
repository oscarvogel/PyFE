# coding=utf-8
"""El controlador de la pantalla de diseno.

Lo importante de este archivo son dos cosas.

La vista previa
---------------
Boton "Ver comprobante de prueba". Arma un PDF con datos de mentira usando el
MISMO metodo que imprime una factura real (FacturaController._armar_comprobante).
No se puede probar con una factura de verdad porque emitir deja rastro fiscal
contra ARCA y no se puede deshacer, asi que un cliente que quiere ver si le
gusta su diseno no puede hacerlo sin arriesgar una factura. Y no sirve Armar el
PDF a mano en otro lado: si la vista previa usa un camino distinto al de la
impresion, muestra un diseno que la app no usa, que es justo el problema que
viene a resolver.

Ni una fila de la base se toca para esto. Los datos del comprobante de muestra
son un objeto en memoria, no un Cabfact.

Los diez parametros
-------------------
Se leen y se escriben por ParamSist. Antes existian, los leia FacturaBranding,
y no habia NADA que los escribiera: habia que entrar a la base a mano. Esta
pantalla es ese 'algo que los escribe'.
"""
import os
import tempfile
from decimal import Decimal

from controladores.ControladorBase import ControladorBase
from controladores.Facturas import FacturaController
from controladores.FacturaBranding import cargar_config_marca_factura
from libs import Ventanas
from libs.Utiles import (LeerIni, inicializar_y_capturar_excepciones,
                         ubicacion_sistema)
from modelos.ParametrosSistema import ParamSist
from vistas.DisenoComprobante import COLORES, LIMITE_LEYENDA, LIMITE_WEB
from vistas.DisenoComprobante import DisenoComprobanteView

PREFIXO = "FACTURA_MARCA_"


class _Muestra(object):
    """Un comprobante de mentira para la vista previa.

    Solo tiene que parecerse en la forma a un Cabfact, porque
    _armar_comprobante solo lee atributos. Los importes y el cliente son
    inventados y estan marcados como tales en el PDF, para que nadie lo tome
    por una factura real.
    """

    def __init__(self, tipo_comprobante, numero, renglones=()):
        cliente = _Atributos(
            idcliente=1,
            nombre="CLIENTE DE PRUEBA",
            cuit="20345678907",
            dni=11111111,
            tiporesp_id=1,
            tiporesp=_Atributos(nombre="RESPONSABLE INSCRIPTO",
                                idtiporesp=1, condicion_iva_receptor_id=1),
            localidad=_Atributos(nombre="CAPITAL", provincia="CABA"),
            percepcion=_Atributos(detalle="IIBB"),
        )
        self.tipocomp = _Atributos(codigo=tipo_comprobante, nombre="FACTURA A")
        self.cliente = cliente
        self.numero = numero
        # idcabfact no se usa para calcular nada: lo lee el mensaje de error
        # de _pdf_generado, para decir que comprobante es. Va en cero porque
        # esta muestra no esta guardada en ningun lado.
        self.idcabfact = 0
        # Fechas de verdad, no texto: FechaMysql() les llama strftime() y con
        # un string revienta. Que reviente aca es buena noticia, porque es el
        # metodo real de impresion el que revienta, no un doble.
        import datetime
        self.fecha = datetime.date(2026, 1, 1)
        self.concepto = 1
        self.nombre = ""
        self.domicilio = "DIRECCION DE PRUEBA"
        self.total = Decimal("121.00")
        self.neto = Decimal("100.00")
        self.iva = Decimal("21.00")
        self.percepciondgr = Decimal("0.00")
        self.netoa = Decimal("100.00")
        self.netob = Decimal("0.00")
        self.cae = "71234567890123"
        self.venccae = datetime.date(2026, 1, 11)
        self.desde = datetime.date(2026, 1, 1)
        self.hasta = datetime.date(2026, 1, 1)
        self.formapago = _Atributos(detalle="CONTADO")
        # Los items del comprobante. _armar_comprobante los busca en detfact si
        # no se le pasan, y la vista previa no puede meter filas en la base de
        # verdad, asi que se los pasa.
        self.renglones = list(renglones)

    def items_de_muestra(self):
        """Dos renglones de mentira, con la forma de un Detfact."""
        return [
            _Atributos(
                idarticulo=_Atributos(idarticulo=1),
                descad="SERVICIO DE PRUEBA",
                cantidad=Decimal("1"),
                precio=Decimal("100.00"),
                tipoiva=_Atributos(iva=Decimal("21")),
                montoiva=Decimal("21.00"),
            ),
            _Atributos(
                idarticulo=_Atributos(idarticulo=2),
                descad="PRODUCTO DE PRUEBA",
                cantidad=Decimal("2"),
                precio=Decimal("10.50"),
                tipoiva=_Atributos(iva=Decimal("21")),
                montoiva=Decimal("4.41"),
            ),
        ]


class _Atributos(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


class _ImpresorDeMuestra(FacturaController):
    """El FacturaController sin ventana, para la vista previa.

    Hereda de verdad y solo se salta el __init__ que arma la pantalla. Asi el
    PDF se arma con el codigo de la impresion real y no con una copia: si la
    vista previa usara otro camino, mostraria un diseno que la app no usa, que
    es justo el problema que viene a resolver.

    _armar_comprobante() no toca self.view, asi que view = None noMolesta.
    Donde si se usaba era en _cae_de_pantalla(), que tiene su propio except.
    """

    def __init__(self):
        self.view = None
        self.facturaGenerada = None
        self.Excepcion = ""
        self.Traceback = ""
        self.SilenciarError = True


class DisenoComprobanteController(ControladorBase):

    def __init__(self):
        super(DisenoComprobanteController, self).__init__()
        self.view = DisenoComprobanteView()
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGrabar.clicked.connect(self.GrabaParametros)
        self.view.btnProbar.clicked.connect(self.VerComprobanteDePrueba)

    # -- Carga y guardado ---------------------------------------------------

    def _leer(self, clave, defecto=""):
        try:
            return ParamSist.ObtenerParametro(PREFIXO + clave) or defecto
        except Exception:
            return defecto

    def CargaDatos(self, *args, **kwargs):
        config = cargar_config_marca_factura()
        activa = "S" if config.activa else "N"
        self.view.controles['activa'].setIndex(activa)

        # Las rutas del logo y del fondo se guardan como quedan en el
        # parametro, que es lo que espera FacturaBranding.
        self.view.controles['logo'].setText(config.logo or "")
        self.view.controles['fondo'].setText(config.fondo or "")
        self.view.controles['web'].setText(config.web or "")
        self.view.controles['leyenda'].setText(config.leyenda or "")

        for clave, _nombre, defecto in COLORES:
            self.view.controles[clave].setText(self._leer(
                "COLOR_" + clave.replace("color_", "").upper(), defecto))

    @inicializar_y_capturar_excepciones
    def GrabaParametros(self, *args, **kwargs):
        malos = self.view.colores_invalidos()
        if malos:
            Ventanas.showAlert(
                "Diseño del comprobante",
                "Estos colores no se pueden usar:\n\n{}\n\nVa un valor como "
                "#0F2A44: seis digitos hexadecimales, con o sin el #.".format(
                    "\n".join(malos)))
            return False

        if not self._existen(self.view.controles['logo'].text()):
            Ventanas.showAlert(
                "Diseño del comprobante",
                "No se encuentra el logo:\n{}\n\nCopiarlo con el botón de "
                "archivo, o dejarlo vacio para no usar logo.".format(
                    self.view.controles['logo'].text()))
            return False

        if not self._existen(self.view.controles['fondo'].text()):
            Ventanas.showAlert(
                "Diseño del comprobante",
                "No se encuentra la imagen de fondo:\n{}\n\nCopiarlo con el "
                "botón de archivo, o dejarlo vacio para no usar fondo.".format(
                    self.view.controles['fondo'].text()))
            return False

        # El boton de Aceptar avisa que se va a pisar el diseno anterior, que
        # es la unica forma de volver atras: el parametro es lo unico que hay.
        Ventanas.showAlert("Diseño guardado",
                           "El comprobante va a salir con este diseño desde "
                           "la próxima impresión.")

        for clave, valor in self._parametros():
            ParamSist.GuardarParametro(PREFIXO + clave, valor)
        return True

    def _parametros(self):
        """Los diez, en el orden y con el nombre que espera FacturaBranding."""
        parametros = [
            ("ACTIVA", self.view.controles['activa'].text()),
            ("FORMATO", "plantillas/factura_marca.csv"),
            ("LOGO", self.view.controles['logo'].text().strip()),
            ("FONDO", self.view.controles['fondo'].text().strip()),
            ("WEB", self.view.controles['web'].text().strip()[:LIMITE_WEB]),
            ("LEYENDA", self.view.controles['leyenda'].text().strip()[:LIMITE_LEYENDA]),
        ]
        for clave, _nombre, defecto in COLORES:
            valor = self.view.controles[clave].text().strip().upper()
            if not valor.startswith('#'):
                valor = '#' + valor
            parametros.append(("COLOR_" + clave.replace("color_", "").upper(),
                                valor))
        return parametros

    @staticmethod
    def _existen(ruta):
        ruta = str(ruta or "").strip()
        if not ruta:
            return True
        return os.path.isfile(os.path.join(ubicacion_sistema(), ruta)) or \
            os.path.isfile(ruta)

    # -- Vista previa --------------------------------------------------------

    @inicializar_y_capturar_excepciones
    def VerComprobanteDePrueba(self, *args, **kwargs):
        """Arma un PDF de muestra y lo abre. No toca la base.

        Los parametros se guardan ANTES de generar, asi el PDF sale con lo que
        el operador acaba de cargar y no con lo que habia de antes. Si no, la
        vista previa muestra el diseno viejo y el operador no puede ver lo que
        acaba de hacer.
        """
        if not self.GrabaParametros():
            return False

        # El codigo del QR lleva el CUIT, y la libreria lo pasa a int. Sin
        # CUIT el error es un 'invalid literal for int()' que no dice nada.
        # En una instalacion real siempre esta, porque lo escribe el
        # asistente de primer arranque, pero si falta que lo diga claro.
        from libs.instalacion import cuit_emisor, cuit_es_real
        if not cuit_es_real(cuit_emisor()):
            Ventanas.showAlert(
                "Diseño del comprobante",
                "No hay un CUIT de emisor cargado, y sin él no se puede armar "
                "el código QR del comprobante.\n\nCargalo en Configuración > "
                "Configuración de inicio > CUIT.")
            return False

        # En la carpeta temporal: un comprobante de muestra no debe quedar
        # mezclado con las facturas de verdad, que se reimprimen despues.
        carpeta = tempfile.mkdtemp(prefix="comprobante_prueba_")
        salida = os.path.join(carpeta, "comprobante-de-prueba.pdf")

        try:
            factura = _ImpresorDeMuestra()
            muestra = _Muestra(1, "000100000001")
            ok = factura._armar_comprobante(
                muestra, salida=salida, mostrar=False,
                renglones=muestra.items_de_muestra())
            factura.SilenciarError = False

            if not ok or not os.path.isfile(salida):
                Ventanas.showError(
                    "No se pudo generar la muestra.",
                    "El comprobante de prueba no salió.",
                    que_hacer="Revise que las rutas del logo y del fondo existan, "
                              "y que la carpeta tenga permiso de escritura.",
                    detalle=getattr(factura, "Traceback", "") or
                            getattr(factura, "Excepcion", ""))
                return False

            self.view.setTextStatusBar("Muestra: {}".format(salida))
            if not self._abrir_muestra(salida):
                Ventanas.showAlert(
                    "Comprobante de prueba",
                    "Se generó la muestra pero no se pudo abrir sola.\n\n"
                    "Está en:\n{}".format(salida))
            return True
        except Exception as e:
            Ventanas.showError(
                "No se pudo generar la muestra.",
                "Revise el detalle.",
                que_hacer="Si el problema es de colores o de plantilla, "
                          "corríalo y volvé a probar.",
                detalle="{}: {}".format(type(e).__name__, e))
            return False

    @staticmethod
    def _abrir_muestra(salida):
        """Abre el PDF con el visor del sistema. False si no se pudo."""
        try:
            os.startfile(salida)
            return True
        except Exception:
            return False
