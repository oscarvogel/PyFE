# coding=utf-8
from controladores.ControladorBase import ControladorBase
from vistas.ImportarArticulos import ImportarArticulosView


class ImportarArticulosController(ControladorBase):
    """Importar articulos desde el Excel de un proveedor.

    Sin logica propia: todo esta en `libs/importararticulos.py` y la vista
    solo junta lo que se pidio. El controlador existe para el registro en
    `controladores/Main.py` y para que `ConectarWidgets` se llame desde un
    solo lugar, como en el resto de las pantallas.
    """

    def __init__(self):
        super(ImportarArticulosController, self).__init__()
        self.view = ImportarArticulosView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.ConectarWidgets()