from controladores.ControladorBaseABM import ControladorBaseABM
from modelos.Tiporesp import Tiporesp
from vistas.ABMTipoResponsable import ABMTipoResponsableView


class ABMTipoResponsableController(ControladorBaseABM):
    
    model = Tiporesp
    campoclave = Tiporesp.idtiporesp.name
    
    def __init__(self):
        super().__init__()
        self.view = ABMTipoResponsableView()
        #self.view.exec_()
        self.conectarWidgets()