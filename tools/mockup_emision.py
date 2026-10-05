"""Prototipo de la pantalla de emision, rediseñada. Es un mockup, no la app.

Arma la ventana con los MISMOS componentes y el mismo tema que usa
`vistas/Facturas.py`, pero con otra jerarquia, y la guarda en PNG. Sirve para
discutir el rediseño sobre algo que se ve, y no sobre una descripcion.

No conecta nada: los campos muestran datos de ejemplo. Es un dibujo hecho con
las piezas reales, que es lo unico que se puede mirar antes de decidir.
"""

import os
import sys

os.environ.pop("QT_QPA_PLATFORM", None)
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QVBoxLayout,
                             QWidget)

from PyQt5.QtWidgets import QApplication  # noqa: E402

SALIDA = os.path.join(RAIZ, "_capturas")
if not os.path.isdir(SALIDA):
    os.makedirs(SALIDA)

app = QApplication.instance() or QApplication([])

from libs.Botones import Boton, BotonCerrarFormulario  # noqa: E402
from libs.Checkbox import CheckBox  # noqa: E402
from libs.Etiquetas import Etiqueta, EtiquetaTitulo  # noqa: E402
from libs.Fechas import Fecha  # noqa: E402
from libs.Formulario import Formulario  # noqa: E402
from libs.Grillas import Grilla  # noqa: E402
from libs.GroupBox import Agrupacion  # noqa: E402
from libs.Utiles import icono  # noqa: E402
from libs.tema import aplicar_tema  # noqa: E402

aplicar_tema(app)


def total(valor, grande=False):
    """Un total. Derecha, grande, y no un campo de texto gris.

    El total es lo primero que el operador mira y lo unico que no puede
    editar. En la pantalla actual son cuatro `EntradaTexto` deshabilitados
    con etiquetas de 10 px, alineados a la izquierda: hay que leerlos como
    si fueran un formulario mas.
    """
    etiqueta = QLabel(valor)
    if grande:
        etiqueta.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #1F2933;")
    else:
        etiqueta.setStyleSheet(
            "font-size: 15px; font-weight: 500; color: #1F2933;")
    etiqueta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return etiqueta


def fila_total(texto, valor, grande=False):
    caja = QHBoxLayout()
    etiqueta = QLabel(texto)
    etiqueta.setStyleSheet("color: #52606D; font-size: 13px;")
    caja.addWidget(etiqueta)
    caja.addStretch(1)
    caja.addWidget(total(valor, grande))
    return caja


def campo(etiqueta_texto, widget):
    caja = QVBoxLayout()
    etiqueta = QLabel(etiqueta_texto)
    etiqueta.setStyleSheet("color: #52606D; font-size: 12px;")
    caja.addWidget(etiqueta)
    caja.addWidget(widget)
    return caja


def entrada(placeholder, ancho=0):
    from libs.EntradaTexto import EntradaTexto
    campo_ = EntradaTexto(placeholderText=placeholder)
    if ancho:
        campo_.setFixedWidth(ancho)
    return campo_


def combo(items, ancho=0):
    from PyQt5.QtWidgets import QComboBox
    caja = QComboBox()
    caja.addItems(items)
    if ancho:
        caja.setFixedWidth(ancho)
    return caja


def fecha(valor="04/10/2026"):
    f = Fecha()
    f.setFecha()
    return f


def construir(autorizada=False):
    ventana = Formulario()
    ventana.setWindowTitle("Emisión de comprobante electrónico")
    raiz = QVBoxLayout(ventana)
    raiz.setContentsMargins(22, 16, 22, 16)
    raiz.setSpacing(14)

    # -- Cabecera: que esta haciendo y en que estado esta -------------------
    cabecera = QHBoxLayout()
    cabecera.addWidget(EtiquetaTitulo(texto="Nueva factura"))
    cabecera.addStretch(1)

    estado = QLabel()
    if autorizada:
        # El CAE no es un dato mas: es la prueba de que la factura vale. En la
        # pantalla actual es un grupo gris abajo a la izquierda, al lado del
        # boton de Emitir, y hay que ir a buscarlo.
        estado.setText("Autorizada")
        estado.setStyleSheet(
            "background-color: #E4F3E8; color: #1E7A45; border: 1px solid #7FC79B;"
            "border-radius: 11px; padding: 3px 12px; font-size: 12px;")
    else:
        estado.setText("Sin autorizar")
        estado.setStyleSheet(
            "background-color: #F0F4F9; color: #52606D; border: 1px solid #A9BACD;"
            "border-radius: 11px; padding: 3px 12px; font-size: 12px;")
    cabecera.addWidget(estado)
    raiz.addLayout(cabecera)

    # -- Cliente: arriba, con el nombre grande y los datos de Supporting ----
    grupoCliente = Agrupacion(titulo="Cliente")
    layCliente = QGridLayout(grupoCliente)
    layCliente.setVerticalSpacing(8)

    nombre = QLabel("Estación de Servicio Palermo")
    nombre.setStyleSheet("font-size: 17px; font-weight: 600; color: #1F2933;")
    layCliente.addWidget(nombre, 0, 0, 1, 4)

    layCliente.addLayout(campo("Código", entrada("1", 110)), 1, 0)
    layCliente.addLayout(campo("Domicilio", entrada("Av. Corrientes 1234, CABA")), 1, 1, 1, 2)
    layCliente.addLayout(campo("Documento", entrada("30-12345678-9", 180)), 1, 3)

    layCliente.addLayout(campo("Condición frente al IVA",
                              combo(["Consumidor final"])), 2, 0)
    layCliente.addLayout(campo("Forma de pago",
                              combo(["Contado", "Cuenta corriente", "30 días"])),
                        2, 1)
    layCliente.addWidget(Etiqueta(texto="Sin cuenta corriente asociada"), 2, 2, 1, 2)
    raiz.addWidget(grupoCliente)

    # -- Cuerpo en tres columnas -------------------------------------------
    cuerpo = QHBoxLayout()
    cuerpo.setSpacing(12)

    # Izquierda: el comprobante y las condiciones
    izquierda = QVBoxLayout()
    izquierda.setSpacing(12)

    grupoComprobante = Agrupacion(titulo="Comprobante")
    layComprobante = QGridLayout(grupoComprobante)
    layComprobante.addLayout(campo("Tipo", combo(["Factura A", "Factura B", "Factura C"])), 0, 0)
    layComprobante.addLayout(campo("Fecha", fecha()), 0, 1)
    izquierda.addWidget(grupoComprobante)

    grupoConcepto = Agrupacion(titulo="Concepto")
    layConcepto = QGridLayout(grupoConcepto)
    chkProductos = CheckBox(texto="Productos")
    chkServicios = CheckBox(texto="Servicios")
    chkProductos.setChecked(True)
    layConcepto.addWidget(chkProductos, 0, 0)
    layConcepto.addWidget(chkServicios, 0, 1)
    izquierda.addWidget(grupoConcepto)

    # Lo de Factura C queda escondido: solo se usa en un tipo de comprobante
    # y antes ocupaba media pantalla siempre.
    grupoPeriodo = Agrupacion(titulo="Período facturado  (solo Factura C)")
    layPeriodo = QGridLayout(grupoPeriodo)
    layPeriodo.addLayout(campo("Desde", fecha()), 0, 0)
    layPeriodo.addLayout(campo("Hasta", fecha()), 0, 1)
    layPeriodo.addLayout(campo("Vto. para el pago", fecha()), 1, 0, 1, 2)
    izquierda.addWidget(grupoPeriodo)
    izquierda.addStretch(1)

    from libs.Paginas import Pagina, TabPagina
    contenedorIzq = QWidget()
    contenedorIzq.setLayout(izquierda)
    contenedorIzq.setFixedWidth(272)
    cuerpo.addWidget(contenedorIzq)

    # Centro: los articulos, que es donde esta la mayor parte del trabajo
    centro = QVBoxLayout()
    centro.setSpacing(10)

    pagina = Pagina()
    tabArticulos = TabPagina()
    layArt = QVBoxLayout(tabArticulos)
    layArt.setContentsMargins(10, 10, 10, 10)

    grilla = Grilla()
    grilla.enabled = True
    grilla.ArmaCabeceras(
        cabeceras=["Cant.", "Código", "Detalle", "Unitario", "IVA", "SubTotal"],
        formatos=["Cantidad", "Entero", "String", "Moneda", "Moneda", "Moneda"])
    grilla.AgregaItem(items=["2,00", "1", "GASOLINA NAFTA SUPER",
                             "500,00", "21,00", "1.000,00"])
    grilla.AgregaItem(items=["1,00", "1", "ACEITE 5W30 x 4L",
                             "18.000,00", "21,00", "18.000,00"])
    grilla.AgregaItem(items=["3,00", "1", "SERVICIO DE LAVADO",
                             "3.500,00", "21,00", "10.500,00"])
    layArt.addWidget(grilla)

    layBotonesArt = QHBoxLayout()
    btnAgrega = Boton(texto="Agregar línea", imagen=icono('nuevo'), autodefault=False)
    layBotonesArt.addWidget(btnAgrega)
    layBotonesArt.addStretch(1)
    btnBorrar = Boton(texto="Quitar línea", imagen=icono('borrar'), autodefault=False)
    layBotonesArt.addWidget(btnBorrar)
    layArt.addLayout(layBotonesArt)
    pagina.addTab(tabArticulos, "Artículos")

    for nombre_pestana in ("Alicuotas de IVA", "Otros tributos", "Observaciones"):
        pestana = TabPagina()
        lay = QVBoxLayout(pestana)
        lay.addWidget(Etiqueta(texto="Sin ítems."))
        lay.addStretch(1)
        pagina.addTab(pestana, nombre_pestana)
    centro.addWidget(pagina)
    cuerpo.addLayout(centro, 1)

    # Derecha: los totales, siempre a la vista y en la misma columna
    derecha = QVBoxLayout()
    derecha.setSpacing(8)

    separador = QLabel()
    separador.setFrameShape(QLabel.HLine)
    separador.setStyleSheet("color: #C8D2DE;")
    derecha.addWidget(separador)
    derecha.addSpacing(6)

    derecha.addLayout(fila_total("Subtotal", "29.500,00"))
    derecha.addLayout(fila_total("Otros tributos", "0,00"))
    derecha.addLayout(fila_total("IVA", "6.195,00"))
    derecha.addSpacing(8)

    # La linea antes del total: sin ella, el total es un numero mas de los
    # cuatro y hay que ir a buscarlo con la vista.
    separadorTotal = QLabel()
    separadorTotal.setFrameShape(QLabel.HLine)
    separadorTotal.setStyleSheet("color: #1F2933;")
    derecha.addWidget(separadorTotal)

    derecha.addLayout(fila_total("Total", "$ 35.695,00", grande=True))

    derecha.addSpacing(10)
    etiquetaCae = QLabel("Autorización")
    etiquetaCae.setStyleSheet("color: #52606D; font-size: 12px;")
    derecha.addWidget(etiquetaCae)

    if autorizada:
        # Autorizado: el CAE, el numero y el vencimiento van juntos y arriba,
        # con el boton de imprimir al lado. En la pantalla actual el CAE es un
        # campo de texto deshabilitado dentro de un grupo que parece de los
        # muchos.
        cajaCae = QVBoxLayout()
        numero = QLabel("Factura A 0001-00002345")
        numero.setStyleSheet("font-size: 14px; font-weight: 600; color: #1F2933;")
        cajaCae.addWidget(numero)
        codigo = QLabel("CAE  7501  2345  6789")
        codigo.setStyleSheet("font-size: 13px; color: #1E7A45;"
                             "font-family: Consolas, monospace;")
        cajaCae.addWidget(codigo)
        vencimiento = QLabel("Vence el 14/10/2026")
        vencimiento.setStyleSheet("font-size: 12px; color: #52606D;")
        cajaCae.addWidget(vencimiento)
        derecha.addLayout(cajaCae)
    else:
        derecha.addWidget(Etiqueta(texto="Se solicita al emitir"))

    derecha.addStretch(1)

    if autorizada:
        btnAccion = Boton(texto="Imprimir", imagen=icono('imprimir'),
                          autodefault=False, estilo='primario')
        btnAccion.setMinimumHeight(44)
        derecha.addWidget(btnAccion)
        derecha.addWidget(Boton(texto="Nueva factura", imagen=icono('nueva-venta'),
                                autodefault=False))
    else:
        btnAccion = Boton(texto="Emitir factura", imagen=icono('guardar'),
                          autodefault=False, estilo='primario')
        btnAccion.setMinimumHeight(44)
        derecha.addWidget(btnAccion)
    derecha.addWidget(BotonCerrarFormulario(autodefault=False))
    contenedorDer = QWidget()
    contenedorDer.setLayout(derecha)
    contenedorDer.setFixedWidth(280)
    cuerpo.addWidget(contenedorDer)

    raiz.addLayout(cuerpo, 1)
    return ventana


for autorizada, nombre in ((False, "propuesta_emision"),
                           (True, "propuesta_emision_autorizada")):
    ventana = construir(autorizada=autorizada)
    ventana.resize(1400, 860)
    ventana.show()
    ventana.raise_()
    for _ in range(12):
        app.processEvents()
    ruta = os.path.join(SALIDA, nombre + ".png")
    ventana.grab().save(ruta)
    print("{}: {}x{}".format(ruta, ventana.width(), ventana.height()))
    ventana.close()
