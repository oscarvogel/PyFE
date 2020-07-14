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
import platform
import subprocess
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

from libs import Ventanas, Constantes


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

#leo el archivo de configuracion del sistema
#recibe la clave y el key a leer en caso de que tenga mas de una seccion el archivo
def LeerIni(clave=None, key=None, carpeta=''):
    analizador = argparse.ArgumentParser(description='Sistema de Facturacion Electronica.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio de sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    argumento = analizador.parse_args()
    retorno = ''
    Config = ConfigParser()
    archivoini = argumento.archivo
    carpeta = argumento.inicio
    # Config.read("sistema.ini")
    if carpeta:
        Config.read(join(carpeta, archivoini))
        # logging.debug("Archivo utilizado {}".format(join(carpeta, archivoini)))
    else:
        Config.read(archivoini)
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

def GrabarIni(clave=None, key=None, valor=''):
    analizador = argparse.ArgumentParser(description='Sistema de Facturacion Electronica.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio de sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    argumento = analizador.parse_args()
    archivoini = argumento.archivo
    carpeta = argumento.inicio

    if not clave or not key:
        return
    Config = ConfigParser()
    Config.read(join(carpeta, archivoini))
    cfgfile = open(join(carpeta, archivoini), 'w')
    if not Config.has_section(key):
        Config.add_section(key)
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
            if LeerIni('debug') == 'N':
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