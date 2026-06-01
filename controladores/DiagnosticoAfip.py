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


class DiagnosticoAfip:
    def __init__(self, fe_factory=FEv1, leer_ini=LeerIni):
        self.fe_factory = fe_factory
        self.leer_ini = leer_ini

    def ejecutar(self):
        pasos = []
        modo = "Homologacion" if self.leer_ini(clave="homo") == "S" else "Produccion"
        cuit = self.leer_ini(clave="cuit", key="WSFEv1")

        pasos.append(self._validar_configuracion(modo, cuit))
        if not pasos[-1].ok:
            return pasos

        fe = self.fe_factory()
        fe.LanzarExcepciones = True

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

        try:
            ok = self._conectar_wsfe(fe)
            if not ok:
                pasos.append(PasoDiagnosticoAfip("WSFE conexion", False, self._error_fe(fe)))
                return pasos
            pasos.append(PasoDiagnosticoAfip("WSFE conexion", True, "Conexion establecida."))
        except Exception as exc:
            pasos.append(PasoDiagnosticoAfip("WSFE conexion", False, self._limpiar_error(exc)))
            return pasos

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
            lineas.append("Resultado: revisar el paso marcado con ERROR antes de emitir.")

        return "\n\n".join(lineas)

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
