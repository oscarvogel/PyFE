# coding=utf-8
import base64
import email
import json
import logging
import os
import sys
import warnings
from os.path import abspath

import qrcode

from libs import Ventanas
from libs.Utiles import LeerIni, ubicacion_sistema, inicializar_y_capturar_excepciones
from controladores.pyqr import PyQR
from pyafipws.wsaa import WSAA
from pyafipws.wscdc import WSCDC
from pyafipws.wsfev1 import WSFEv1

CERT = "certificados/homologacion.crt"        # El certificado X.509 obtenido de Seg. Inf.
PRIVATEKEY = "certificados/homologacion.key"  # La clave privada del certificado CERT

try:
    from M2Crypto import BIO, Rand, SMIME, SSL
except ImportError:
    BIO = Rand = SMIME = SSL = None
    # utilizar alternativa (ejecutar proceso por separado)
    from subprocess import Popen, PIPE
    from base64 import b64encode
    from tempfile import NamedTemporaryFile


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
    def UltimoComprobante(self, tipo=1, ptovta=1, *args, **kwargs):
        wsdl = self.WSDL
        print("WSDL {}".format(wsdl))
        cache = None
        proxy = ""
        wrapper = ""  # "pycurl"
        cacert = None  # geotrust.crt"
        # cacert = LeerIni('iniciosistema') + LeerIni(clave='cacert', key='WSFEv1')
        wrapper = ""
        # if int(platform.release()) < 10:
        #     cacert = None
        # else:
        #     cacert = LeerIni('iniciosistema') + LeerIni(clave='cacert', key='WSFEv1')
        # cacert = LeerIni('iniciosistema') + LeerIni(clave='cacert', key='WSFEv1')
        # cacert = None
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
        wsaa = FEWSAA()
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
            logging.debug("Ticket de acceso {}".format(tra))
            #Generar el mensaje firmado(CMS)
            if LeerIni(clave='homo') == 'S':#homologacion
                cms = wsaa.SignTRA(tra, abspath(LeerIni(clave="cert_homo", key="WSAA")),
                               abspath(LeerIni(clave="privatekey_homo", key="WSAA")))
                ok = wsaa.Conectar("", LeerIni(clave='url_homo', key='WSAA'))  # Homologación
            else:
                # cacert = LeerIni('iniciosistema') + LeerIni(clave='cacert', key='WSFEv1')
                cacert = True
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

class FEWSAA(WSAA):


    @inicializar_y_capturar_excepciones
    def SignTRA(self, tra, cert, privatekey, passphrase=""):
        "Firmar el TRA y devolver CMS"
        return sign_tra(tra, cert, privatekey, passphrase)


def sign_tra(tra, cert=CERT, privatekey=PRIVATEKEY, passphrase=""):
    "Firmar PKCS#7 el TRA y devolver CMS (recortando los headers SMIME)"

    if BIO:
        print("pudo importar m2crypto")
        # Firmar el texto (tra) usando m2crypto (openssl bindings para python)
        buf = BIO.MemoryBuffer(tra)             # Crear un buffer desde el texto
        #Rand.load_file('randpool.dat', -1)     # Alimentar el PRNG
        s = SMIME.SMIME()                       # Instanciar un SMIME
        # soporte de contraseña de encriptación (clave privada, opcional)
        callback = lambda *args, **kwarg: passphrase
        # Cargar clave privada y certificado
        if not privatekey.startswith("-----BEGIN RSA PRIVATE KEY-----"):
            # leer contenido desde archivo (evitar problemas Applink / MSVCRT)
            if os.path.exists(privatekey) and os.path.exists(cert):
                privatekey = open(privatekey).read()
                cert = open(cert).read()
            else:
                raise RuntimeError("Archivos no encontrados: %s, %s" % (privatekey, cert))
        # crear buffers en memoria de la clave privada y certificado:
        key_bio = BIO.MemoryBuffer(privatekey.encode('utf8'))
        crt_bio = BIO.MemoryBuffer(cert.encode('utf8'))
        s.load_key_bio(key_bio, crt_bio, callback)  # (desde buffer)
        p7 = s.sign(buf, 0)                      # Firmar el buffer
        out = BIO.MemoryBuffer()                # Crear un buffer para la salida
        s.write(out, p7)                        # Generar p7 en formato mail
        # Rand.save_file('randpool.dat')         # Guardar el estado del PRNG's

        # extraer el cuerpo del mensaje (parte firmada)
        msg = email.message_from_string(out.read().decode('utf8'))
        for part in msg.walk():
            filename = part.get_filename()
            if filename == "smime.p7m":                 # es la parte firmada?
                return part.get_payload(decode=False)   # devolver CMS
    else:
        # Firmar el texto (tra) usando OPENSSL directamente
        try:
            if sys.platform.startswith("linux"):
                openssl = "openssl"
            else:
                path_openssl = LeerIni(clave="openssl", key="WSAA")
                if path_openssl != '':
                    openssl = path_openssl
                else:
                    if sys.maxsize <= 2**32:
                        openssl = r"c:\OpenSSL-Win32\bin\openssl.exe"
                    else:
                        openssl = r"c:\OpenSSL-Win64\bin\openssl.exe"
            # NOTE: workaround if certificate is not already stored in a file
            # SECURITY WARNING: the private key will be exposed a bit in /tmp
            #                   (in theory only for the current user)
            if cert.startswith("-----BEGIN CERTIFICATE-----"):
                cert_f = NamedTemporaryFile()
                cert_f.write(cert.encode('utf-8'))
                cert_f.flush()
                cert = cert_f.name
            else:
                cert_f = None
            if privatekey.startswith("-----BEGIN RSA PRIVATE KEY-----"):
                key_f = NamedTemporaryFile()
                key_f.write(privatekey.encode('utf-8'))
                key_f.flush()
                privatekey = key_f.name
            else:
                key_f = None
            try:
                out = Popen([openssl, "smime", "-sign",
                        "-signer", cert, "-inkey", privatekey,
                        "-outform","DER", "-nodetach"],
                    stdin=PIPE, stdout=PIPE,
                    stderr=PIPE).communicate(tra)[0]
            finally:
                # close temp files to delete them (just in case):
                if cert_f:
                    cert_f.close()
                if key_f:
                    key_f.close()
            return b64encode(out).decode("utf8")
        except OSError as e:
            if e.errno == 2:
                warnings.warn("El ejecutable de OpenSSL no esta disponible en el PATH")
            raise

class PyQRv1(PyQR):

    def __init__(self):
        super().__init__()

    def GenerarImagen(self, ver=1,
                      fecha="2020-10-13",
                      cuit=30000000007,
                      pto_vta=10, tipo_cmp=1, nro_cmp=94,
                      importe=12100, moneda="PES", ctz=1.000,
                      tipo_doc_rec=80, nro_doc_rec=20000000001,
                      tipo_cod_aut="E", cod_aut=70417054367476,
                      ):
        "Generar una im�gen con el c�digo QR"
        # basado en: https://www.afip.gob.ar/fe/qr/especificaciones.asp
        datos_cmp = {
            "ver": int(ver),
            "fecha": fecha,
            "cuit": int(cuit),
            "ptoVta": int(pto_vta),
            "tipoCmp": int(tipo_cmp),
            "nroCmp": int(nro_cmp),
            "importe": float(importe),
            "moneda": moneda,
            "ctz": float(ctz),
            "tipoDocRec": int(tipo_doc_rec),
            "nroDocRec": int(nro_doc_rec),
            "tipoCodAut": tipo_cod_aut,
            "codAut": int(cod_aut),
            }

        # convertir a representación json y codificar en base64:
        datos_cmp_json = json.dumps(datos_cmp)
        data_bytes = datos_cmp_json.encode("utf-8")
        url = self.URL % (base64.b64encode(data_bytes))

        qr = qrcode.QRCode(
            version=self.qr_ver,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        img.save(self.Archivo, "PNG")
        return url