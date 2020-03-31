
from controladores.ControladorBaseABM import ControladorBaseABM
from modelos.CategoriasMonotributo import CategoriaMono
from vistas.ABMCategoriasMonotributo import ABMCategoriaMonoView


class ABMCategoriaMonoController(ControladorBaseABM):

    model = CategoriaMono
    campoclave = CategoriaMono.categoria.name

    def __init__(self):
        super().__init__()
        self.view = ABMCategoriaMonoView()
        self.conectarWidgets()
