
import os
from fpdf import FPDF, Template

from pyafipws.pyfepdf import FEPDF

HOMO = False
__version__ = '1.0'

class FEPDFv1(FEPDF):
    
    
    def CrearPlantilla(self, papel="A4", orientacion="portrait"):
        "Iniciar la creación del archivo PDF"

        fact = self.factura
        tipo, letra, nro = self.fmt_fact(
            fact["tipo_cbte"], fact["punto_vta"], fact["cbte_nro"].replace("-", "")
        )

        if HOMO:
            self.AgregarCampo(
                "homo",
                "T",
                100,
                250,
                0,
                0,
                size=70,
                rotate=45,
                foreground=0x808080,
                priority=-1,
            )

        # sanity check:
        for field in self.elements:
            # si la imagen no existe, eliminar nombre para que no falle fpdf
            text = field["text"]
            if text and not isinstance(text, str):
                text = str(text, "latin1", "ignore")
            if field["type"] == "I" and not os.path.exists(text):
                # ajustar rutas relativas a las imágenes predeterminadas:
                if os.path.exists(os.path.join(self.InstallDir, text)):
                    field["text"] = os.path.join(self.InstallDir, text)
                else:
                    field["text"] = ""
                    ##field['type'] = "T"
                    ##field['font'] = ""
                    ##field['foreground'] = 0xff0000

        # genero el renderizador con propiedades del PDF
        t = Template(
            elements=self.elements,
            format=papel,
            orientation=orientacion,
            title="%s %s %s" % (tipo.encode("latin1", "ignore"), letra, nro),
            author="CUIT %s" % self.CUIT,
            subject="CAE %s" % fact["cae"],
            keywords="AFIP Factura Electrónica",
            creator="PyFEPDF %s (http://www.servinlgsm.com.ar)" % __version__,
        )
        self.template = t
        return True
    
    