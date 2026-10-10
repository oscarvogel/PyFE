# coding=utf-8
"""Deja listo el certificado de homologacion para el instalador DEMO.

Por que existe
--------------
El demo se publica con un certificado de homologacion de Vogel, para que
abra y pueda emitir sin que el operador tenga que ir a ManageARCA. Eso mete
una clave privada en un asset publico, asi que el chequeo va ANTES de copiar
nada, y no es un chequeo de que el archivo exista:

1. que el `.crt` se pueda leer;
2. que no este vencido (y que no este por vencer, avisando antes);
3. que el CUIT del certificado sea el esperado -- si alguien pasa por error el
   certificado de PRODUCCION, el demo emitiria de verdad contra ARCA;
4. que la clave privada sea la del certificado. Un par desarmado no da error
   al copiar: da error al autorizar, en la maquina del cliente.

El certificado va a `installer/demo-certificados/`, que esta en .gitignore. No
va a `dist/`: de ahi saca los archivos la build de PRODUCCION.

Uso
---
    python tools/preparar_certificado_demo.py
    python tools/preparar_certificado_demo.py --verificar
    python tools/preparar_certificado_demo.py --limpiar
"""

import argparse
import datetime
import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

DESTINO = os.path.join(REPO, "installer", "demo-certificados")
ORIGEN = r"C:\Programacion\sistema\certificados"

# Los nombres que la app ya espera en sistema.ini. Ver
# controladores/GeneraCertificados.py
NOMBRE_CERT = "certificado_homologacion.crt"
NOMBRE_CLAVE = "clave_privada_homo.key"

# El CUIT del demo. Es de Vogel, no de un cliente: el certificado de
# homologacion que hay en esa carpeta es suyo.
CUIT_ESPERADO = "20-23347203-5"

# Si el certificado vence antes de esto, avisar: el demo se publica y queda
# sirviendo sin poder emitir sin que nadie se entere.
DIAS_AVISO = 45


class ErrorPreparacion(Exception):
    """Algo impide armar el certificado. El mensaje va a consola tal cual."""


def _cuit_del_certificado(cert):
    """El CUIT, del atributo `numero` del sujeto (asi lo emite ARCA)."""
    for atributo in cert.subject:
        if atributo.oid.dotted_string == "2.5.4.5":   # serialNumber
            texto = atributo.value
            digitos = "".join(c for c in texto if c.isdigit())
            if len(digitos) == 11:
                return digitos
    raise ErrorPreparacion(
        "El certificado no tiene el CUIT en el sujeto. Revisar que sea el de "
        "homologacion de ARCA y no otro archivo.")


def validar(ruta_cert, ruta_clave, cuit_esperado=CUIT_ESPERADO, hoy=None):
    """Chequea el par entero. Devuelve un dict con lo que encontro.

    Levanta ErrorPreparacion con un mensaje para mostrar si algo no esta bien.
    """
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    if not os.path.isfile(ruta_cert):
        raise ErrorPreparacion("No existe el certificado: {}".format(ruta_cert))
    if not os.path.isfile(ruta_clave):
        raise ErrorPreparacion("No existe la clave privada: {}".format(ruta_clave))

    with open(ruta_cert, "rb") as fh:
        cert = x509.load_pem_x509_certificate(fh.read())

    with open(ruta_clave, "rb") as fh:
        clave = serialization.load_pem_private_key(fh.read(), password=None)

    # La clave tiene que ser LA de ese certificado. Comparar el numero publico
    # (el modulo de la clave RSA) alcanza y no hace falta la firma.
    modulo_cert = cert.public_key().public_numbers().n
    modulo_clave = clave.public_key().public_numbers().n
    if modulo_cert != modulo_clave:
        raise ErrorPreparacion(
            "La clave privada NO es la del certificado. Un par desarmado no "
            "falla al copiar: falla al autorizar, en la maquina del cliente.")

    cuit = _cuit_del_certificado(cert)
    if cuit_esperado and cuit != "".join(c for c in cuit_esperado if c.isdigit()):
        raise ErrorPreparacion(
            "El certificado es del CUIT {} y el demo usa el {}. Si el archivo "
            "es el de PRODUCCION, el demo emitiria de verdad contra ARCA: "
            "no lo embarques.".format(cuit, cuit_esperado))

    hoy = hoy or datetime.datetime.now(datetime.timezone.utc)
    vence = cert.not_valid_after_utc
    dias = (vence.date() - hoy.date()).days
    if dias < 0:
        raise ErrorPreparacion(
            "El certificado vencio el {} (hace {} dias). Hay que pedir uno "
            "nuevo en ManageARCA.".format(vence.date(), abs(dias)))

    try:
        cn = cert.subject.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME)[0].value
    except Exception:
        cn = "(sin CN)"

    return {"cuit": cuit, "vence": vence.date(), "dias": dias, "cn": cn}


def copiar(ruta_cert, ruta_clave):
    """Deja el par en installer/demo-certificados/ con los nombres de la app."""
    os.makedirs(DESTINO, exist_ok=True)
    destino_cert = os.path.join(DESTINO, NOMBRE_CERT)
    destino_clave = os.path.join(DESTINO, NOMBRE_CLAVE)
    shutil.copyfile(ruta_cert, destino_cert)
    shutil.copyfile(ruta_clave, destino_clave)
    return destino_cert, destino_clave


def limpiar():
    if os.path.isdir(DESTINO):
        shutil.rmtree(DESTINO)
        return True
    return False


def main():
    analizador = argparse.ArgumentParser(
        description="Prepara el certificado de homologacion del demo.")
    analizador.add_argument("--cert", default=os.path.join(ORIGEN, "homo.crt"))
    analizador.add_argument("--clave", default=os.path.join(ORIGEN, "homo.key"))
    analizador.add_argument("--cuit", default=CUIT_ESPERADO)
    analizador.add_argument("--verificar", action="store_true",
                            help="Solo informa; no copia nada.")
    analizador.add_argument("--limpiar", action="store_true",
                            help="Borra la carpeta de certificados del demo.")
    args = analizador.parse_args()

    if args.limpiar:
        print("limpiado" if limpiar() else "no habia nada que limpiar")
        return 0

    try:
        info = validar(args.cert, args.clave, args.cuit)
    except ErrorPreparacion as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1

    print("CUIT         : {}".format(info["cuit"]))
    print("CN           : {}".format(info["cn"]))
    print("Vence        : {} (en {} dias)".format(info["vence"], info["dias"]))
    if info["dias"] < DIAS_AVISO:
        print("AVISO: vence en menos de {} dias. El demo se va a publicar y "
              "despues no va a poder emitir.".format(DIAS_AVISO))

    if args.verificar:
        return 0

    destino_cert, destino_clave = copiar(args.cert, args.clave)
    print("certificado  : {}".format(destino_cert))
    print("clave privada: {}".format(destino_clave))
    return 0


if __name__ == "__main__":
    sys.exit(main())