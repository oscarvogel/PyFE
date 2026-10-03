# coding=utf-8
import threading
from ftplib import FTP

from libs.Utiles import LeerIni

def threaded(fn):
    def wrapper(*args, **kwargs):
        threading.Thread(target=fn, args=args, kwargs=kwargs).start()
    return wrapper

class ResguardoController(FTP):
    sizeWritten = 0

    @threaded
    def Cargar(self, filename, callback=None):
        servidor = LeerIni("servidor", key='RESPALDO')
        usuario = LeerIni("usuario", key='RESPALDO')
        clave = LeerIni("clave", key='RESPALDO')

        if not (servidor and usuario and clave):
            print("Resguardo desactivado: falta configurar [RESPALDO] en sistema.ini")
            return

        try:
            self.connect(servidor)
            self.login(usuario, clave)
            folderName = LeerIni("empresa", key='FACTURA')
            if not folderName in self.nlst():
                self.mkd(LeerIni("empresa", key='FACTURA'))
            self.cwd(LeerIni("empresa", key='FACTURA'))

            with open(filename, "rb") as f:
                self.storbinary("STOR " + filename, f, callback=self.handle, blocksize=1024)
        except Exception as e:
            print("Error no se pudo copiar {}".format(filename))

    def handle(self, block):
        self.sizeWritten += 1024
        print("Total de datos escritos {}".format(self.sizeWritten))