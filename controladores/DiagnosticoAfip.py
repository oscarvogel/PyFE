# coding=utf-8
import os
from dataclasses import dataclass
from os.path import abspath

from controladores.FE import FEv1
from libs.Utiles import LeerIni


@dataclass
class PasoDiagnosticoAfip:
    nombre: str
    ok: bool
    detalle: str


# Que hacer segun donde se haya cortado. Sin esto el diagnostico dice QUE pasa
# pero no QUE hacer, que es lo que el usuario necesita a la hora de emitir.
AYUDA_POR_PASO = {
    "Configuracion": (
        "Revise Configuracion > Parametros: la seccion [WSAA] tiene que tener "
        "el certificado y la clave privada del modo que esta usando "
        "(homologacion o produccion), y el CUIT del emisor en [WSFEv1]. "
        "Los certificados se generan desde Configuracion > Certificados."
    ),
    "WSAA": (
        "Es la autenticacion. Casi siempre es el certificado: puede estar "
        "vencido, o no corresponde al CUIT cargado en [WSFEv1]. Regenere el "
        "certificado desde Configuracion > Certificados y verifique el CUIT."
    ),
    "WSFE conexion": (
        "Se autentico bien pero no se pudo hablar con el servicio de "
        "facturacion. Revise la conexion a internet de esta maquina: si hay "
        "proxy o firewall, tiene que dejar salir a servicios1.afip.gov.ar. "
        "En produccion tambien verifique [WSFEv1] url_prod."
    ),
    "WSFE Dummy": (
        "Se conecto pero AFIP no respondio bien. Suele ser transitorio: "
        "reintente en unos minutos. Si sigue igual, es un problema del lado "
        "de ARCA y conviene intentarlo mas tarde."
    ),
}

# Las etapas, en el orden en que se recorren. Las llama ejecutar() una por
# una, asi que la lista tiene que seguir manteniendose al ritmo.
ETAPAS_DIAGNOSTICO = [
    "Revisando la configuración",
    "Autenticando con ARCA",
    "Conectando al servicio de facturación",
    "Pidiendo un comprobante de prueba",
]


class DiagnosticoAfip:
    def __init__(self, fe_factory=FEv1, leer_ini=LeerIni):
        self.fe_factory = fe_factory
        self.leer_ini = leer_ini

    def ejecutar(self, al_avanzar=None):
        """Corre el diagnostico paso a paso.

        `al_avanzar` se llama con el nombre de cada etapa ANTES de ejecutarla,
        para que la barra de progreso diga la verdad: contra ARCA esto tarda, y
        ver en que etapa se quedo es justo la informacion que se busca.
        """
        def avisar(nombre):
            if al_avanzar:
                al_avanzar(nombre)

        pasos = []
        modo = "Homologacion" if self.leer_ini(clave="homo") == "S" else "Produccion"
        cuit = self.leer_ini(clave="cuit", key="WSFEv1")

        avisar(ETAPAS_DIAGNOSTICO[0])
        pasos.append(self._validar_configuracion(modo, cuit))
        if not pasos[-1].ok:
            return pasos

        fe = self.fe_factory()
        fe.LanzarExcepciones = True

        avisar(ETAPAS_DIAGNOSTICO[1])
        try:
            ta = fe.Autenticar()
            if not ta:
                pasos.append(PasoDiagnosticoAfip("WSAA", False, "No devolvio ticket de acceso."))
                return pasos
            fe.SetTicketAcceso(ta_string=ta)
            fe.Cuit = cuit
            pasos.append(PasoDiagnosticoAfip("WSAA", True, "Ticket de acceso valido para wsfe."))
        except Exception as exc:
            pasos.append(PasoDiagnosticoAfip("WSAA", False, self._limpiar_error(exc)))
            return pasos

        avisar(ETAPAS_DIAGNOSTICO[2])
        try:
            ok = self._conectar_wsfe(fe)
            if not ok:
                pasos.append(PasoDiagnosticoAfip("WSFE conexion", False, self._error_fe(fe)))
                return pasos
            pasos.append(PasoDiagnosticoAfip("WSFE conexion", True, "Conexion establecida."))
        except Exception as exc:
            pasos.append(PasoDiagnosticoAfip("WSFE conexion", False, self._limpiar_error(exc)))
            return pasos

        avisar(ETAPAS_DIAGNOSTICO[3])
        try:
            fe.Dummy()
            detalle = "AppServer: {} | DbServer: {} | AuthServer: {}".format(
                getattr(fe, "AppServerStatus", ""),
                getattr(fe, "DbServerStatus", ""),
                getattr(fe, "AuthServerStatus", ""),
            )
            pasos.append(PasoDiagnosticoAfip("WSFE Dummy", True, detalle))
        except Exception as exc:
            pasos.append(PasoDiagnosticoAfip("WSFE Dummy", False, self._limpiar_error(exc)))

        return pasos

    def formatear(self, pasos):
        lineas = []
        for paso in pasos:
            estado = "OK" if paso.ok else "ERROR"
            lineas.append("{}: {}\n{}".format(paso.nombre, estado, paso.detalle))

        if pasos and all(paso.ok for paso in pasos):
            lineas.append("Resultado: AFIP/ARCA esta respondiendo correctamente.")
        else:
            lineas.append("Resultado: hay un paso marcado con ERROR. "
                          "Mire 'Que hacer' para continuar.")

        return "\n\n".join(lineas)

    def que_hacer(self, pasos):
        """El consejo del primer paso que fallo. Vacio si todo anda bien."""
        for paso in pasos:
            if not paso.ok:
                return AYUDA_POR_PASO.get(
                    paso.nombre,
                    "Revise el detalle del paso marcado con ERROR.")
        return ""

    def titulo(self, pasos):
        """Titulo del aviso: si todo bien es un informe, si no es un error."""
        if pasos and all(paso.ok for paso in pasos):
            return "Conexión con ARCA"
        return "No se pudo conectar con ARCA"

    def _validar_configuracion(self, modo, cuit):
        faltantes = []
        if not cuit:
            faltantes.append("WSFEv1.cuit")

        if modo == "Homologacion":
            cert = self.leer_ini(clave="cert_homo", key="WSAA")
            key = self.leer_ini(clave="privatekey_homo", key="WSAA")
            url_wsaa = self.leer_ini(clave="url_homo", key="WSAA")
        else:
            cert = self.leer_ini(clave="cert_prod", key="WSAA")
            key = self.leer_ini(clave="privatekey_prod", key="WSAA")
            url_wsaa = self.leer_ini(clave="url_prod", key="WSAA")

        url_wsfe = self.leer_ini(clave="url_prod", key="WSFEv1") if modo == "Produccion" else "WSDL homologacion pyafipws"

        if not cert:
            faltantes.append("WSAA.cert_{}".format("homo" if modo == "Homologacion" else "prod"))
        elif not os.path.exists(abspath(cert)):
            faltantes.append("certificado no encontrado: {}".format(abspath(cert)))

        if not key:
            faltantes.append("WSAA.privatekey_{}".format("homo" if modo == "Homologacion" else "prod"))
        elif not os.path.exists(abspath(key)):
            faltantes.append("clave privada no encontrada: {}".format(abspath(key)))

        if not url_wsaa:
            faltantes.append("WSAA.url_{}".format("homo" if modo == "Homologacion" else "prod"))

        if modo == "Produccion" and not url_wsfe:
            faltantes.append("WSFEv1.url_prod")

        if faltantes:
            return PasoDiagnosticoAfip("Configuracion", False, "Faltan datos: {}".format(", ".join(faltantes)))

        return PasoDiagnosticoAfip(
            "Configuracion",
            True,
            "Modo: {} | CUIT: {} | WSAA: {} | WSFE: {}".format(modo, cuit, url_wsaa, url_wsfe),
        )

    def _conectar_wsfe(self, fe):
        if self.leer_ini(clave="homo") == "S":
            return fe.Conectar("")
        return fe.Conectar(
            "",
            self.leer_ini(clave="url_prod", key="WSFEv1"),
            cacert=None,
        )

    def _leer_cacert(self, seccion):
        cacert = self.leer_ini(clave="cacert", key=seccion)
        return cacert.strip() if cacert and cacert.strip() else None

    def _error_fe(self, fe):
        return (
            getattr(fe, "ErrMsg", "")
            or getattr(fe, "Excepcion", "")
            or getattr(fe, "Traceback", "")
            or "No se pudo conectar al servicio."
        )

    def _limpiar_error(self, exc):
        return str(exc).strip() or exc.__class__.__name__
