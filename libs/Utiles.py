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
import calendar
import platform
from configparser import ConfigParser
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from smtplib import SMTP

from PyQt5 import QtGui
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

from libs import Ventanas, Constantes


#necesario porque en mysql tengo definido el campo boolean como bit
def EsVerdadero(valor):

    return valor == b'\01'

#abro el archivo con el programa por defecto en windows
#tendria que ver como hacerlo en Linux
def AbrirArchivo(cArchivo=None):
    if cArchivo:
        if platform.system() == 'Linux':
            open(cArchivo)
        else:
            win32api.ShellExecute(0, "open", cArchivo, None, ".", 0)

#leo el archivo de configuracion del sistema
#recibe la clave y el key a leer en caso de que tenga mas de una seccion el archivo
def LeerIni(clave=None, key=None):
    retorno = ''
    Config = ConfigParser()
    Config.read("sistema.ini")
    try:
        if not key:
            key = 'param'
        retorno = Config.get(key, clave)
    except:
        # Ventanas.showAlert("Sistema", "No existe la seccion {}".format(clave))
        print("No existe la seccion {}".format(clave))
    # parser = SafeConfigParser()
    # # Open the file with the correct encoding
    # with codecs.open('sistema.ini', 'r', encoding='utf-8') as f:
    #     parser.readfp(f)
    # try:
    #     if not key:
    #         key = 'param'
    #     retorno = parser.get(key, clave)
    # except:
    #     print("No existe la seccion {}".format(clave))
    return retorno

def GrabarIni(clave=None, key=None, valor=''):
    if not clave or not key:
        return
    Config = ConfigParser()
    Config.read('sistema.ini')
    cfgfile = open("sistema.ini",'w')
    Config.set(key, clave, valor)
    Config.write(cfgfile)
    cfgfile.close()

def ubicacion_sistema():
    cUbicacion = LeerIni("iniciosistema") or os.path.dirname(argv[0])

    return cUbicacion

def imagen(archivo):
    archivoImg = ubicacion_sistema() + join("imagenes", archivo)
    # print("Icono formulario {}".format(archivoImg))
    if os.path.exists(archivoImg):
        return archivoImg
    else:
        return ""

def icono_sistema():

    cIcono = QtGui.QIcon(imagen("Logo S-01.png"))
    return cIcono

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
            Ventanas.showAlert("Error", "Se ha producido un error \n{}".format(self.Excepcion))
            pyemail = PyEmail()
            remitente = 'fe@servinlgsm.com.ar'
            destinatario = 'fe@servinlgsm.com.ar'
            mensaje = "{} {} Enviado desde mi Software de Gestion desarrollado por http://www.servinlgsm.com.ar".format(
                self.Traceback, self.Excepcion
            )
            motivo = "Se envia informe de errores de {}".format(LeerIni(clave='empresa', key='FACTURA'))
            # servidor = ParamSist.ObtenerParametro("SERVER_SMTP")
            # clave = ParamSist.ObtenerParametro("CLAVE_SMTP")
            # usuario = ParamSist.ObtenerParametro("USUARIO_SMTP")
            # puerto = ParamSist.ObtenerParametro("PUERTO_SMTP") or 587
            #
            pyemail.Conectar(servidor=Constantes.SERVER_SMTP,
                             usuario=Constantes.USUARIO_SMTP,
                             clave=Constantes.CLAVE_SMTP,
                             puerto=Constantes.PUERTO_SMTP)

            ok = pyemail.Enviar(remitente, motivo, destinatario, mensaje)
            if not ok:
                Ventanas.showAlert("Error", "{} {}".format(
                    pyemail.Excepcion, pyemail.Traceback
                ))
            # envia_correo(from_address=remitente, to_address=destinatario,
            #              message=mensaje, subject=motivo)
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

    cArchivo = QFileDialog.getSaveFileName(caption=caption,
                                           directory=join(directory, filename),
                                           filter=filter)[0]
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
    # options |= QFileDialog.DontUseNativeDialog
    fileName, _ = QFileDialog.getOpenFileName(form, title, filename,
                                              files, options=options)
    if fileName:
        return fileName
    else:
        return ''

def envia_correo(from_address = '', to_address = '', message = '', subject = '', password_email = '', to_cc='',
                 smtp_server='', smtp_port=587, files=''):
    smtp_email = smtp_server
    ok = True
    mime_message = MIMEMultipart('related')
    mime_message["From"] = from_address
    mime_message["To"] = to_address
    mime_message["Subject"] = subject
    if to_cc:
        mime_message["Cc"] = to_cc
    mime_message.attach(MIMEText(message, "plain"))
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