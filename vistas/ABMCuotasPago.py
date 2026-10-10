from libs.busqueda import normalizar
from libs.Spinner import Spinner
from libs.Utiles import inicializar_y_capturar_excepciones
from modelos.CuotasPago import CuotaPago
from modelos.Formaspago import ComboFormapago
from vistas.ABM import ABM


class ABMCuotasPagoView(ABM):

    model = CuotaPago()
    camposAMostrar = [CuotaPago.idcuota, CuotaPago.cuotas,
                      CuotaPago.recargo]
    ordenBusqueda = CuotaPago.cuotas
    campoClave = CuotaPago.idcuota

    # Cuando se abre desde Formas de pago, muestra solo los planes de esa
    # forma y da de alta sobre ella. None = todos (entrada por menu).
    forma_fija = None

    def __init__(self, *args, **kwargs):
        ABM.__init__(self, *args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        self.layoutID = self.ArmaEntrada(CuotaPago.idcuota.column_name,
                                         texto='Codigo')
        # OJO: el nombre del control es el del CAMPO ('formapago') y no el de
        # la columna ('idformapago'). El dict de peewee trae la FK con el
        # nombre del campo, y el guardado generico escribe `__data__` con ese
        # mismo nombre: con 'idformapago' la grilla revienta con KeyError y la
        # edicion no carga el combo.
        self.ArmaEntrada('formapago', texto='Forma pago',
                         boxlayout=self.layoutID,
                         control=ComboFormapago())
        lineaNum = self.ArmaEntrada(CuotaPago.cuotas.column_name,
                                    texto='Cuotas',
                                    control=Spinner(decimales=0))
        self.ArmaEntrada(CuotaPago.recargo.column_name, texto='Recargo %',
                         control=Spinner(decimales=2), boxlayout=lineaNum)

    @inicializar_y_capturar_excepciones
    def ArmaTabla(self):
        """La lista con el nombre de la tarjeta, no con su id.

        El ABM generico arma la fila con `d[columna]` y para la FK la clave
        del dict es 'formapago', no 'idformapago': mostrar el id crudo
        reventaba con KeyError. Aca se muestra el detalle (VISA, etc.).
        """
        self.tableView.setRowCount(0)
        self.tableView.ArmaCabeceras(
            cabeceras=['Idcuota', 'Forma de pago', 'Cuotas', 'Recargo'],
            formatos=['Entero', 'String', 'Entero', 'Moneda'])
        from modelos.Formaspago import Formapago
        try:
            filas = (CuotaPago.select(CuotaPago, Formapago)
                     .join(Formapago,
                           on=(CuotaPago.formapago == Formapago.idformapago))
                     .order_by(Formapago.detalle, CuotaPago.cuotas))
        except Exception:
            return
        busqueda = normalizar(self.lineEditBusqueda.text())
        for fila in filas:
            try:
                forma_id = int(fila.formapago_id)
            except Exception:
                try:
                    forma_id = int(fila.formapago.idformapago)
                except Exception:
                    forma_id = None
            if self.forma_fija and forma_id != int(self.forma_fija):
                continue
            try:
                detalle = fila.formapago.detalle
            except Exception:
                detalle = ""
            if busqueda and busqueda not in normalizar(detalle):
                continue
            self.tableView.AgregaItem(
                items=[fila.idcuota, detalle, fila.cuotas, fila.recargo])

    def PostAgrega(self):
        # Alta dirigida desde Formas de pago: la forma ya viene elegida.
        if self.forma_fija:
            try:
                combo = self.controles.get('formapago')
                indice = combo.findData(str(int(self.forma_fija)))
                if indice >= 0:
                    combo.setCurrentIndex(indice)
            except Exception:
                pass

    def CargaDatos(self, data=None):
        ABM.CargaDatos(self, data)
        # El combo se carga por dato (el id) y no por texto (el detalle):
        # `setText` busca por texto visible y con el id no encuentra nada.
        try:
            for d in (data or []):
                if 'formapago' not in d:
                    continue
                combo = self.controles.get('formapago')
                if combo is None:
                    continue
                indice = combo.findData(str(d['formapago']))
                if indice >= 0:
                    combo.setCurrentIndex(indice)
        except Exception:
            pass
