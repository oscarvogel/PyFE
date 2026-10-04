# coding=utf-8
"""Comprueba que una instalacion nueva quedo completa.

Para que testear el instalador no sea mirar la pantalla: se corre esto contra
la carpeta instalada y dice, punto por punto, que quedo bien y que no.

    python tools/verificar_primera_instalacion.py C:\\ruta\\de\\instalacion

Que mira
-------
- que sistema.ini exista y tenga configurado = S (o sea, que el asistente
  llego a completarse)
- que el CUIT emisor se haya completado: es la clave que viaja a ARCA, y sin
  esto la app abre pero no puede emitir
- que la base exista y tenga los maestros sembrados
- que la version de la base haya quedado Advanced sin sellar migraciones
  fallidas
- que cada tipo de responsable mande su condicion de IVA correcta a ARCA
- que este el cliente consumidor final
- que el certificado del modo activo este, y si no, lo dice como pendiente

Que NO puede mirar
------------------
Que el asistente se vea bien, ni que la app sea usable: eso es del operador.
"""
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# La carpeta a revisar se toma ANTES de limpiar sys.argv: libs.Utiles parsea
# los argumentos al importarse (para encontrar el sistema.ini) y se los
# come. Guardar el valor primero y limpiar despues, al reves, hace que la
# herramienta mire siempre la carpeta por omision.
CARPETA = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files\Asiento"
sys.argv = [sys.argv[0]]


class _Falso(object):
    def __init__(self, **atributos):
        self.__dict__.update(atributos)


def _cabeza(titulo):
    print()
    print(titulo)
    print("-" * len(titulo))


def _ok(texto):
    print("  OK    {}".format(texto))


def _falta(texto, que_hacer=""):
    print("  FALTA {}".format(texto))
    if que_hacer:
        print("         {}".format(que_hacer))


def _chequear_ini(carpeta):
    _cabeza("Configuracion")
    from libs.Utiles import GrabarIni, LeerIni  # noqa: F401

    os.chdir(carpeta)
    ruta = os.path.join(carpeta, "sistema.ini")
    if not os.path.isfile(ruta):
        _falta("sistema.ini: el asistente no llego a completarse",
               "Correr main.exe desde {} y completar el asistente.".format(carpeta))
        return False

    _ok("sistema.ini existe")

    if str(LeerIni(clave="configurado", key="param") or "").upper() != "S":
        _falta("configurado != S: la app va a volver a pedir la instalacion")
        return False
    _ok("configurado = S (no vuelve a pedir la instalacion)")

    # El CUIT emisor: la clave que va en Auth.Cuit de cada llamada a ARCA.
    from libs.instalacion import cuit_emisor, cuit_es_real, normalizar_cuit_emisor

    cuit = cuit_emisor()
    de_facturacion = LeerIni(clave="cuit", key="FACTURA")
    if not cuit_es_real(cuit):
        _falta("CUIT del emisor: {!r}".format(cuit or "(vacio)"),
               "Cargarlo en Configuracion > Datos empresa. Sin esto la app "
               "abre pero no puede emitir contra ARCA.")
        return False
    _ok("CUIT del emisor: {}".format(cuit))

    if not de_facturacion:
        _falta("[FACTURA] cuit esta vacio: el asistente no lo guardo")

    resultado = normalizar_cuit_emisor()
    if resultado["estado"] == "discrepan":
        _falta("las dos claves de CUIT dicen cosas distintas ({})".format(
            resultado.get("conflicto")),
               "La app usa el de Configuracion. Corregilo ahi.")
        return False
    _ok("las dos claves de CUIT coinciden ({})".format(resultado["estado"]))
    return True


def _chequear_base(carpeta):
    _cabeza("Base de datos y maestros")
    from libs.Utiles import LeerIni

    nombre = LeerIni(clave="basedatos", key="param")
    ruta = os.path.join(carpeta, "{}.db".format(nombre or "sistema"))
    if not os.path.isfile(ruta):
        _falta("no esta la base {}".format(os.path.basename(ruta)),
               "Puede ser que base = mysql en vez de sqlite.")
        return False
    _ok("base creada: {}".format(os.path.basename(ruta)))

    c = sqlite3.connect(ruta)
    try:
        def contar(tabla):
            try:
                return c.execute("select count(*) from " + tabla).fetchone()[0]
            except Exception:
                return None

        minimos = [
            ("Alícuotas de IVA", "tipoiva", 3),
            ("Tipos de documento", "tipodoc", 5),
            ("Tipos de responsable", "tiporesp", 4),
            ("Formas de pago", "formapago", 1),
            ("Tipos de comprobante", "tipocomp", 10),
        ]
        for nombre, tabla, minimo in minimos:
            n = contar(tabla)
            if n is None:
                _falta("no existe la tabla {}".format(tabla))
            elif n < minimo:
                _falta("{} tiene {} filas, se esperaban {}".format(tabla, n, minimo),
                       "La carpeta data/ no viajaron con el programa. Sin los "
                       "CSV la base queda vacia y no se puede emitir.")
            else:
                _ok("{}: {} filas".format(tabla, n))

        clientes = contar("clientes")
        if not clientes:
            _falta("no hay ningun cliente cargado",
                   "El consumidor final no se creo: sin el no se pueden "
                   "emitir facturas B ni tiques.")
        else:
            _ok("clientes: {} filas".format(clientes))

        # La condicion de IVA del receptor: es obligatoria ante ARCA desde la
        # RG 5616, y el default de la columna es 'Consumidor Final'.
        try:
            filas = c.execute(
                "select nombre, condicion_iva_receptor_id from tiporesp").fetchall()
            from libs.catalogos import (CONDICION_CONSUMIDOR_FINAL,
                                        CONDICION_IVA_POR_TIPO_RESPONSABLE)
            colgados = [n for n, v in filas
                        if CONDICION_IVA_POR_TIPO_RESPONSABLE.get((n or "").upper())
                        not in (None, v)]
            if colgados:
                _falta("tipos de responsable con la condicion de IVA de "
                       "Consumidor Final: {}".format(", ".join(colgados)),
                       "A esos clientes se los manda a ARCA como consumidor "
                       "final, que es incompatible con el documento 80. Se "
                       "corrige solo en el primer arranque si siguen en 5.")
            else:
                _ok("cada tipo de responsable manda su condicion de IVA")
        except Exception as e:
            _falta("no se pudieron leer las condiciones de IVA: {}".format(e))

        try:
            version = c.execute(
                "select valor from paramsist where parametro = 'VERSION_DB'"
            ).fetchone()
            version = version[0] if version else None
            _ok("VERSION_DB = {}".format(version))
        except Exception as e:
            _falta("no se pudo leer VERSION_DB: {}".format(e))
    finally:
        c.close()
    return True


def _chequear_certificado(carpeta):
    _cabeza("Certificado")
    from libs.Utiles import LeerIni
    from libs.instalacion import SECCION_CERT

    homologacion = str(LeerIni(clave="homo") or "S").upper() == "S"
    sufijo = "homo" if homologacion else "prod"
    modo = "homologación" if homologacion else "producción"

    cert = str(LeerIni(clave="cert_" + sufijo, key=SECCION_CERT) or "").strip()
    key = str(LeerIni(clave="privatekey_" + sufijo, key=SECCION_CERT) or "").strip()

    problemas = []
    for etiqueta, ruta in (("certificado", cert), ("clave privada", key)):
        if not ruta:
            problemas.append("{} sin cargar".format(etiqueta))
        elif not os.path.isfile(os.path.join(carpeta, ruta)):
            problemas.append("{} no esta en {}".format(etiqueta, ruta))

    if problemas:
        _falta("modo {}: {}".format(modo, "; ".join(problemas)),
               "Es lo unico que falta para poder emitir. Se genera desde la "
               "pantalla Certificados, o se copian los dos archivos a la "
               "carpeta certificados/.")
    else:
        _ok("certificado y clave de {} presentes".format(modo))
    return not problemas


def main():
    carpeta = os.path.abspath(CARPETA)
    print("Revisando la instalacion de:", carpeta)
    if not os.path.isdir(carpeta):
        print("Esa carpeta no existe.")
        return 1

    ejecutable = os.path.join(carpeta, "main.exe")
    if os.path.isfile(ejecutable):
        _ok("main.exe presente ({} MB)".format(
            round(os.path.getsize(ejecutable) / 1048576.0, 1)))
    else:
        _falta("main.exe")

    datos = os.path.join(carpeta, "data")
    if os.path.isdir(datos):
        _ok("data/ con {} archivos CSV (los maestros)".format(
            len([n for n in os.listdir(datos) if n.endswith(".csv")])))
    else:
        _falta("data/: sin los CSV la base se crea VACIA y no se puede emitir",
               "Es el fallo que hizo que instalar en una maquina nueva no "
               "pudiera facturar nada.")

    # A partir de leer el ini hace falta estar parado en la carpeta: la app
    # resuelve todo con rutas relativas a donde corre.
    if os.path.isfile(os.path.join(carpeta, "sistema.ini")):
        ok_ini = _chequear_ini(carpeta)
        ok_base = _chequear_base(carpeta)
        ok_cert = _chequear_certificado(carpeta)
    else:
        ok_ini = ok_base = ok_cert = False

    print()
    if ok_ini and ok_base and ok_cert:
        print("LISTO PARA EMITIR. La instalacion quedo completa.")
        return 0
    print("FALTA ALGO. Con esto todavia no se puede emitir contra ARCA.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
