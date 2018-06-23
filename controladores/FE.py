# coding=utf-8
import logging

from libs.Utiles import LeerIni, ubicacion_sistema
from pyafipws.wsaa import WSAA
from pyafipws.wsfev1 import WSFEv1


class FEv1(WSFEv1):

    wsfev1 = None
    PRODUCTOYSERVICIOS = 3
    SERVICIOS = 2
    PRODUCTOS = 1
    ID_IMP_PCIAL = 2
    TASA_IVA = {
        "0":3,
        "10.5":4,
        "21.00":5,
        "27.00": 6
    }

    def __init__(self):
        WSFEv1.__init__(self)

    #crea ticket de acceso verificando que ya no tenga abierto uno
    def CreaTA(self):
        ta = self.Autenticar()
        return ta

    def UltimoComprobante(self, tipo=1, ptovta=1):
        wsdl = self.WSDL
        cache = None
        proxy = ""
        wrapper = ""  # "pycurl"
        cacert = True  # geotrust.crt"
        ok = self.Conectar(cache, wsdl, proxy, wrapper, cacert)

        if not ok:
            raise RuntimeError(self.Excepcion)

        ta = self.Autenticar()
        self.SetTicketAcceso(ta)
        self.Cuit = LeerIni(clave="CUIT", key='WSFEv1')
        ultimo = self.CompUltimoAutorizado(tipo_cbte=tipo, punto_vta=ptovta)
        return ultimo

    def Autenticar(self):
        wsaa = WSAA()
        archivo = ubicacion_sistema() + 'ta.xml'
        try:
            file = open(archivo, "r")
            ta = file.read()
            file.close()
        except:
            ta = ''

        if ta == '': #si no existe el archivo se solicita un ticket
            solicitar = True
        else:
            ok = wsaa.AnalizarXml(ta)
            expiracion = wsaa.ObtenerTagXml("expirationTime")
            solicitar = wsaa.Expirado(expiracion) #si el ticket esta vencido se solicita uno nuevo
            logging.info("Fecha expiracion de ticket acceso {}".format(expiracion))

        if solicitar:
            #Generar un Ticket de Requerimiento de Acceso(TRA)
            tra = wsaa.CreateTRA()

            #Generar el mensaje firmado(CMS)
            cms = wsaa.SignTRA(tra, LeerIni(clave="CERT", key="WSAA"),
                               LeerIni(clave="PRIVATEKEY", key="WSAA"))
            #Produccion usar: ta = WSAA.CallWSAA(cms, "https://wsaa.afip.gov.ar/ws/services/LoginCms") & & Producción
            ok = wsaa.Conectar("", LeerIni(clave='URL', key='WSAA')) #Homologación

            #Llamar al web service para autenticar
            ta = wsaa.LoginCMS(cms)

            #Grabo el ticket de acceso para poder reutilizarlo
            file = open(archivo, 'w')
            file.write(ta)
            file.close()
        # devuelvo el ticket de acceso
        return ta
