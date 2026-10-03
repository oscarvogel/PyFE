def test_diagnostico_afip_informa_configuracion_incompleta(tmp_path):
    from controladores.DiagnosticoAfip import DiagnosticoAfip

    def leer_ini(clave=None, key=None, carpeta=""):
        valores = {
            ("param", "homo"): "N",
            ("WSFEv1", "cuit"): "20233472035",
            ("WSAA", "cert_prod"): "",
            ("WSAA", "privatekey_prod"): "",
            ("WSAA", "url_prod"): "https://wsaa.afip.gov.ar/ws/services/LoginCms",
            ("WSFEv1", "url_prod"): "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
        }
        return valores.get((key or "param", clave), "")

    pasos = DiagnosticoAfip(leer_ini=leer_ini).ejecutar()

    assert pasos[0].nombre == "Configuracion"
    assert pasos[0].ok is False
    assert "cert_prod" in pasos[0].detalle
    assert "privatekey_prod" in pasos[0].detalle


def test_diagnostico_afip_ejecuta_wsaa_conexion_y_dummy(tmp_path):
    from controladores.DiagnosticoAfip import DiagnosticoAfip

    cert = tmp_path / "cert.crt"
    key_file = tmp_path / "cert.key"
    cert.write_text("cert")
    key_file.write_text("key")

    def leer_ini(clave=None, key=None, carpeta=""):
        valores = {
            ("param", "homo"): "N",
            ("WSFEv1", "cuit"): "20233472035",
            ("WSAA", "cert_prod"): str(cert),
            ("WSAA", "privatekey_prod"): str(key_file),
            ("WSAA", "url_prod"): "https://wsaa.afip.gov.ar/ws/services/LoginCms",
            ("WSFEv1", "url_prod"): "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL",
            ("WSFEv1", "cacert"): "conf/afip_ca_info.crt",
        }
        return valores.get((key or "param", clave), "")

    class FEv1Doble:
        def Autenticar(self):
            return "<ta />"

        def SetTicketAcceso(self, ta_string):
            self.ta_string = ta_string

        def Conectar(self, cache, wsdl=None, cacert=None):
            self.wsdl = wsdl
            self.cacert = cacert
            return True

        def Dummy(self):
            self.AppServerStatus = "OK"
            self.DbServerStatus = "OK"
            self.AuthServerStatus = "OK"

    instancias = []

    def fe_factory():
        fe = FEv1Doble()
        instancias.append(fe)
        return fe

    diagnostico = DiagnosticoAfip(fe_factory=fe_factory, leer_ini=leer_ini)
    pasos = diagnostico.ejecutar()

    assert [paso.nombre for paso in pasos] == [
        "Configuracion",
        "WSAA",
        "WSFE conexion",
        "WSFE Dummy",
    ]
    assert all(paso.ok for paso in pasos)
    assert instancias[0].cacert is None
    assert "AFIP/ARCA esta respondiendo correctamente" in diagnostico.formatear(pasos)
