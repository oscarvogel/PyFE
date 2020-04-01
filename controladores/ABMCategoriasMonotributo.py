
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

    def conectarWidgets(self):
        super().conectarWidgets()
        self.view.controles[CategoriaMono.categoria.name].editingFinished.connect(self.onEditingCategoria)

    def onEditingCategoria(self):
        self.view.controles[CategoriaMono.categoria.name].setText(
            self.view.controles[CategoriaMono.categoria.name].text().upper()
        )
