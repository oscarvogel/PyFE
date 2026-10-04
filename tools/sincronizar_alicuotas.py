# coding=utf-8
"""Sincroniza las alicuotas de IVA con la tabla de ARCA.

Por que una herramienta y no mas filas en el CSV
-----------------------------------------------
El CSV de data/ trae tres alicuotas: 21, 10.5 y 0. Faltan 27, 5 y 2.5, y para
un comercio que venda alimentos, medicina o articulos basicos eso es no poder
facturar.

La tentacion es completar el CSV a mano. El problema es que los codigos de
alicuota del WSFE no son los del Libro IVA Digital: el Libro numera del 0003 al
0009 y el WSFE usa 01, 02, 03, 04, 05, 06, 07, 08, 09, 50. Copiar los de la
tabla del Libro y ponerlos en el CSV produce codigos que ARCA no acepta, y el
error aparece recien al emitir, con la factura autorizada a medias.

Por eso los codigos se bajan de ARCA: `ParamGetTiposIva` los devuelve con su
descripcion y sus fechas de vigencia, que es la unica fuente que no se inventa.
La herramienta se corre una vez, con el certificado cargado.

Que hace

- Se autentica contra ARCA en el modo configurado (homologacion o produccion).
- Baja `ParamGetTiposIva`.
- Inserta o actualiza la tabla tipoiva. No borra nada: si el administrador
  cargo una alicuota propia, se queda.

Que no hace

- No se corre solo al instalar. Requiere internet y un certificado valido, y
  una app de escritorio no puede exigir eso al arrancar. Por eso la instalacion
  siembra las tres alicuotas de siempre, que son las que todo negocio usa, y
  esto queda como un paso a pedido.
"""
import os
import sys
from decimal import Decimal, InvalidOperation

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.argv = [sys.argv[0]]


def _parsear(lineas, sep="|"):
    """'01|IVA General|2010-09-17|' -> (codigo, descripcion, desde, hasta)."""
    filas = []
    for linea in lineas:
        partes = str(linea).split(sep)
        partes = partes + [""] * (4 - len(partes))
        codigo, descripcion, desde, hasta = partes[:4]
        filas.append((codigo.strip(), descripcion.strip(),
                      desde.strip(), hasta.strip()))
    return filas


def _porcentaje_explicito(descripcion):
    """El porcentaje, SOLO si la descripcion lo dice. Si no, None.

    "IVA 27%" y "IVA 10,5%" se leen bien. "IVA General" y "Decreto 493/01" no
    dicen el porcentaje: son el 21% y el 10,5%, pero no hay forma de saberlo
    leyendo el nombre. Adivinar ahi es escribir 0 en una alicuota del 21%, que
    no se ve hasta que hay un renglon facturado mal.

    Por eso devuelve None en vez de un numero, y quien llama decide.
    """
    import re
    if not descripcion or "%" not in descripcion:
        return None
    numeros = re.findall(r"\d+(?:[.,]\d+)?", descripcion)
    for numero in numeros:
        try:
            return Decimal(numero.replace(",", "."))
        except InvalidOperation:
            continue
    return None


def sincronizar(fe, separador="|"):
    """Baja las alicuotas y las deja en la tabla. Devuelve un resumen."""
    from modelos.Tipoiva import Tipoiva

    filas = _parsear(fe.ParamGetTiposIva(sep=separador), separador)
    if not filas:
        raise RuntimeError(
            "ARCA no devolvio ninguna alicuota. Revise el certificado y si "
            "esta en el modo correcto (homologacion o produccion).")

    altas, cambios, sin_porcentaje, codigos_malos = 0, 0, [], []
    for codigo, descripcion, _desde, _hasta in filas:
        if not codigo:
            continue
        codigo = str(codigo).strip()
        # codigo entra en VARCHAR(2). Uno mas largo no se trunca: truncarlo lo
        # convertiria en otro codigo y meteria una fila silenciosamente mala.
        if len(codigo) != 2 or not codigo.isdigit():
            codigos_malos.append((codigo, descripcion))
            continue

        previa = Tipoiva.get_or_none(Tipoiva.codigo == codigo)
        if previa is not None:
            # El porcentaje NO se toca: es el dato que el administrador puede
            # haber corregido, y no se lo vamos a pisar con una lectura de la
            # descripcion.
            if previa.descrip != (descripcion or codigo)[:30]:
                previa.descrip = (descripcion or codigo)[:30]
                previa.save()
                cambios += 1
            continue

        iva = _porcentaje_explicito(descripcion)
        if iva is None:
            # Sin numero en el nombre no se sabe el porcentaje, y escribir un 0
            # seria inventar. Se informa y lo carga el operador.
            sin_porcentaje.append((codigo, descripcion))
            continue

        Tipoiva.create(codigo=codigo, descrip=(descripcion or codigo)[:30],
                       iva=iva)
        altas += 1

    return {"altas": altas, "cambios": cambios,
            "sin_porcentaje": sin_porcentaje, "codigos_malos": codigos_malos,
            "total": Tipoiva.select().count()}


def main():
    import logging

    from controladores.FE import FEv1
    from libs.Utiles import LeerIni

    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s: %(message)s")

    modo = "homologacion" if LeerIni(clave="homo") == "S" else "produccion"
    print("Sincronizando alicuotas de IVA contra ARCA ({})...".format(modo))
    print("Si falla por el certificado, corra Diagnostico desde Configuracion.")

    fe = FEv1()
    fe.Autenticar()
    if not fe.Token:
        print("No se pudo autenticar contra ARCA. No se toco la base.")
        return 1

    resumen = sincronizar(fe)
    print("Listo. {} alicuotas nuevas, {} actualizadas, {} en total.".format(
        resumen["altas"], resumen["cambios"], resumen["total"]))

    if resumen["sin_porcentaje"]:
        print()
        print("Estas alicuotas NO se agregaron porque la descripcion no dice el")
        print("porcentaje, y poner un 0 seria inventar. Cargalas desde el ABM de")
        print("Alicuotas de IVA con el valor que corresponde:")
        for codigo, descripcion in resumen["sin_porcentaje"]:
            print("  {} - {}".format(codigo, descripcion))

    if resumen["codigos_malos"]:
        print()
        print("Estos codigos vinieron con una forma rara y se descartaron:")
        for codigo, descripcion in resumen["codigos_malos"]:
            print("  {!r} - {}".format(codigo, descripcion))

    from modelos.Tipoiva import Tipoiva
    for t in Tipoiva.select().order_by(Tipoiva.codigo):
        print("  {} {:>10} {}".format(t.codigo, t.iva, t.descrip))
    return 0


if __name__ == "__main__":
    sys.exit(main())
