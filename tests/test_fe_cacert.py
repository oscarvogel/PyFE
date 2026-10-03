def test_obtener_cacert_vacio_desactiva_validacion(monkeypatch):
    import controladores.FE as fe

    monkeypatch.setattr(fe, "LeerIni", lambda clave=None, key=None, carpeta="": "")

    assert fe.obtener_cacert("WSAA") is None


def test_obtener_cacert_devuelve_ruta_configurada(monkeypatch):
    import controladores.FE as fe

    monkeypatch.setattr(fe, "LeerIni", lambda clave=None, key=None, carpeta="": " conf/afip_ca_info.crt ")

    assert fe.obtener_cacert("WSAA") == "conf/afip_ca_info.crt"


def test_archivo_ticket_acceso_separa_ambiente(monkeypatch, tmp_path):
    import controladores.FE as fe

    def leer_ini(clave=None, key=None, carpeta=""):
        if clave == "homo":
            return "N"
        return ""

    monkeypatch.setattr(fe, "LeerIni", leer_ini)
    monkeypatch.setattr(fe, "ubicacion_sistema", lambda: str(tmp_path))

    assert fe.archivo_ticket_acceso("wsfe") == str(tmp_path / "wsfe-prod-ta.xml")
