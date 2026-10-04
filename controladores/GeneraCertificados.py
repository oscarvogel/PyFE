import os
import threading

from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication

from controladores.ControladorBase import ControladorBase
from libs import Ventanas
from libs.Utiles import (LeerIni, formato_cuit, inicializar_y_capturar_excepciones,
                         validar_cuit)
from libs.instalacion import cuit_emisor
from pyafipws.wsaa import WSAA
from vistas.GenerarCertificados import GeneraCertificadoView

# El nombre de la clave que la app ya espera en sistema.ini. El CSR no cambia
# segun el modo, pero la primera instalacion arranca en homologacion, asi que
# el par que se baja de ARCA es el de homologacion.
NOMBRE_CLAVE_HOMOLOGACION = "clave_privada_homo.key"
NOMBRE_CERT_HOMOLOGACION = "certificado_homologacion.crt"

ETAPAS = [
    "Generando la clave privada",
    "Firmando el pedido de certificado",
]


class _CertificadoWorker(QObject):
    """Crea la clave y firma el CSR en un hilo aparte.

    Va en su propia clase y no como metodo del controlador por la misma razon
    que el worker de la emision de facturas: Qt necesita un QObject con vida
    propia, y SIN padre a proposito, porque Qt no deja mover a otro hilo un
    QObject con padre. Si se le pasa la vista como padre, el trabajo termina en
    el hilo principal y la ventana se sigue congelando igual: parece que
    funciona y no funciona. La vida la sostiene self._worker en el controlador.
    """

    etapa = pyqtSignal(str)
    terminado = pyqtSignal(bool, str)

    def __init__(self, cuit, empresa, nombre, ruta_csr, ruta_clave, parent=None):
        super().__init__(parent)
        self._datos = (cuit, empresa, nombre, ruta_csr, ruta_clave)

    @pyqtSlot()
    def run(self):
        cuit, empresa, nombre, ruta_csr, ruta_clave = self._datos
        try:
            wsaa = WSAA()
            self.etapa.emit(ETAPAS[0])
            wsaa.CrearClavePrivada(filename=ruta_clave)
            self.etapa.emit(ETAPAS[1])
            wsaa.CrearPedidoCertificado(cuit=cuit, empresa=empresa,
                                        nombre=nombre, filename=ruta_csr)
            self.terminado.emit(True, "")
        except Exception as e:
            self.terminado.emit(False, "{}: {}".format(type(e).__name__, e))


class GeneraCertificadosController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = GeneraCertificadoView()
        self._worker = None
        self._hilo = None
        self._progreso = None
        self.conectarWidgets()
        self.CargaDatos()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGenera.clicked.connect(self.onClickBtnGenera)

    def CargaDatos(self):
        self.view.controles['cuit'].setText(formato_cuit(cuit_emisor()))
        self.view.controles['empresa'].setText(LeerIni(clave='empresa', key='FACTURA'))
        self.view.controles['nombre'].setText(LeerIni(clave='empresa', key='FACTURA'))

    # -- El pedido de certificado -------------------------------------------

    @inicializar_y_capturar_excepciones
    def onClickBtnGenera(self):
        cuit = self.view.controles['cuit'].text().strip()
        empresa = self.view.controles['empresa'].text().strip()
        nombre = self.view.controles['nombre'].text().strip()
        ruta_csr = self.view.controles['archivo'].text().strip()

        # El CUIT va en el subject del CSR y ARCA usa ese valor para emitir el
        # certificado. Si esta mal, el certificado sale con el CUIT equivocado y
        # hay que repetir todo con una clave nueva. Por eso se valida antes de
        # generar la clave, no despues.
        if not validar_cuit(cuit):
            Ventanas.showAlert(
                "Certificado",
                "El CUIT no es valido: {}.\n\nARCA emite el certificado con "
                "ese numero, asi que uno mal obliga a empezar de nuevo con una "
                "clave nueva.".format(cuit or "(vacio)"))
            return False

        if not empresa or not nombre:
            Ventanas.showAlert(
                "Certificado",
                "Falta la razon social o el nombre del titular, que van en el "
                "pedido.")
            return False

        if not ruta_csr:
            Ventanas.showAlert(
                "Certificado",
                "Elegi donde guardar el pedido (.csr) con el boton de archivo.")
            return False

        carpeta = os.path.dirname(os.path.abspath(ruta_csr))
        if not os.path.isdir(carpeta):
            Ventanas.showAlert("Certificado",
                               "La carpeta {} no existe.".format(carpeta))
            return False

        # La clave al lado del CSR, con el nombre que la app ya espera: despues
        # de bajar el .crt de ARCA no hay que renombrar nada.
        ruta_clave = os.path.join(carpeta, NOMBRE_CLAVE_HOMOLOGACION)
        if os.path.exists(ruta_clave):
            if not Ventanas.showConfirmation(
                    "Ya hay una clave privada",
                    "En {} ya hay una clave. Si seguis, se REEMPLAZA, y con "
                    "ella se pierde cualquier certificado que se haya hecho "
                    "con la anterior.\n\n¿Seguir?".format(ruta_clave),
                    textoOk="Reemplazar la clave", textoCancelar="Cancelar"):
                return False

        return self._generar(cuit, empresa, nombre, ruta_csr, ruta_clave)

    def _generar(self, cuit, empresa, nombre, ruta_csr, ruta_clave):
        """Corre el pedido en un hilo y espera, sin congelar la ventana.

        Generar una clave RSA de 4096 bits lleva segundos. En el hilo principal
        la ventana quedaria congelada, y este es el primer boton que aprieta un
        cliente que quiere emitir: que se congele ahi es la peor primera
        impresion que hay.
        """
        estado = {"ok": False, "error": ""}
        listo = threading.Event()

        def al_terminar(ok, error):
            estado["ok"] = ok
            estado["error"] = error
            listo.set()

        with Ventanas.Progreso("Generando el pedido de certificado",
                               ETAPAS) as barra:
            self._progreso = barra
            # Sin padre: ver la nota de la clase. La referencia la sostiene
            # self._worker hasta que el hilo termina.
            self._worker = _CertificadoWorker(cuit, empresa, nombre,
                                              ruta_csr, ruta_clave)
            self._worker.etapa.connect(barra.avanzar)
            self._worker.terminado.connect(al_terminar)

            self._hilo = QThread()
            self._worker.moveToThread(self._hilo)
            self._hilo.started.connect(self._worker.run)
            self._hilo.start()

            while not listo.wait(0.05):
                # El wait(0.05) devuelve solo y sigue ventilando la interfaz:
                # sin esto la ventana quedaria congelada.
                QApplication.processEvents()
                if not self._hilo.isRunning():
                    break

            self._hilo.quit()
            self._hilo.wait(5000)      # 5 s sobran para un return limpio

        self._hilo = None
        self._worker = None
        self._progreso = None

        if not estado["ok"]:
            Ventanas.showError(
                "No se pudo generar el pedido.",
                "No se genero el CSR. Si ya habia una clave privada, puede "
                "haberse reemplazado a medias: volve a intentarlo.",
                que_hacer="Revise que la carpeta tenga permiso de escritura y "
                          "que el nombre del archivo .csr no sea muy largo.",
                detalle=estado["error"])
            return False

        Ventanas.showAlert(
            "Pedido generado",
            "Se creo el pedido de certificado:\n{}\ny la clave privada:\n{}\n\n"
            "Ahora hay que autorizarlo en ARCA, que es donde se emite el "
            "certificado:\n\n"
            "1. Entrá a ManageARCA con el certificado que ya tengas.\n"
            "2. Subí el archivo .csr.\n"
            "3. Descará el certificado que te da y guardalo como\n"
            "   {} en la carpeta certificados/.\n"
            "4. Volvé a Configuración > Diagnóstico para probar si la "
            "autenticación anda.".format(
                ruta_csr, ruta_clave, NOMBRE_CERT_HOMOLOGACION))
        return True
