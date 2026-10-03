"""La capa de avisos, confirmaciones y progreso.

Dos cosas que se prueban aca:

1. Que un dialogo sin interfaz NO reviente el proceso. Armar un QMessageBox
   sin QApplication tira 0xC0000409 y se lleva el proceso entero sin dejar
   traceback, asi que los tests y las herramientas de linea de comandos
   morian sin que se viera por que.
2. Que los errores de emision digan QUE HACER y no solo el codigo de ARCA.
"""
import sys

import pytest

from libs import Ventanas
from controladores.DiagnosticoAfip import (DiagnosticoAfip,
                                           ETAPAS_DIAGNOSTICO,
                                           PasoDiagnosticoAfip)


# -- Dialogos sin interfaz ---------------------------------------------------

@pytest.fixture
def sin_interfaz(monkeypatch):
    """Fuerza el escenario sin QApplication.

    No se puede confiar en que todavia no haya una: los tests corren en un solo
    proceso y otro archivo ya puede haber creado la aplicacion. Ademas, si la
    hay, showConfirmation abriria un modal de verdad y el proceso muere.
    """
    from PyQt5.QtWidgets import QApplication
    monkeypatch.setattr(QApplication, "instance", staticmethod(lambda: None))
    return True


def test_hay_interfaz_es_falso_sin_qapplication(sin_interfaz):
    assert Ventanas.hay_interfaz() is False


def test_show_confirmation_sin_interfaz_devuelve_no(sin_interfaz):
    """Sin ventana no se puede preguntar, y sin respuesta no se autoriza."""
    assert Ventanas.showConfirmation("Emitir", "¿Emitir?") is False


def test_show_alert_y_show_error_sin_interfaz_no_revientan(sin_interfaz, capsys):
    Ventanas.showAlert("Aviso", "algo paso")
    Ventanas.showError("Error", "algo fallo",
                       que_hacer="revisar", detalle="detalle tecnico")

    salida = capsys.readouterr().err
    assert "algo paso" in salida
    assert "algo fallo" in salida
    assert "revisar" in salida, "el que hacer no se puede perder"
    assert "detalle tecnico" in salida


def test_progreso_sin_interfaz_anota_las_etapas_y_no_falla(sin_interfaz):
    etapas = []

    with Ventanas.Progreso("Probando", ETAPAS_DIAGNOSTICO) as barra:
        for etapa in ETAPAS_DIAGNOSTICO:
            barra.avanzar(etapa)
            etapas.append(barra.actual)
        barra.refrescar()

    assert etapas == ETAPAS_DIAGNOSTICO


# -- Diagnostico: que hacer, no solo que pasa -------------------------------

def _diagnostico_con_pasos(*pasos):
    diagnostico = DiagnosticoAfip.__new__(DiagnosticoAfip)
    diagnostico.leer_ini = lambda *a, **k: ""
    diagnostico.fe_factory = lambda: None
    return diagnostico, list(pasos)


def test_el_diagnostico_arranca_por_las_etapas_declaradas(monkeypatch):
    """La barra de progreso tiene que decir la verdad, no animar."""
    diagnostico, _ = _diagnostico_con_pasos()
    vistas = []

    class Paso:
        ok = True
        nombre = "Configuracion"
        detalle = "ok"

    monkeypatch.setattr(diagnostico, "_validar_configuracion",
                        lambda modo, cuit: Paso())

    # Con la configuracion bien, sigue al WSAA y se frena ahi.
    class Fe:
        LanzarExcepciones = True

        def Autenticar(self):
            return None

    diagnostico.fe_factory = lambda: Fe()

    diagnostico.ejecutar(al_avanzar=vistas.append)

    assert vistas == [ETAPAS_DIAGNOSTICO[0], ETAPAS_DIAGNOSTICO[1]]


def test_un_error_diagnostico_dice_que_hacer():
    diagnostico, pasos = _diagnostico_con_pasos(
        PasoDiagnosticoAfip("Configuracion", False, "Faltan datos: cert"))

    consejo = diagnostico.que_hacer(pasos)
    assert "Certificados" in consejo
    assert diagnostico.titulo(pasos) == "No se pudo conectar con ARCA"


def test_cada_paso_que_falla_tiene_su_consejo():
    """Un paso sin consejo propio al menos no devuelve texto vacio."""
    diagnostico, pasos = _diagnostico_con_pasos(
        PasoDiagnosticoAfip("WSAA", False, "cert vencido"))
    assert "certificado" in diagnostico.que_hacer(pasos).lower()

    diagnostico, pasos = _diagnostico_con_pasos(
        PasoDiagnosticoAfip("WSFE conexion", False, "no conecta"))
    assert "internet" in diagnostico.que_hacer(pasos).lower()

    diagnostico, pasos = _diagnostico_con_pasos(
        PasoDiagnosticoAfip("WSFE Dummy", False, "sin respuesta"))
    assert "reintente" in diagnostico.que_hacer(pasos).lower()


def test_si_todo_anda_bien_no_hay_que_hacer_que_dar():
    diagnostico, pasos = _diagnostico_con_pasos(
        PasoDiagnosticoAfip("Configuracion", True, "todo bien"),
        PasoDiagnosticoAfip("WSAA", True, "ok"),
    )
    assert diagnostico.que_hacer(pasos) == ""
    assert diagnostico.titulo(pasos) == "Conexión con ARCA"


def test_el_informe_de_diagnostico_apunta_a_que_hacer():
    diagnostico, pasos = _diagnostico_con_pasos(
        PasoDiagnosticoAfip("WSAA", False, "cert vencido"))
    texto = diagnostico.formatear(pasos)
    assert "ERROR" in texto
    assert "WSAA" in texto
    assert "Que hacer" in texto


# -- El decorador de excepciones y el dialogo que se lleva puesto -------------

class _FalsoEmail(object):
    enviados = []

    def __init__(self, *args, **kwargs):
        self.Excepcion = "sin conexion"
        self.Traceback = ""

    def Conectar(self, **kwargs):
        return True

    def Enviar(self, remitente, motivo, destinatario, mensaje):
        _FalsoEmail.enviados.append(motivo)
        return True


def _controlador_que_falla(**atributos):
    """Un objeto minimo con el decorador puesto.

    No se usa ControladorBase a proposito: el decorador solo lee
    `LanzarExcepciones` y `SilenciarError`, y traer la clase base entera al
    test mete widgets en una prueba que no necesita ninguna ventana.
    """
    from libs.Utiles import inicializar_y_capturar_excepciones

    @inicializar_y_capturar_excepciones
    def revienta(self, *args, **kwargs):
        raise ValueError("se rompio")

    # El decorador lee LanzarExcepciones sin default; ControladorBase lo define
    # y esta clase minima no, asi que va puesto aca.
    atributos.setdefault("LanzarExcepciones", False)
    clase = type("Ctrl", (object,), atributos)
    return revienta(clase())


# Valores de Parametros del sistema con los que el reporte queda habilitado.
PARAMETROS_SMTP = {
    "SERVER_SMTP": "smtp.de-ejemplo.com",
    "USUARIO_SMTP": "info@vogelconsultoria.com.ar",
    "CLAVE_SMTP": "la-clave",
    "PUERTO_SMTP": "465",
    "DESTINO_ERRORES": "info@vogelconsultoria.com.ar",
}


def _preparar_reporte(monkeypatch, con_clave=True):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    import libs.Utiles as utiles
    from libs import Ventanas

    _FalsoEmail.enviados = []
    monkeypatch.setattr(utiles, "PyEmail", _FalsoEmail)
    monkeypatch.setattr(utiles, "LeerIni", lambda *a, **k: "N")

    def parametros(nombre, defecto=""):
        if not con_clave and nombre == "CLAVE_SMTP":
            return ""
        return PARAMETROS_SMTP.get(nombre, defecto)

    monkeypatch.setattr(utiles, "_parametro_smtp", parametros)

    mostrados = []
    monkeypatch.setattr(Ventanas, "showAlert",
                        lambda t, m: mostrados.append((t, m)))
    errores = []
    import logging
    monkeypatch.setattr(logging, "error", lambda *a, **k: errores.append(a))
    return mostrados, errores


def test_el_decorador_muestra_el_error_y_lo_reporta(monkeypatch):
    mostrados, errores = _preparar_reporte(monkeypatch)

    _controlador_que_falla()

    assert mostrados, "sin silenciar tiene que avisar"
    assert _FalsoEmail.enviados, "y ademas reportar a soporte"


def test_silenciar_el_error_apaga_el_dialogo_pero_no_el_reporte(monkeypatch):
    """Esto es lo que hace la emision de una factura.

    El usuario no puede ver el mismo fallo dos veces, pero si el reporte
    automatico dejara de salir, una falla fiscal se quedaria sin registrar y
    eso seria peor que el dialogo duplicado.
    """
    mostrados, errores = _preparar_reporte(monkeypatch)

    _controlador_que_falla(SilenciarError=True)

    assert mostrados == [], "con SilenciarError no puede haber dialogo"
    assert _FalsoEmail.enviados, \
        "el reporte a soporte no se puede apagar: es el unico registro de la falla"


def test_sin_clave_no_se_intenta_conectar(monkeypatch):
    """Sin clave, conectar revienta con un error de socket que no dice nada.

    Y este codigo corre justo cuando algo ya fallo: el traceback original ya
    quedo en el log, que es el registro que importa.
    """
    mostrados, errores = _preparar_reporte(monkeypatch, con_clave=False)

    _controlador_que_falla()

    assert _FalsoEmail.enviados == [], "no se puede mandar sin configuracion"
    assert errores, "pero tiene que quedar anotado que falta configurarlo"
    # El mensaje va ya armado a proposito: este log lo lee una persona, y no
    # depende de que el handler de logging resuelva los argumentos.
    unido = " ".join(str(args[0]) for args in errores)
    assert "CLAVE_SMTP" in unido, \
        "el log tiene que decir QUE falta, no solo que algo fallo"


def test_el_reporte_no_da_la_direccion_anterior(monkeypatch):
    """El reporte automatico de los clientes no puede seguir yendo a otro."""
    mostrados, errores = _preparar_reporte(monkeypatch)
    from libs import Constantes

    assert "servinlgsm" not in Constantes.USUARIO_SMTP.lower()
    assert "servinlgsm" not in Constantes.SERVER_SMTP.lower()
    assert "vogelconsultoria" in Constantes.USUARIO_SMTP.lower()
    # Y el servidor no se inventa: vacio hasta que el administrador lo ponga.
    assert Constantes.SERVER_SMTP == "", \
        "un host inventado hace fallar el reporte, que es el peor momento"
