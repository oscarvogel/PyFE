# coding=utf-8
"""¿La instalación quedó lista para salir a facturar?

Por que un chequeo local y no el diagnóstico de ARCA
----------------------------------------------------
`DiagnosticoAfip` habla con la web de ARCA: sirve para saber si la
autenticación anda, pero necesita internet y además no mira nada de lo que
falta para *empezar*. Con una instalación recién hecha el usuario se iba con
la app en verde y sin poder emitir, porque el CUIT emisor era un relleno y los
maestros podían estar vacíos si la carpeta `data/` no había viajado con el
ejecutable.

Este chequeo es local: mira la base y la configuración, no sale a la red. Por
eso puede correr al terminar de instalar y decir qué falta, con el lugar exacto
donde se carga cada cosa.

Los pasos se devuelven, no se muestran: la pantalla decide. Así la lógica se
prueba sin Qt.
"""

import os
from dataclasses import dataclass
from os.path import abspath, exists

from libs.instalacion import (SECCION_CERT, SECCION_FACTURACION,
                              cuit_emisor, cuit_es_real)
from libs.Utiles import LeerIni


@dataclass
class PasoInstalacion:
    nombre: str
    ok: bool
    detalle: str
    que_hacer: str = ""


# Los maestros sin los cuales no hay nada que emitir. Si falta uno, la app
# arranca igual y falla al usar la pantalla correspondiente.
MAESTROS_IMPRESCINDIBLES = [
    ("Alícuotas de IVA", "Tipoiva", "una alícuota es lo que se informa en cada renglón"),
    ("Tipos de documento", "Tipodoc", "el CUIT del cliente se elige de acá"),
    ("Tipos de responsable", "Tiporesp", "define la condición de IVA del receptor"),
    ("Formas de pago", "Formapago", "toda factura necesita una"),
    ("Tipos de comprobante", "TipoComprobante", "sin esto no se puede elegir qué emitir"),
]


def _conteos_maestros():
    """Trae los conteos de los maestros. Puede fallar si la base no abre."""
    from modelos.Formaspago import Formapago
    from modelos.Tipocomprobantes import TipoComprobante
    from modelos.Tipodoc import Tipodoc
    from modelos.Tipoiva import Tipoiva
    from modelos.Tiporesp import Tiporesp

    return {
        "Tipoiva": Tipoiva.select().count(),
        "Tipodoc": Tipodoc.select().count(),
        "Tiporesp": Tiporesp.select().count(),
        "Formapago": Formapago.select().count(),
        "TipoComprobante": TipoComprobante.select().count(),
    }


def chequear_instalacion(leer=None):
    """Devuelve la lista de pasos. Todos los que importan, en orden.

    No lanza: si la base no abre, eso es un paso que falla, no una excepción
    sin manejar en el arranque.
    """
    if leer is None:
        leer = LeerIni

    pasos = []
    pasos.append(_paso_base())
    pasos.extend(_pasos_maestros())
    pasos.append(_paso_consumidor_final())
    pasos.append(_paso_condicion_receptor())
    pasos.append(_paso_cuit(leer))
    pasos.extend(_pasos_facturacion(leer))
    return pasos


def pendientes(pasos):
    return [p for p in pasos if not p.ok]


# -- Pasos ------------------------------------------------------------------

def _paso_base():
    try:
        _conteos_maestros()
    except Exception as e:
        return PasoInstalacion(
            "Base de datos", False,
            "No se pudo leer: {}".format(type(e).__name__),
            "Revise los datos de conexión en Configuracion > Parametros. Con "
            "SQLite, que el archivo sistema.db este en la carpeta del programa "
            "y tenga permiso de escritura.")
    return PasoInstalacion("Base de datos", True, "Se pudo leer.")


def _pasos_maestros():
    try:
        conteos = _conteos_maestros()
    except Exception as e:
        return [PasoInstalacion(
            "Datos maestros", False,
            "No se pudieron leer: {}".format(type(e).__name__),
            "Esto pasa cuando la carpeta data/ no está junto al ejecutable. "
            "Sin los CSV la base queda creada pero vacía, y la app abre sin "
            "posibilidad de emitir.")]

    faltantes = []
    for nombre, clave, para_que in MAESTROS_IMPRESCINDIBLES:
        if conteos[clave] == 0:
            faltantes.append("{} ({}: {})".format(nombre, clave, para_que))

    detalle = ", ".join("{}: {}".format(c, conteos[c]) for c in
                        sorted(conteos))
    if faltantes:
        return [PasoInstalacion(
            "Datos maestros", False,
            "Vacíos: {}".format(", ".join(faltantes)),
            "Suele ser que la carpeta data/ no Viajó con el programa. La base "
            "se crea vacía y no hay forma de cargar los maestros desde la app.")]
    return [PasoInstalacion("Datos maestros", True, detalle)]


def _paso_consumidor_final():
    """El cliente por defecto para factura B y tique."""
    try:
        from modelos.Clientes import Cliente
        from modelos.Tiporesp import Tiporesp

        clientes = Cliente.select().count()
        if clientes == 0:
            return PasoInstalacion(
                "Cliente consumidor final", False, "No hay ningún cliente.",
                "Cárguelo desde Clientes. Es el que se usa por defecto en las "
                "facturas B.")
        # Con idtiporesp 3 (Consumidor Final) y documento vacío es el que
        # espera la app; el nombre exacto no importa tanto como el tipo.
        cf = (Tiporesp.get_or_none(Tiporesp.idtiporesp == 3) is not None)
        if not cf:
            return PasoInstalacion(
                "Cliente consumidor final", False,
                "No está el tipo de responsable 'Consumidor Final'.",
                "Se necesita el tipo con id 3. Sin él, la app no sabe cómo "
                "tratar a un cliente sin identificación.")
        return PasoInstalacion(
            "Cliente consumidor final", True, "{} cliente(s) cargados.".format(clientes))
    except Exception as e:
        return PasoInstalacion(
            "Cliente consumidor final", False,
            "No se pudo comprobar: {}".format(type(e).__name__), "")


def _paso_condicion_receptor():
    """Que ningún tipo quede con el default que no le corresponde.

    El default de la columna es 5 (Consumidor Final). Cuando la siembra no
    cargaba la columna, todas las filas quedaban ahí, y a un Responsable
    Inscripto con CUIT se le mandaba 'Consumidor Final' a ARCA.
    """
    from libs.catalogos import (CONDICION_CONSUMIDOR_FINAL,
                                CONDICION_IVA_POR_TIPO_RESPONSABLE)
    from modelos.Tiporesp import Tiporesp

    colgados = []
    for tipo in Tiporesp.select():
        nombre = (tipo.nombre or "").strip().upper()
        esperada = CONDICION_IVA_POR_TIPO_RESPONSABLE.get(nombre)
        if esperada is None:
            continue
        if (tipo.condicion_iva_receptor_id == CONDICION_CONSUMIDOR_FINAL
                and esperada != CONDICION_CONSUMIDOR_FINAL):
            colgados.append("{} (debería ser {})".format(tipo.nombre, esperada))

    if colgados:
        return PasoInstalacion(
            "Condición de IVA del receptor", False,
            "En el valor por defecto: {}".format(", ".join(colgados)),
            "A esos clientes se les manda 'Consumidor Final' a ARCA, y el "
            "campo es obligatorio desde la RG 5616. Corregilo desde el ABM de "
            "Tipos de Responsable.")
    return PasoInstalacion(
        "Condición de IVA del receptor", True,
        "Cada tipo tiene la suya.")


def _paso_cuit(leer):
    cuit = cuit_emisor(leer=leer)
    if not cuit:
        return PasoInstalacion(
            "CUIT del emisor", False, "No hay un CUIT válido.",
            "Es el CUIT con el que se emite: va a ARCA en cada comprobante y "
            "sale impreso en la factura. Carga el de la empresa en "
            "Configuracion > Datos empresa.")
    if not cuit_es_real(cuit):
        return PasoInstalacion(
            "CUIT del emisor", False, "El CUIT cargado no es válido.",
            "Revisalo en Configuracion > Datos empresa.")
    return PasoInstalacion("CUIT del emisor", True, cuit)


def _pasos_facturacion(leer):
    pasos = []

    categoria = str(leer(clave="cat_iva", key=SECCION_FACTURACION) or "").strip()
    if not categoria:
        pasos.append(PasoInstalacion(
            "Categoría de IVA", False, "Vacía.",
            "Es la categoría de IVA de la empresa. Configuracion > "
            "Parámetros."))
    else:
        pasos.append(PasoInstalacion("Categoría de IVA", True, categoria))

    try:
        pto = int(str(leer(clave="pto_vta", key=SECCION_FACTURACION) or 0))
    except ValueError:
        pto = 0
    if pto <= 0:
        pasos.append(PasoInstalacion(
            "Punto de venta", False, "No está cargado.",
            "Tiene que ser un punto de venta habilitado en ARCA. En "
            "Configuración > Parámetros."))
    else:
        pasos.append(PasoInstalacion("Punto de venta", True, str(pto)))

    pasos.append(_paso_certificados(leer))
    return pasos


def _paso_certificados(leer):
    homologacion = str(leer(clave="homo") or "S").upper() == "S"
    sufijo = "homo" if homologacion else "prod"
    modo = "homologación" if homologacion else "producción"

    cert = str(leer(clave="cert_" + sufijo, key=SECCION_CERT) or "").strip()
    key = str(leer(clave="privatekey_" + sufijo, key=SECCION_CERT) or "").strip()

    faltan = []
    for etiqueta, ruta in (("certificado", cert), ("clave privada", key)):
        if not ruta:
            faltan.append("{} sin cargar".format(etiqueta))
        elif not exists(abspath(ruta)):
            faltan.append("{} no está en {}".format(etiqueta, abspath(ruta)))

    if faltan:
        return PasoInstalacion(
            "Certificado de {}".format(modo), False,
            "; ".join(faltan),
            "Sin el certificado no hay autenticación contra ARCA, así que no se "
            "puede emitir. Se genera desde Configuración > Certificados.")
    return PasoInstalacion(
        "Certificado de {}".format(modo), True, cert)


def formatear(pasos):
    """Un texto para mostrar: sólo lo que falta, y qué hacer con eso."""
    faltan = pendientes(pasos)
    if not faltan:
        return "La instalación está completa. Se puede emitir."
    lineas = []
    for paso in faltan:
        lineas.append("* {}: {}".format(paso.nombre, paso.detalle))
        if paso.que_hacer:
            lineas.append("  {}".format(paso.que_hacer))
    return "\n".join(lineas)
