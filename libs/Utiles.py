# coding=utf-8

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

from PyQt4.QtGui import QFileDialog

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
import win32api
from ConfigParser import ConfigParser
from functools import wraps

from cryptography.fernet import Fernet
from os.path import join
from sys import argv

from PyQt4 import QtGui

from libs import Ventanas

#necesario porque en mysql tengo definido el campo boolean como bit
def EsVerdadero(valor):

    return valor == b'\01'

#abro el archivo con el programa por defecto en windows
#tendria que ver como hacerlo en Linux
def AbrirArchivo(cArchivo=None):
    if cArchivo:
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
        Ventanas.showAlert("Sistema", "No existe la seccion {}".format(clave))
    return retorno

def GrabarIni(clave=None, key=None, valor=''):
    if not clave or not key:
        return
    Config = ConfigParser()
    Config.read('sistema.ini')
    cfgfile = open("sistema.ini",'wb')
    Config.set(key, clave, valor)
    Config.write(cfgfile)
    cfgfile.close()

def ubicacion_sistema():
    cUbicacion = LeerIni("iniciosistema") or os.path.dirname(argv[0])

    return cUbicacion

def imagen(archivo):
    archivoImg = ubicacion_sistema() + join("imagenes", archivo)
    if os.path.exists(archivoImg):
        return archivoImg
    else:
        return ""

def icono_sistema():

    cIcono = QtGui.QIcon(imagen("logo.ico"))
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
    plain_text = cipher_suite.decrypt(encrypted_data)
    return plain_text


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
    for i in xrange(10):
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

    #dialog = QFileDialog()
    #dialog.selectFile(filename)
    #dialog.setDirectory(directory)
    #dialog.setAcceptMode(QFileDialog.AcceptSave)
    #dialog.setFileMode(filter)
    cArchivo = QFileDialog.getSaveFileName(caption=caption,
                                           directory=join(directory, filename),
                                           filter=filter)
    #dialog.exec_()
    #cArchivo = dialog.selectedFiles()[0]
    return cArchivo if cArchivo else ''


def Normaliza(valor):
    valor = DeCodifica(valor)
    return valor.replace('Ñ','N').replace('ñ','n').replace('º','')

def DeCodifica(dato):
    return "{}".format(bytearray(dato, 'latin-1', errors='ignore').decode('utf-8','ignore'))
