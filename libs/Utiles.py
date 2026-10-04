# coding=utf-8
# encoding: utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

#Utilidades varias necesarias en el sistema
import argparse
import calendar
import configparser
import platform
import subprocess
import tempfile
from configparser import ConfigParser
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from smtplib import SMTP

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog

from pyafipws.pyemail import PyEmail

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

import datetime
import hashlib
import logging
import os
import sys
import traceback
import uuid
try:
    import win32api
except:
    pass
from functools import wraps

from cryptography.fernet import Fernet
from os.path import join
from sys import argv

from libs import Constantes


#necesario porque en mysql tengo definido el campo boolean como bit
def EsVerdadero(valor):

    return valor == b'\01'

#abro el archivo con el programa por defecto en windows
#tendria que ver como hacerlo en Linux
def AbrirArchivo(cArchivo=None):
    if cArchivo:
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', cArchivo))
        elif platform.system() == 'Windows':  # Windows
            os.startfile(cArchivo)
        else:  # linux variants
            subprocess.call(('xdg-open', cArchivo))


def escribir_pdf(generar, destino):
    """Arma el PDF a un temporal y recien despues lo pasa al destino.

    `generar` es la funcion que arma el PDF y acepta la ruta donde escribir.

    Devuelve `(ok, destino, motivo)`. Con `ok` en False, `motivo` dice por que
    y el archivo de destino queda **intacto**.

    Por que el temporal y no escribir directo
    ------------------------------------------
    fpdf2 abre el archivo de salida en modo escritura antes de escribir una
    sola linea. Si el destino esta abierto en un visor de PDF, Windows no lo
    deja: el archivo se trunca a 0 bytes y recien ahi la libreria se da
    cuenta. El resultado es doble y malo: se perdio el PDF anterior y quedo un
    archivo vacio. Y como el archivo existe, cualquier chequeo de "se genero"
    lo daba por bueno, asi que la app reportaba exito con un comprobante de
    cero bytes.

    Eso se reprodujo con Foxit PDF Reader abierto: `PermissionError` en
    `Path(name).write_bytes(self.buffer)`, archivo de 0 bytes, ningun aviso.

    Escribir a un temporal no tiene el problema: el temporal es nuevo y no
    puede estar bloqueado, y el destino se reemplaza de una sola vez, que en
    Windows y en Linux es atomico si estan en el mismo volumen. Si el
    destino esta bloqueado, el error pasa a ser del `os.replace`, que es donde
    corresponde, y el PDF viejo sigue ahi.
    """
    destino = os.path.abspath(destino)
    carpeta = os.path.dirname(destino) or "."
    if not os.path.isdir(carpeta):
        os.makedirs(carpeta)

    descriptor, temporal = tempfile.mkstemp(prefix="pyfe-", suffix=".pdf",
                                            dir=carpeta)
    os.close(descriptor)
    try:
        generar(temporal)
        if not os.path.isfile(temporal) or os.path.getsize(temporal) == 0:
            return False, destino, "el generador no escribio ningun archivo"
        os.replace(temporal, destino)
        return True, destino, None
    except PermissionError as error:
        return False, destino, (
            "no se pudo reemplazar {}: {} ({}). Es el que tenés abierto en el "
            "visor de PDF.".format(os.path.basename(destino), error.strerror,
                                   getattr(error, "winerror", "")))
    except Exception as error:
        return False, destino, "{}: {}".format(type(error).__name__, error)
    finally:
        if os.path.isfile(temporal):
            try:
                os.unlink(temporal)
            except OSError:
                pass

#leo el archivo de configuracion del sistema
#recibe la clave y el key a leer en caso de que tenga mas de una seccion el archivo

def _leer_config(Config, ruta):
    """Carga el archivo de configuracion en el ConfigParser, a mano.

    No se usa Config.read() a proposito: pyafipws/utils.py reemplaza ese
    metodo a nivel global por uno que abre en latin1 y que revienta si el
    archivo no existe. Como el patch es global, en cuanto se importa
    cualquier cosa de pyafipws el sistema.ini entero se leia en latin1
    (los acentos y la enie salian como caracteres raros) y cualquier
    archivo ausente tiraba FileNotFoundError en vez de devolver vacio.
    """
    try:
        with open(ruta, "r", encoding="utf-8-sig") as archivo:
            Config.read_file(archivo)
    except FileNotFoundError:
        pass
    except (OSError, UnicodeDecodeError, configparser.Error):
        # un archivo de configuracion ilegible no puede voltear la app
        pass


def LeerIni(clave=None, key=None, carpeta=''):
    analizador = argparse.ArgumentParser(description='Sistema de Facturacion Electronica.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio de sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    argumento = analizador.parse_known_args()[0]
    retorno = ''
    Config = ConfigParser()
    archivoini = argumento.archivo
    carpeta = argumento.inicio
    # Config.read("sistema.ini")
    if carpeta:
        _leer_config(Config, join(carpeta, archivoini))
        # logging.debug("Archivo utilizado {}".format(join(carpeta, archivoini)))
    else:
        _leer_config(Config, archivoini)
        # logging.debug("Archivo utilizado {}".format(archivoini))

    try:
        if not key:
            key = 'param'
        retorno = Config.get(key, clave)
    except:
        #Ventanas.showAlert("Sistema", "No existe la seccion {}".format(clave))
        pass
    # print("archivo {} clave {} key {} carpeta {} valor {}".format(archivoini, clave, key, carpeta, retorno))
    return retorno

def GrabarIni(clave=None, key=None, valor='', borrar=False):
    analizador = argparse.ArgumentParser(description='Sistema de Facturacion Electronica.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio del sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    argumento = analizador.parse_known_args()[0]
    archivoini = argumento.archivo
    carpeta = argumento.inicio

    if not clave or not key:
        return
    Config = ConfigParser()
    _leer_config(Config, join(carpeta, archivoini))
    # utf-8 explicito: con la codificacion por defecto de la plataforma
    # (cp1252 en Windows) los acentos y la enie del nombre de la empresa
    # se guardaban con otros bytes y al releerlos no coincidian.
    cfgfile = open(join(carpeta, archivoini), 'w', encoding='utf-8')
    if not Config.has_section(key):
        Config.add_section(key)
    if borrar:
        # Saca la clave en vez de dejarla vacia. Se usa cuando un secreto
        # migra a otro backend y la clave vieja deja de servir.
        Config.remove_option(key, clave)
    else:
        Config.set(key, clave, valor)
    Config.write(cfgfile)
    cfgfile.close()

def ubicacion_sistema():
    c_ubicacion = LeerIni("iniciosistema")
    if not c_ubicacion:#en caso de que no este establecido el inicio del sistema lo grabo
        ubicacion = os.path.split(os.path.abspath(os.path.realpath(sys.argv[0])))[0]
        GrabarIni(clave="iniciosistema", key="param", valor=f'{ubicacion}/')
        c_ubicacion = f'{os.path.dirname(sys.argv[0])}/'

    logging.debug("Ubicacion del sistema {}".format(c_ubicacion))
    return c_ubicacion

def imagen(archivo):
    """Ruta de un icono dentro de imagenes/.

    La resolucion real esta en libs.recursos: prueba varias carpetas base y
    devuelve la primera donde exista el archivo. Antes se armaba la ruta con
    el `iniciosistema` del ini, que queda desactualizado cuando la instalacion
    se copia a otra carpeta y por eso dejaba los iconos rotos en el ejecutable
    compilado.
    """
    from libs.recursos import imagen as _imagen
    return _imagen(archivo)


def icono(nombre, alterno=None):
    """Icono del set nuevo (imagenes/iconos/*.svg), con caida al viejo.

    Los SVG son vectoriales y de un solo trazo, asi que se ven nítidos en
    cualquier monitor y comparten estilo entre sí. Conviven con los PNG
    anteriores mientras se migra pantalla por pantalla.
    """
    from libs.recursos import icono as _icono
    return _icono(nombre, alterno)

def icono_sistema():
    """Icono de la aplicacion: el logo de Vogel Consultoria.

    Se usan los .png de imagenes/marca/ en vez de un .ico suelto porque QIcon
    elige la resolucion que necesita de la lista: en un monitor de alta
    densidad el icono de la barra de tareas se ve borroso si se le pasa un PNG
    de 1254 px que se reescala, y con un solo .ico hay que acertar el tamano.
    Los .ico si se usan para el .exe y el instalador, que los necesita el
    sistema operativo, no Qt.
    """
    cIcono = QtGui.QIcon()
    from libs.recursos import ruta_recurso
    for lado in (256, 128, 64, 48, 32, 24, 16):
        ruta = ruta_recurso("imagenes/marca/logo-{}.png".format(lado))
        if ruta:
            cIcono.addFile(ruta)
    if cIcono.isNull():
        # Sin los derivados: cae al original completo antes de quedar sin icono.
        cIcono = QtGui.QIcon(ruta_recurso("imagenes/marca/logo-vogel.png") or "")
    return cIcono

def a_entero(valor, defecto=0):
    """Convierte a entero sin tirar abajo la pantalla.

    El .ini lo edita la gente, a mano. Una clave vacia, con un typo o con un
    valor no numerico no puede impedir que se abra una pantalla entera: lo
    unico razonable es usar el valor por defecto y seguir.

    Antes se usaba a_entero(LeerIni(...), 0) pelado. Con [WSFEv1] cat_iva vacia, la
    pantalla de Comprobantes, la consulta de CAE y el rind e de CAEA caian
    con 'invalid literal for int()'.
    """
    if valor is None:
        return defecto
    if isinstance(valor, (int, float)):
        return int(valor)
    texto = str(valor).strip()
    if not texto:
        return defecto
    try:
        return int(texto)
    except ValueError:
        pass
    try:
        # "5.0" o "5,0" tambien son numeros validos para un entero.
        return int(float(texto.replace(",", ".")))
    except ValueError:
        return defecto


def a_decimal(valor, defecto=None):
    """Como a_entero, pero para montos.

    El defecto es None a proposito: None significa 'no hay dato', que es
    distinto de cero. Un importe en 0 y un importe desconocido no son lo mismo.
    """
    import decimal
    if valor is None:
        return defecto
    if isinstance(valor, decimal.Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return decimal.Decimal(str(valor))
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        return defecto
    try:
        return decimal.Decimal(texto)
    except decimal.InvalidOperation:
        return defecto


def formato_cuit(valor):
    """Devuelve el CUIT con guiones: 20123456789 -> 20-12345678-9

    El dato se guarda sin guiones porque es lo que espera AFIP, pero en un
    comprobante fiscal se muestra con guiones: es como lo pide la norma y
    como lo lee cualquier persona. El campo de captura de la app ya usa la
    mascara '99-99999999-9', pero el valor guardado en el .ini nunca pasa por
    esa mascara y llegaba al PDF crudo.
    """
    if not valor:
        return ""
    digitos = "".join(c for c in str(valor) if c.isdigit())
    if len(digitos) != 11:
        # No lo toco: un CUIT raro o algo que no es un CUIT se muestra tal
        # cual para que se vea el problema, en vez de recortarlo.
        return str(valor).strip()
    return "{}-{}-{}".format(digitos[:2], digitos[2:10], digitos[10:])


def hash_password(password):
    # uuid is used to generate a random number
    salt = uuid.uuid4().hex
    return hashlib.sha256(salt.encode() + password.encode()).hexdigest() + ':' + salt


def check_password(hashed_password, user_password):
    password, salt = hashed_password.split(':')
    return hashlib.sha256(salt.encode() + user_password.encode()).hexdigest()

def encriptar(password):
    key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(password)
    return cipher_text, key

def desencriptar(encrypted_data, key):
    cipher_suite = Fernet(key)
    if not isinstance(encrypted_data, bytes):
        encrypted_data = encrypted_data.encode()
    plain_text = cipher_suite.decrypt(encrypted_data)
    return plain_text.decode('utf-8')


def _texto_excepcion(objeto):
    """La Excepcion de pyafipws, como texto.

    pyemail.py deja `self.Excepcion = traceback.format_exception_only`: la
    FUNCION, sin llamar. Si se la pasa a logging tal cual, al log le queda la
    representacion "<built-in function format_exception_only>" en vez del
    mensaje real del error, que es justo lo que se necesita leer.
    """
    valor = getattr(objeto, "Excepcion", "")
    if callable(valor):
        try:
            valor = valor(sys.exc_info()[0], sys.exc_info()[1])
            if isinstance(valor, (list, tuple)):
                valor = "".join(valor)
        except Exception:
            valor = "error desconocido en el envio de correo"
    return str(valor or "") + " " + str(getattr(objeto, "Traceback", "") or "")


def _parametro_smtp(nombre, defecto=""):
    """Un valor de Parametros del sistema, o el que le paso.

    Los datos de correo estan guardados en la base, no en el codigo, para que
    cada instalacion pueda tener los suyos sin tocar el programa. Si la base
    todavia no esta (por ejemplo, en el primer arranque, o justo en el error que
    estamos reportando) se devuelve el valor por defecto.
    """
    try:
        from modelos.ParametrosSistema import ParamSist
        valor = ParamSist.ObtenerParametro(nombre)
        if valor and str(valor).strip():
            return str(valor).strip()
    except Exception:
        pass
    return defecto or ""


def inicializar_y_capturar_excepciones(func):
    "Decorador para inicializar y capturar errores"
    @wraps(func)
    def capturar_errores_wrapper(self, *args, **kwargs):
        try:
            # inicializo (limpio variables)
            self.Traceback = self.Excepcion = ""
            return func(self, *args, **kwargs)
        except Exception as e:
            ex = traceback.format_exception( sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            self.Traceback = ''.join(ex)
            self.Excepcion = traceback.format_exception_only( sys.exc_info()[0], sys.exc_info()[1])[0]
            logging.debug(self.Traceback)
            from libs import Ventanas
            # SilenciarError apaga SOLO el dialogo, no el reporte. Quien llama
            # (por ejemplo la emision de una factura) sabe mas que este
            # decorador y va a mostrar un error accionable; mostrar este ademas
            # era hacer ver el mismo problema dos veces. El correo a soporte
            # sigue yendo: perder el aviso automatico de una falla fiscal seria
            # un retroceso peor que el dialogo duplicado.
            if not getattr(self, "SilenciarError", False):
                Ventanas.showAlert("Error", "Se ha producido un error \n{}".format(self.Excepcion))
            if LeerIni('debug') == 'N':
                # A quien se le avisa sale de Parametros del sistema, y si no
                # esta configurado, de las constantes. Antes estaba fijo en el
                # codigo con la direccion del desarrollador anterior, y el
                # reporte automatico de errores de los clientes seguia yendo
                # ahi: o se perdia, o llegaba a un buzon que ya no es de nadie
                # de este proyecto.
                servidor = _parametro_smtp("SERVER_SMTP", Constantes.SERVER_SMTP)
                remitente = _parametro_smtp("USUARIO_SMTP", Constantes.USUARIO_SMTP)
                clave = _parametro_smtp("CLAVE_SMTP", Constantes.CLAVE_SMTP)
                puerto = _parametro_smtp("PUERTO_SMTP", Constantes.PUERTO_SMTP) or 587
                destinatario = _parametro_smtp("DESTINO_ERRORES", remitente) or remitente

                if not servidor or not remitente or not clave:
                    # Sin configurar no se intenta conectar: un host vacio o
                    # inventado revienta con un error de socket que no dice nada
                    # util, y esto corre justo cuando algo ya fallo. El
                    # traceback original ya quedo en el log, que es el registro
                    # que importa.
                    # Con el nombre real del parámetro, no con una palabra
                    # suelta: el que lee el log tiene que poder ir a
                    # Parametros del sistema y saber exactamente qué tocar.
                    faltantes = [n for n, v in
                                 (("SERVER_SMTP", servidor),
                                  ("USUARIO_SMTP", remitente),
                                  ("CLAVE_SMTP", clave)) if not v]
                    logging.error(
                        "No se reporto el error por correo: falta configurar {} "
                        "en Parametros del sistema. El traceback quedo en el log.".format(
                            ", ".join(faltantes)))
                else:
                    mensaje = "{} {}\n\nEnviado desde {}. {}".format(
                        self.Traceback, self.Excepcion,
                        Constantes.NOMBRE_PRODUCTO, Constantes.CREDITO_SOFTWARE
                    )
                    motivo = "Informe de errores de {}".format(
                        LeerIni(clave='empresa', key='FACTURA') or Constantes.NOMBRE_PRODUCTO)
                    pyemail = PyEmail()
                    conectado = pyemail.Conectar(servidor=servidor, usuario=remitente,
                                                 clave=clave, puerto=puerto)
                    if not conectado:
                        # pyemail deja Excepcion como la FUNCION traceback.
                        # format_exception_only, sin llamar, y por eso hay que
                        # traerla a texto antes de usarla.
                        logging.error("No se pudo conectar al servidor de correo: %s",
                                      _texto_excepcion(pyemail))
                    else:
                        ok = pyemail.Enviar(remitente, motivo, destinatario, mensaje)
                        if not ok:
                            # Que falle el reporte no puede tapar el error
                            # original: queda en el log.
                            logging.error("No se pudo enviar el reporte de errores: %s",
                                          _texto_excepcion(pyemail))
                # envia_correo(from_address=remitente, to_address=destinatario,
                #              message=mensaje, subject=motivo)
            else:
                print(self.Traceback, self.Excepcion)
            if self.LanzarExcepciones:
                raise
        finally:
            pass
    return capturar_errores_wrapper

def validar_cuit(cuit):
    # validaciones minimas
    if len(cuit) != 13 or cuit[2] != "-" or cuit[11] != "-":
        return False

    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

    cuit = cuit.replace("-", "") # remuevo las barras

    # calculo el digito verificador:
    aux = 0
    for i in range(10):
        aux += int(cuit[i])* base[i]

    aux = 11 - (aux - (int(aux / 11)* 11))

    if aux == 11:
        aux = 0
    if aux == 10:
        aux = 9

    return aux == int(cuit[10])

def FechaMysql(fecha=None):

    if not fecha:
        fecha = datetime.datetime.today()
    retorno = fecha.strftime('%Y%m%d')

    return retorno

def HoraMysql(hora=None):

    if not hora:
        hora = datetime.datetime.now()

    retorno = hora.strftime('%H:%M:%S')

    return retorno

def InicioMes(dFecha=None):
    if not dFecha:
        dFecha = datetime.date.today()

    return dFecha.replace(day=1)

def FinMes(hFecha=None):
    if not hFecha:
        hFecha = datetime.date.today()

    return hFecha.replace(day = calendar.monthrange(hFecha.year, hFecha.month)[1])

def GuardarArchivo(caption="Guardar archivo", directory="", filter="", filename=""):
    options = QFileDialog.Options()
    if platform.system() == 'Linux':
        options |= QFileDialog.DontUseNativeDialog
    cArchivo = QFileDialog.getSaveFileName(caption=caption,
                                           directory=join(directory, filename),
                                           filter=filter, options=options)[0]

    print(cArchivo)
    return cArchivo if cArchivo else ''


def Normaliza(valor):
    valor = DeCodifica(valor)
    return valor.replace('Ñ','N').replace('ñ','n').replace('º','')

def DeCodifica(dato):
    # return "{}".format(bytearray(dato, 'latin-1', errors='ignore').decode('utf-8','ignore'))
    # return '{}'.format(bytearray(str(dato))).decode('utf-8').encode('latin-1')
    return "{}".format(bytearray(dato, 'latin-1', errors='ignore').decode('utf-8','ignore'))

def initialize_logger(output_dir):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "error.log"), "a", encoding=None, delay="true")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create debug file handler and set level to debug
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(os.path.join(output_dir, "all.log"), maxBytes=20000)
    logger.addHandler(handler)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def openFileNameDialog(form=None, files=None, title='Abrir', filename=''):
    options = QFileDialog.Options()
    if platform.system() == 'Linux':
        options |= QFileDialog.DontUseNativeDialog
    fileName, _ = QFileDialog.getOpenFileName(form, title, filename,
                                              files, options=options)
    if fileName:
        return fileName
    else:
        return ''

def AbrirMultiplesArchivos(form=None, filter=None, title='Abrir'):
    options = QFileDialog.Options()
    if platform.system() == 'Linux':
        options |= QFileDialog.DontUseNativeDialog
    fileNames, _ = QFileDialog.getOpenFileNames(form, title,
                                              filter=filter, options=options)
    if fileNames:
        return fileNames
    else:
        return ''

def envia_correo(from_address = '', to_address = '', message = '', subject = '', password_email = '', to_cc='',
                 smtp_server='', smtp_port=587, files='', to_cco=''):
    smtp_email = smtp_server
    ok = True
    mime_message = MIMEMultipart('alternative')
    mime_message["From"] = from_address
    mime_message["To"] = to_address
    mime_message["Subject"] = subject
    if to_cc:
        mime_message["Cc"] = to_cc
    if to_cco:
        mime_message["Bcc"] = to_cco
    mime_message.attach(MIMEText(message, "plain"))
    mime_message.attach(MIMEText(message, "html"))
    if files:
        if not isinstance(files, list):
            files = [files,]
        for archivo in files:
            part = MIMEApplication(open(archivo, "rb").read())
            part.add_header('Content-Disposition', 'attachment',
                            filename=os.path.basename(archivo))
            mime_message.attach(part)

    try:
        smtp = SMTP(smtp_email, smtp_port)
        smtp.ehlo()
        smtp.starttls()

        smtp.login(from_address, password_email)
        smtp.sendmail(from_address, [to_address, to_cc], mime_message.as_string())
        smtp.quit()
        err_msg = ''
    except:
        err_msg = sys.exc_info()[1]
        logging.info(err_msg)
        ok = False

    return ok, err_msg

def PeriodoAFecha(periodo:str = ''):

    fecha = datetime.date(int(periodo[:4]), int(periodo[4:]), 1)

    return fecha

def saveFileDialog(form=None, files=None, title="Guardar", filename="excel/archivo.xlsx"):
    if not files:
        files = "Todos los archivos (*);;Archivos de texto (*.txt)"

    options = QFileDialog.Options()
    if platform.system() == 'Linux':
        options |= QFileDialog.DontUseNativeDialog

    #verifico que tenga un nombre de una carpeta incluido
    if filename.find("/") != -1:

        #si no existe la carpeta la creo
        if not os.path.isdir(filename.split("/")[0]):
            os.mkdir(filename.split("/")[0])

    fileName, _ = QFileDialog.getSaveFileName(form, title, filename,
                                              files, options=options)
    return fileName


def FormatoFecha(fecha=datetime.datetime.today(), formato='largo'):

    retorno = ''
    if isinstance(fecha, (str)):
        retorno = fecha
    else:
        if formato == 'largo':
            retorno = datetime.datetime.strftime(fecha,'%d %b %Y')
        elif formato == 'corto':
            retorno = datetime.datetime.strftime(fecha, '%d-%b')
        elif formato == 'dma':
            retorno = datetime.datetime.strftime(fecha, '%d/%m/%Y')
        elif formato == 'afip':
            retorno = datetime.datetime.strftime(fecha, '%d-%m-%Y')

    return retorno

def MesIdentificador(dFecha=datetime.datetime.now().date(), formato='largo'):
    MESES = [
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre',
    ]
    retorno = ''
    if formato == 'largo':
        retorno = '{}/{}'.format(MESES[dFecha.month - 1], dFecha.year)
    elif formato == 'corto':
        retorno = '{}/{}'.format(MESES[dFecha.month - 1][:3], dFecha.year)
    return retorno


def diferencia_meses(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month

def total_lineas_archivo(archivo):
    with open(archivo) as f:
        count = sum(1 for _ in f)
    return count

def getFileName(filename='pdf', base=False):

    tf = tempfile.NamedTemporaryFile(prefix=filename, mode='w+b')
    if base:
        return os.path.basename(tf.name)
    return tf.name
