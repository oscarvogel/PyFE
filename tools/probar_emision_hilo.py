# coding=utf-8
"""Emite una factura de homologacion pasando por el QThread de verdad.

Por que esto y no los tests
---------------------------
Los tests comprueban que el codigo este bien, pero un QThread se rompe de
formas que un test no ve: una senal que no llega, un hilo que muere sin
avisar, un widget tocado desde el hilo equivocado. Lo unico que lo demuestra es
emitir contra ARCA de verdad y ver que vuelve el CAE.

Que NO prueba
------------
GrabaFE: aca se deja de lado a proposito, para aislar el hilo de la base.
Grabar la factura se prueba en la app, no aca.
"""
from __future__ import print_function

import datetime
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTORNO = os.path.join(RAIZ, "_prueba_facturacion")

if not os.path.isdir(ENTORNO):
    print("El entorno de prueba no existe. Corré primero:")
    print("    python tools/armar_prueba_facturacion.py")
    sys.exit(1)

os.chdir(ENTORNO)
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
sys.argv = [sys.argv[0]]

# QApplication con ventana de verdad: el hilo emite senales que Qt encola al
# hilo principal, y sin una instancia no hay a quien encolarlas. offscreen
# alcanza, porque no se dibuja nada.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication, QWidget  # noqa: E402
app = QApplication.instance() or QApplication(sys.argv)

from libs.Utiles import LeerIni  # noqa: E402
from controladores.Facturas import FacturaController  # noqa: E402


class Pantalla(QWidget):
    """Lo minimo que _emitir_en_hilo toca de la vista.

    Es un QWidget de verdad porque en la app lo es, y el worker se crea con la
    vista como padre: asi el hilo muere con la ventana y no queda vivo
    emitiendo sobre una pantalla que ya no existe.
    """

    def Cerrar(self):
        self.close()


if LeerIni("homo") != "S":
    print("CORTANDO: esto solo emite en el entorno de prueba (homo = S).")
    sys.exit(1)

controlador = object.__new__(FacturaController)
controlador.view = Pantalla()
controlador._progreso = None
controlador._hilo = None
controlador._worker = None
controlador._error_afip = ""
controlador.Excepcion = ""
controlador.Traceback = ""
controlador.SilenciarError = True
controlador.GrabaFE = lambda: True


# crear_factura_wsfe lee la condicion de IVA del receptor desde el cliente.
class TipoResp(object):
    idtiporesp = 3
    condicion_iva_receptor_id = 5


controlador.cliente = type("Cliente", (), {"tiporesp": TipoResp()})()

controlador.view.lineditCAE = type("C", (), {
    "setText": lambda self, v: setattr(self, "texto", v),
    "text": lambda self: getattr(self, "texto", "")})()
controlador.view.lineEditResultado = type("C", (), {
    "setText": lambda self, v: setattr(self, "texto", v)})()
controlador.view.fechaVencCAE = type("F", (), {
    "setFecha": lambda self, f, format=None: setattr(self, "fecha", f)})()

# Los mismos datos que usaria la pantalla de emision, pero como datos planos.
# _datos_emision() no se llama porque necesita la pantalla completa.
total = "1210.00"
neto = "1000.00"
datos = {
    "concepto_productos": True,
    "concepto_servicios": False,
    "es_consumidor_final": True,
    "documento": "11111111",
    "tipo_doc": 96,
    "tipo_cbte": 6,                       # Factura B
    "punto_vta": 1,
    "cbt_desde": 1,                       # lo recalcula _autorizar
    "imp_total": total,
    "imp_neto": neto,
    "imp_iva": "210.00",
    "imp_trib": "0.00",
    "imp_tot_conc": "0.00",
    "imp_op_ex": "0.00",
    "fecha_cbte": datetime.date.today().strftime("%Y%m%d"),
    "moneda_id": "PES",
    "moneda_ctz": "1.000",
    "es_ri": True,
    "netos": {"21.0": 1000.00},
    "condicion_iva_receptor": 5,
    "asociado_pto": "",
    "asociado_nro": "",
    "tiene_asociado": False,
    "cbu": "",
    "alias": "",
    "percepcion_detalle": "",
    "percepcion_alicuota": 0,
    "cuit": LeerIni(clave="cuit", key="WSFEv1"),
    "concepto": "PRODUCTOS",
    "fecha_serv_desde": "",
    "fecha_serv_hasta": "",
    "fecha_venc_pago": "",
}

print("=== EMISION POR HILO (QThread) ===")
print("CUIT      : {}".format(datos["cuit"]))
print("comprobante: {}  punto de venta: {}".format(datos["tipo_cbte"],
                                                   datos["punto_vta"]))
print("total     : {}".format(datos["imp_total"]))
print("")

print("")
print("=== DONDE SE EJECUTO EL CODIGO ===")
hilos = {}
_controlador_autorizar = controlador._autorizar


def _autorizar_espia(datos, avisar=None):
    """Anota en que hilo se ejecuto _autorizar."""
    import threading
    hilos["autorizar"] = threading.current_thread().ident
    return _controlador_autorizar(datos, avisar)


controlador._autorizar = _autorizar_espia
import threading  # noqa: E402
hilos["principal"] = threading.current_thread().ident

inicio = time.time()
controlador._emitir_en_hilo(datos)
segundos = time.time() - inicio

print("hilo principal        : {}".format(hilos["principal"]))
print("hilo de _autorizar()  : {}".format(hilos.get("autorizar")))
if hilos.get("autorizar") == hilos["principal"]:
    print("")
    print("MAL: _autorizar corrio en el hilo principal. La ventana se sigue")
    print("congelando aunque el codigo parezca enhebrado.")
    sys.exit(1)
print("distintos             : OK, la emision no bloquea la ventana")

print("")
print("tardo {:.1f} segundos".format(segundos))
print("hilo terminado: {}".format(controlador._hilo is None))
print("CAE en pantalla: {}".format(controlador.view.lineditCAE.text()))
print("resultado      : {}".format(getattr(controlador.view.lineEditResultado,
                                            "texto", "")))
print("vence CAE      : {}".format(getattr(controlador.view.fechaVencCAE,
                                            "fecha", "")))

if controlador.view.lineditCAE.text():
    print("")
    print("AUTORIZADA DESDE EL HILO. La ventana no se congelo y el CAE")
    print("volvio correctamente al hilo principal.")
    sys.exit(0)

print("")
print("NO se obtuvo CAE. Error guardado: {}".format(controlador._error_afip))
sys.exit(1)
