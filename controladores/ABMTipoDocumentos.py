from controladores.ControladorBase import ControladorBase
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.Tipodoc import Tipodoc
from vistas.ABMTipoDocumentos import ABMTipoDocumentoView


class ABMTipoDocumentoController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = ABMTipoDocumentoView()
        #self.view.exec_()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)

    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        if self.view.tipo == 'M':
            impuesto = Tipodoc.get_by_id(self.view.controles[Tipodoc.codigo.name].text())
        else:
            impuesto = Tipodoc()
            impuesto.codigo = self.view.controles[Tipodoc.codigo.name].text()

        impuesto.nombre = self.view.controles[Tipodoc.nombre.name].text()
        impuesto.save(force_insert=self.view.tipo == "A")
        self.view.btnAceptarClicked()
