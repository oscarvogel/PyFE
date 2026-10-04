"""Reimprimir con el PDF abierto destruia el comprobante anterior.

El sintoma
----------
El operador le daba Imprimir a una factura que ya tenia abierta en un visor
de PDF. La app no avisaba nada, y el archivo de la factura quedaba de CERO
bytes. El comprobante anterior, que era el unico que tenia, se perdia.

Por que
-------
fpdf2 abre el archivo de salida en modo escritura antes de escribir una sola
linea. Si el destino esta abierto en un visor, Windows no lo deja y el
`open` de fpdf2 igual lo trunca. Reproducido con Foxit PDF Reader abierto:

    File "controladores/Facturas.py", line 1207, in _armar_comprobante
        ok = pyfpdf.GenerarPDF(salida)
    File "fpdf/fpdf.py", line 6538, in output
        Path(name).write_bytes(self.buffer)

Despues el archivo existia (de 0 bytes) y la app lo daba por generado, porque
el unico chequeo era que el archivo existiera. Hacia falta pedir el retorno de
`GenerarPDF`, pero con fpdf2 no se puede: `Template.render()` esta anotado
-> None y el envoltorio de pyfepdf se come la excepcion.

El arreglo es no escribir nunca sobre el destino: se arma a un temporal y se
pasa recien terminado. El temporal es nuevo y no puede estar bloqueado, el
reemplazo es de una sola vez, y si falla el archivo anterior sigue intacto.

Una factura autorizada en ARCA no se puede volver a emitir, asi que perder el
PDF no tiene arreglo: hay que avisar, y el aviso tiene que decir que hacer.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import pytest  # noqa: E402

from libs.Utiles import escribir_pdf  # noqa: E402


PDF_VIEJO = b"%PDF-1.4\n%%EOF\ncomprobante de la impresion anterior\n"


def _generador(contenido=b"%PDF-1.4\n%%EOF\ncomprobante nuevo\n"):
    """Una 'generar' que escribe un PDF, como hace GenerarPDF."""
    def generar(ruta):
        with open(ruta, "wb") as archivo:
            archivo.write(contenido)
    return generar


# ------------------------------------------------------------- caso normal


def test_escribe_el_pdf(tmp_path):
    destino = tmp_path / "facturas" / "FACTURA_C-1.pdf"

    ok, ruta, motivo = escribir_pdf(_generador(), str(destino))

    assert ok is True
    assert motivo is None
    assert ruta == str(destino)
    assert destino.is_file()
    assert b"comprobante nuevo" in destino.read_bytes()


def test_crea_la_carpeta_si_no_esta(tmp_path):
    destino = tmp_path / "facturas" / "remitos" / "REMITO-1.pdf"

    ok, _ruta, _motivo = escribir_pdf(_generador(), str(destino))

    assert ok is True
    assert destino.is_file()


def test_sobrescribe_el_anterior(tmp_path):
    """La reimpresion tiene que dejar la version nueva, no acumular."""
    destino = tmp_path / "factura.pdf"
    destino.write_bytes(PDF_VIEJO)

    ok, _ruta, _motivo = escribir_pdf(_generador(), str(destino))

    assert ok is True
    contenido = destino.read_bytes()
    assert b"comprobante nuevo" in contenido
    assert b"impresion anterior" not in contenido


# ------------------------------------------------------------ caso bloqueado


def test_destino_bloqueado_no_toca_el_anterior(tmp_path, monkeypatch):
    """Este es el caso del bug: el visor tiene el archivo abierto.

    El error llega del `os.replace`, que es donde corresponde, y lo que mas
    importa: el comprobante anterior sigue intacto. Con la escritura directa
    quedaba de cero bytes.
    """
    destino = tmp_path / "factura.pdf"
    destino.write_bytes(PDF_VIEJO)

    def replace(origen, _destino):
        raise PermissionError(13, "El proceso no puede acceder al archivo")

    monkeypatch.setattr(os, "replace", replace)

    ok, ruta, motivo = escribir_pdf(_generador(), str(destino))

    assert ok is False
    assert "no se pudo reemplazar" in motivo
    assert "factura.pdf" in motivo
    assert destino.read_bytes() == PDF_VIEJO, \
        "el comprobante anterior se perdio: eso es lo que hay que evitar"


def test_no_deja_temporales_sin_borrar(tmp_path, monkeypatch):
    """Cada intento fallido dejaba un PDF a medio escribir en la carpeta."""
    destino = tmp_path / "factura.pdf"
    destino.write_bytes(PDF_VIEJO)
    monkeypatch.setattr(os, "replace",
                        lambda o, d: (_ for _ in ()).throw(
                            PermissionError(13, "bloqueado")))

    escribir_pdf(_generador(), str(destino))

    assert [p.name for p in tmp_path.iterdir()] == ["factura.pdf"], \
        "quedaron temporales: %s" % [p.name for p in tmp_path.iterdir()]


def test_el_generador_que_no_escribe_no_pisa_el_anterior(tmp_path):
    """Que exista un archivo vacio no es un PDF generado."""
    destino = tmp_path / "factura.pdf"
    destino.write_bytes(PDF_VIEJO)

    ok, _ruta, motivo = escribir_pdf(lambda ruta: None, str(destino))

    assert ok is False
    assert "no escribio" in motivo
    assert destino.read_bytes() == PDF_VIEJO


def test_el_generador_que_falla_no_pisa_el_anterior(tmp_path):
    destino = tmp_path / "factura.pdf"
    destino.write_bytes(PDF_VIEJO)

    def generar(_ruta):
        raise RuntimeError("la plantilla exploto")

    ok, _ruta, motivo = escribir_pdf(generar, str(destino))

    assert ok is False
    assert "la plantilla exploto" in motivo
    assert destino.read_bytes() == PDF_VIEJO


# --------------------------------------------------------- quien lo tiene que usar


def test_la_factura_escribe_a_un_temporal():
    import inspect

    import controladores.Facturas as MOD

    fuente = inspect.getsource(MOD.FacturaController._armar_comprobante)

    assert "escribir_pdf" in fuente, "la factura sigue escribiendo al destino"
    assert "ok = pyfpdf.GenerarPDF(salida)" not in fuente, \
        "quedo la escritura directa sobre el destino"


def test_el_remito_escribe_a_un_temporal():
    import inspect

    import controladores.Remitos as MOD

    fuente = inspect.getsource(MOD)
    assert "ok = pyfpdf.GenerarPDF(salida)" not in fuente, \
        "el remito sigue escribiendo al destino"
    assert "escribir_pdf" in fuente


def test_nadie_acepta_solo_que_el_archivo_exista():
    """El chequeo viejo: 'existe el archivo' como prueba de que se genero."""
    import importlib
    import inspect

    for nombre in ("Facturas", "Remitos"):
        mod = importlib.import_module("controladores.%s" % nombre)
        fuente = inspect.getsource(mod)
        assert "elif os.path.isfile(salida)" not in fuente, \
            "%s volvio al chequeo de que el archivo exista" % nombre
        assert "se_reescribio" not in fuente, \
            "%s todavia usa el chequeo por huella, que no alcanza" % nombre


def test_el_avisa_dice_que_hacer():
    """El mensaje tiene que dar la accion, no solo decir que fallo.

    El operador no puede adivinar que tiene un PDF abierto en otra
    aplicacion, y sin eso lo unico que ve es un error.
    """
    import inspect

    import controladores.Facturas as MOD
    import controladores.Remitos as MOD

    for mod in (MOD,):
        fuente = inspect.getsource(mod)
        assert "Cerrá" in fuente, "el aviso no dice que cerrar el PDF abierto"
        assert "no se pudo reemplazar" in fuente or "motivo" in fuente, \
            "el aviso no distingue el caso del archivo bloqueado"
