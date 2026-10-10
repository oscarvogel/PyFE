# coding=utf-8
"""Asistente de configuracion de una instalacion nueva.

Se muestra en el primer arranque, antes de que se arme la conexion a la
base. No extiende Formulario a proposito: Formulario importa los modelos,
que tocan la base de datos, y este dialogo tiene que existir antes de
que eso pase.

Los certificados quedan para el final y son opcionales: se pueden cargar
mas tarde desde la pantalla de Configuracion, asi que no bloquean la
instalacion.
"""

from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QGridLayout,
                             QGroupBox, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QVBoxLayout, QWidget)

from libs.Utiles import validar_cuit
from libs.build_info import nombre_build

# La lista sale de libs/catalogos.py y no se escribe aca. Estaba duplicada y
# le faltaban el 7 (Sujeto No Categorizado) y el 16 (Monotributo Trabajador
# Independiente), que ARCA si define. El orden es el de la tabla de ARCA.
def _categorias_iva():
    from libs.catalogos import CATEGORIAS_IVA_EMISOR
    return [(etiqueta, str(codigo)) for codigo, etiqueta in CATEGORIAS_IVA_EMISOR]


class DialogoPrimerArranque(QDialog):
    """Pide los datos de la instalacion y devuelve un dict."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración inicial de {}".format(nombre_build()))
        self.setModal(True)
        self.resize(560, 640)

        contenedor = QWidget()
        vertical = QVBoxLayout(contenedor)

        # --- Base de datos -------------------------------------------------
        gbBase = QGroupBox("Base de datos")
        formBase = QFormLayout(gbBase)

        self.cmbBase = QComboBox()
        self.cmbBase.addItem("SQLite (no necesita servidor)", "sqlite")
        self.cmbBase.addItem("MySQL / MariaDB", "mysql")
        self.cmbBase.currentIndexChanged.connect(self._actualizar_base)
        formBase.addRow("Tipo de base", self.cmbBase)

        self.txtBasedatos = QLineEdit()
        self.txtBasedatos.setPlaceholderText("nombre de la base")
        formBase.addRow("Base de datos", self.txtBasedatos)

        self.txtHost = QLineEdit()
        self.txtHost.setPlaceholderText("localhost")
        formBase.addRow("Servidor", self.txtHost)

        self.txtUsuario = QLineEdit()
        formBase.addRow("Usuario", self.txtUsuario)

        self.txtPassword = QLineEdit()
        self.txtPassword.setEchoMode(QLineEdit.Password)
        formBase.addRow("Password", self.txtPassword)

        self.chkRecordar = QCheckBox("Recordar el password en esta computadora")
        self.chkRecordar.setChecked(True)
        self.chkRecordar.setToolTip(
            "Se guarda protegido por Windows, asociado a este usuario.\n"
            "Si lo deseleccion, se le va a pedir en cada arranque.")
        formBase.addRow("", self.chkRecordar)
        vertical.addWidget(gbBase)

        # --- Datos fiscales ------------------------------------------------
        gbFiscal = QGroupBox("Datos fiscales")
        formFiscal = QFormLayout(gbFiscal)

        self.txtEmpresa = QLineEdit()
        self.txtEmpresa.setPlaceholderText("Razon social")
        formFiscal.addRow("Empresa", self.txtEmpresa)

        self.txtMembrete1 = QLineEdit()
        formFiscal.addRow("Membrete linea 1", self.txtMembrete1)

        self.txtMembrete2 = QLineEdit()
        formFiscal.addRow("Membrete linea 2", self.txtMembrete2)

        self.txtCuit = QLineEdit()
        self.txtCuit.setPlaceholderText("20-12345678-9")
        self.txtCuit.textChanged.connect(self._validar_cuit_en_vivo)
        formFiscal.addRow("CUIT", self.txtCuit)

        self.lblCuit = QLabel("")
        # El color del mensaje de error lo decide el tema, no esta linea.
        # Ver QLabel[estado="error"] en temas/pyfe.css.
        self.lblCuit.setProperty("estado", "error")
        formFiscal.addRow("", self.lblCuit)

        self.txtIibb = QLineEdit()
        formFiscal.addRow("IIBB", self.txtIibb)

        self.txtInicio = QLineEdit("01/01/2000")
        formFiscal.addRow("Inicio de actividades", self.txtInicio)
        vertical.addWidget(gbFiscal)

        # --- Facturacion ---------------------------------------------------
        gbFact = QGroupBox("Facturacion")
        formFact = QFormLayout(gbFact)

        self.cmbCatIva = QComboBox()
        for etiqueta, valor in _categorias_iva():
            self.cmbCatIva.addItem(etiqueta, valor)
        idx = self.cmbCatIva.findData("6")
        if idx >= 0:
            self.cmbCatIva.setCurrentIndex(idx)
        formFact.addRow("Categoria IVA", self.cmbCatIva)

        self.txtPtoVta = QLineEdit("1")
        formFact.addRow("Punto de venta", self.txtPtoVta)

        self.txtNombreSistema = QLineEdit(nombre_build())
        formFact.addRow("Nombre del sistema", self.txtNombreSistema)
        vertical.addWidget(gbFact)

        # --- Certificados (opcionales) -------------------------------------
        gbCert = QGroupBox("Certificados de AFIP (se pueden cargar despues)")
        formCert = QFormLayout(gbCert)

        self.txtCertHomo = QLineEdit("certificados/certificado_homologacion.crt")
        formCert.addRow("Certificado homologacion",
                        self._con_boton(self.txtCertHomo))
        self.txtCertProd = QLineEdit("certificados/certificado_produccion.crt")
        formCert.addRow("Certificado produccion",
                        self._con_boton(self.txtCertProd))
        self.txtKeyHomo = QLineEdit("certificados/clave_privada_homo.key")
        formCert.addRow("Clave privada homologacion",
                        self._con_boton(self.txtKeyHomo))
        self.txtKeyProd = QLineEdit("certificados/clave_privada_produccion.key")
        formCert.addRow("Clave privada produccion",
                        self._con_boton(self.txtKeyProd))
        vertical.addWidget(gbCert)

        # --- Envoltorio ----------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(contenedor)

        self.lblAviso = QLabel(
            "Estos datos se guardan en sistema.ini, en la carpeta de la "
            "instalacion. La mayoria se pueden cambiar despues desde "
            "Configuracion.")
        self.lblAviso.setWordWrap(True)

        self.botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.botones.button(QDialogButtonBox.Ok).setText("Guardar y continuar")
        self.botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.botones.accepted.connect(self.aceptar)
        self.botones.rejected.connect(self.reject)

        raiz = QVBoxLayout(self)
        raiz.addWidget(QLabel("<b>Bienvenido. Complete los datos para empezar.</b>"))
        raiz.addWidget(self.lblAviso)
        raiz.addWidget(scroll)
        raiz.addWidget(self.botones)

        self._actualizar_base()

    # -- helpers ----------------------------------------------------------
    def _con_boton(self, campo):
        """Un campo de texto con un boton ... para buscar el archivo."""
        grilla = QGridLayout()
        grilla.addWidget(campo, 0, 0)
        boton = QPushButton("...")
        boton.setFixedWidth(34)
        boton.clicked.connect(lambda: self._buscar(campo))
        grilla.addWidget(boton, 0, 1)
        contenedor = QWidget()
        contenedor.setLayout(grilla)
        return contenedor

    def _buscar(self, campo):
        archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
        if archivo:
            campo.setText(archivo)

    def _actualizar_base(self):
        es_mysql = self.cmbBase.currentData() == "mysql"
        for campo in (self.txtHost, self.txtUsuario, self.txtPassword,
                      self.chkRecordar):
            campo.setEnabled(es_mysql)
        if not es_mysql:
            self.txtHost.setText("localhost")

    def _validar_cuit_en_vivo(self):
        texto = self.txtCuit.text().strip()
        if not texto:
            self.lblCuit.setText("")
            return
        if len(texto) == 13 and validar_cuit(texto):
            self.lblCuit.setText("")
        else:
            self.lblCuit.setText("El CUIT no es válido (13 dígitos con el dígito verificador)")

    # -- resultado --------------------------------------------------------
    def datos(self):
        es_mysql = self.cmbBase.currentData() == "mysql"
        d = {
            "base": self.cmbBase.currentData(),
            "basedatos": self.txtBasedatos.text().strip(),
            "host": self.txtHost.text().strip(),
            "usuario": self.txtUsuario.text().strip(),
            "empresa": self.txtEmpresa.text().strip(),
            "membrete1": self.txtMembrete1.text().strip(),
            "membrete2": self.txtMembrete2.text().strip(),
            "cuit": self.txtCuit.text().strip(),
            "iibb": self.txtIibb.text().strip(),
            "inicio": self.txtInicio.text().strip() or "01/01/2000",
            "cat_iva": self.cmbCatIva.currentData(),
            "pto_vta": self.txtPtoVta.text().strip() or "1",
            "nombre_sistema": self.txtNombreSistema.text().strip() or nombre_build(),
            "homo": "S",
            "cert_homo": self.txtCertHomo.text().strip(),
            "cert_prod": self.txtCertProd.text().strip(),
            "privatekey_homo": self.txtKeyHomo.text().strip(),
            "privatekey_prod": self.txtKeyProd.text().strip(),
        }
        if es_mysql and self.chkRecordar.isChecked():
            d["password"] = self.txtPassword.text()
        return d

    def aceptar(self):
        d = self.datos()
        faltan = []
        if not d["empresa"]:
            faltan.append("la empresa")
        cuit = d["cuit"]
        if not cuit:
            faltan.append("el CUIT")
        elif not (len(cuit) == 13 and validar_cuit(cuit)):
            faltan.append("un CUIT valido")
        if d["base"] == "mysql" and not d["basedatos"]:
            faltan.append("el nombre de la base de datos")
        if faltan:
            self.lblAviso.setText(
                "<span style='color:#b00020'>Falta completar: {}</span>".format(
                    ", ".join(faltan)))
            return
        super().accept()
