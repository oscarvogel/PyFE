# coding=utf-8
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


def EsVerdadero(valor):

    return valor == b'\01'

def AbrirArchivo(cArchivo=None):
    if cArchivo:
        win32api.ShellExecute(0, "open", cArchivo, None, ".", 0)

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

def ubicacion_sistema():
    cUbicacion = LeerIni("InicioSistema") or os.path.dirname(argv[0])

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
