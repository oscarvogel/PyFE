# coding=utf-8
import logging

from libs import Ventanas
from libs.Utiles import LeerIni, ubicacion_sistema, inicializar_y_capturar_excepciones
from pyafipws.wsaa import WSAA
from pyafipws.wscdc import WSCDC
from pyafipws.wsfev1 import WSFEv1


class FEv1(WSFEv1):

    wsfev1 = None
    PRODUCTOYSERVICIOS = 3
    SERVICIOS = 2
    PRODUCTOS = 1
    ID_IMP_PCIAL = 2
    TASA_IVA = {
        "0.0": 3,
        "10.5": 4,
        "21.0": 5,
        "27.0": 6
    }

    def __init__(self):
        WSFEv1.__init__(self)
        if LeerIni(clave='homo') != 'S': #si no es homologacion traigo la url de produccion
            self.WSDL = LeerIni(clave='url_prod', key='WSFEv1')

    #crea ticket de acceso verificando que ya no tenga abierto uno
    def CreaTA(self):
        ta = self.Autenticar()
        return ta

    @inicializar_y_capturar_excepciones
    def UltimoComprobante(self, tipo=1, ptovta=1):
        wsdl = self.WSDL
        print("WSDL {}".format(wsdl))
        cache = None
        proxy = ""
        wrapper = ""  # "pycurl"
        #cacert = True  # geotrust.crt"
        cacert = LeerIni('iniciosistema') + LeerIni(clave='cacert', key='WSFEv1')
        ok = self.Conectar(cache, wsdl, proxy, wrapper, cacert)

        if not ok:
            raise RuntimeError(self.Excepcion)

        ta = self.Autenticar()
        self.SetTicketAcceso(ta)
        self.Cuit = LeerIni(clave="cuit", key='WSFEv1')
        ultimo = self.CompUltimoAutorizado(tipo_cbte=tipo, punto_vta=ptovta)
        return ultimo

    @inicializar_y_capturar_excepciones
    def Autenticar(self, *args, **kwargs):
        if 'service' in kwargs:
            service = kwargs['service']
        else:
            service = 'wsfe'
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
                cacert = LeerIni('iniciosistema') + LeerIni(clave='cacert', key='WSFEv1')
                cms = wsaa.SignTRA(tra, LeerIni(clave="cert_prod", key="WSAA"),
                               LeerIni(clave="privatekey_prod", key="WSAA"))
                ok = wsaa.Conectar("", LeerIni(clave='url_prod', key='WSAA'), cacert=cacert) #Produccion

            #Llamar al web service para autenticar
            ta = wsaa.LoginCMS(cms)

            #Grabo el ticket de acceso para poder reutilizarlo
            file = open(archivo, 'w')
            file.write(ta)
            file.close()
        # devuelvo el ticket de acceso
        return ta

    @inicializar_y_capturar_excepciones
    def ConstatarComprobantes(self, *args, **kwargs):
        cbte_modo =  kwargs['cbte_modo'] # modalidad de emision: CAI, CAE, CAEA
        cuit_emisor = LeerIni(clave='cuit', key='WSFEv1')  # proveedor
        pto_vta = kwargs['pto_vta']  # punto de venta habilitado en AFIP
        cbte_tipo = kwargs['cbte_tipo']  # 1: factura A (ver tabla de parametros)
        cbte_nro = kwargs['cbte_nro']  # numero de factura
        cbte_fch = kwargs['cbte_fch']  # fecha en formato aaaammdd
        imp_total = kwargs['imp_total']  # importe total
        cod_autorizacion = kwargs['cod_autorizacion']  # numero de CAI, CAE o CAEA
        doc_tipo_receptor = kwargs['doc_tipo_receptor']  # CUIT (obligatorio Facturas A o M)
        doc_nro_receptor = kwargs['doc_nro_receptor']  # numero de CUIT del cliente
        wscdc = WSCDC()
        ta = self.Autenticar()
        wscdc.SetTicketAcceso(ta_string=ta)
        wscdc.SetParametros(cuit=LeerIni(clave='cuit', key='WSFEv1'),
                            token=self.Token, sign=self.Sign)
        ok = wscdc.ConstatarComprobante(cbte_modo, cuit_emisor, pto_vta, cbte_tipo,
                                        cbte_nro, cbte_fch, imp_total, cod_autorizacion,
                                        doc_tipo_receptor, doc_nro_receptor)
        if not ok:
            Ventanas.showAlert(LeerIni('nombre_sistema'), "ERROR: {}".format(wscdc.ErrMsg))

        return ok

    def EstadoServidores(self):

        ta = self.Autenticar()
        self.Dummy()
        Ventanas.showAlert(LeerIni('nombre_sistema'),
                           "appserver status {} dbserver status {} authserver status {}".format(
                               self.AppServerStatus, self.DbServerStatus, self.AuthServerStatus
                           ))

    @inicializar_y_capturar_excepciones
    def ConsultarCAE(self, tipocbte, puntoventa, numero):
        self.CAE = ""
        self.Cuit = LeerIni(clave="cuit", key='WSFEv1')
        ta = self.Autenticar()
        self.SetTicketAcceso(ta_string=ta)
        if LeerIni(clave='homo') == 'S':  # homologacion
            self.Conectar()
        else:
            ok = self.Conectar("", self.WSDL) #Producción

        print("Tipo comprobante {}".format(tipocbte))
        caeconsultado = self.CompConsultar(tipo_cbte=tipocbte, punto_vta=puntoventa, cbte_nro=numero)
