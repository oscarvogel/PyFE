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


def test_el_decorador_muestra_el_error_y_lo_reporta(monkeypatch):
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    import libs.Utiles as utiles
    from libs import Ventanas

    _FalsoEmail.enviados = []
    monkeypatch.setattr(utiles, "PyEmail", _FalsoEmail)
    monkeypatch.setattr(utiles, "LeerIni", lambda *a, **k: "N")

    mostrados = []
    monkeypatch.setattr(Ventanas, "showAlert",
                        lambda t, m: mostrados.append((t, m)))

    _controlador_que_falla()

    assert mostrados, "sin silenciar tiene que avisar"
    assert _FalsoEmail.enviados, "y ademas reportar a soporte"


def test_silenciar_el_error_apaga_el_dialogo_pero_no_el_reporte(monkeypatch):
    """Esto es lo que hace la emision de una factura.

    El usuario no puede ver el mismo fallo dos veces, pero si el reporte
    automatico dejara de salir, una falla fiscal se quedaria sin registrar y
    eso seria peor que el dialogo duplicado.
    """
    monkeypatch.setattr(sys, "argv", [sys.argv[0]])
    import libs.Utiles as utiles
    from libs import Ventanas

    _FalsoEmail.enviados = []
    monkeypatch.setattr(utiles, "PyEmail", _FalsoEmail)
    monkeypatch.setattr(utiles, "LeerIni", lambda *a, **k: "N")

    mostrados = []
    monkeypatch.setattr(Ventanas, "showAlert",
                        lambda t, m: mostrados.append((t, m)))

    _controlador_que_falla(SilenciarError=True)

    assert mostrados == [], "con SilenciarError no puede haber dialogo"
    assert _FalsoEmail.enviados, \
        "el reporte a soporte no se puede apagar: es el unico registro de la falla"
