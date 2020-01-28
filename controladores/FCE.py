# coding=utf-8
import logging

from libs import Ventanas
from libs.Utiles import LeerIni, ubicacion_sistema, inicializar_y_capturar_excepciones
from pyafipws.wsaa import WSAA
from pyafipws.wsfecred import WSFECred


class WsFECred(WSFECred):

    def __init__(self):
        WSFECred.__init__(self)

    #crea ticket de acceso verificando que ya no tenga abierto uno
    def CreaTA(self):
        ta = self.Autenticar()
        return ta

    @inicializar_y_capturar_excepciones
    def Autenticar(self, *args, **kwargs):
        if 'service' in kwargs:
            service = kwargs['service']
        else:
            service = 'wsfecred'
        wsaa = WSAA()
        archivo = ubicacion_sistema() + service + '-ta.xml'
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
            tra = wsaa.CreateTRA(service=service)

            #Generar el mensaje firmado(CMS)
            if LeerIni(clave='homo') == 'S':#homologacion
                cms = wsaa.SignTRA(tra, LeerIni(clave="cert_homo", key="WSAA"),
                               LeerIni(clave="privatekey_homo", key="WSAA"))
                ok = wsaa.Conectar("", LeerIni(clave='url_homo', key='WSAA'))  # Homologación
            else:
                cms = wsaa.SignTRA(tra, LeerIni(clave="cert_prod", key="WSAA"),
                               LeerIni(clave="privatekey_prod", key="WSAA"))
                ok = wsaa.Conectar("", LeerIni(clave='url_prod', key='WSAA')) #Produccion

            #Llamar al web service para autenticar
            ta = wsaa.LoginCMS(cms)

            #Grabo el ticket de acceso para poder reutilizarlo
            file = open(archivo, 'w')
            logging.debug('Ticket de acceso {}'.format(ta))
            file.write(ta)
            file.close()
        # devuelvo el ticket de acceso
        #print "Ticket acceso: {}".format(ta)
        return ta

    def ConsultarMontoObligado(self, cuit_consultada, cuit_emisor):
        if isinstance(cuit_emisor, bytes):
            self.Cuit = cuit_emisor.decode()
        else:
            self.Cuit = cuit_emisor
        cuit_consultada = cuit_consultada.replace('-', '')
        if LeerIni(clave='homo') == 'S':
            self.Conectar("")
        else:
            self.Conectar("", wsdl=self.WSDL)
        tafce = self.Autenticar()
        self.SetTicketAcceso(tafce)
        minimo = self.ConsultarMontoObligadoRecepcion(cuit_consultada)
        if self.ErrMsg:
            Ventanas.showAlert("Sistema", self.ErrMsg)
        return self.Resultado == 'S', minimo