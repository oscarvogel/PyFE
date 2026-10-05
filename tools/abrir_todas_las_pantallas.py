"""Abre todas las pantallas del menu una por una y dice cual se cae.

Es el mismo camino que el menu, con la misma fabrica de controladores, asi
que si una pantalla no abre, se ve cual es. Sin esto, un ABM con la grilla
vacia tira un IndexError en `Grillas._reparte_anchos` y en la consola queda
puro el traceback, sin decir que pantalla era.
"""

import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

from PyQt5.QtWidgets import QApplication  # noqa: E402

app = QApplication.instance() or QApplication([])

from controladores.Main import Main  # noqa: E402
from vistas.Main import SECCIONES  # noqa: E402

# El menu, en el mismo orden que lo ve el operador.
controladores = {
    "nueva-venta": "controladores.VentaSimple.VentaSimpleController",
    "comprobantes": "controladores.Facturas.FacturaController",
    "remitos": "controladores.Remitos.RemitoController",
    "recibos": "controladores.EmiteRecibo.EmiteReciboController",
    "reimprimir-factura": "controladores.ReImprimeFactura.ReImprimeFacturaController",
    "reimprimir-remito": "controladores.ReImprimeRemito.ReImprimeRemitoController",
    "proveedores": "controladores.Proveedores.ProveedoresController",
    "centro-costos": "controladores.CentroCostos.CentroCostoController",
    "carga-facturas": "controladores.CargaFacturasProveedor.CargaFacturaProveedorController",
    "iva-compras": "controladores.IVACompras.IVAComprasController",
    "rg3685-compras": "controladores.RG3685Compras.RG3685ComprasController",
    "iva-ventas": "controladores.IVAVentas.IVAVentasController",
    "rg3685-ventas": "controladores.RG3685Ventas.RG3685VentasController",
    "importar": "controladores.ImportaAFIP.ImportaAFIPController",
    "clientes": "controladores.Clientes.ClientesController",
    "cuenta-corriente": "controladores.ConsultaCtaCte.ConsultaCtaCteController",
    "enviar-email": "controladores.EnvioEmail.EnvioEmailController",
    "stock": "controladores.Stock.StockController",
    "productos": "controladores.Articulos.ArticulosController",
    "ajustes-stock": "controladores.Stock.AjustesStockController",
    "movimientos-stock": "controladores.Stock.MovimientosStockController",
    "grupos": "controladores.ABMGrupos.ABMGrupoController",
    "impuestos": "controladores.ABMImpuesto.ABMImpuestoController",
    "informe-ventas-grupo": "controladores.InformeVentasPorGrupo.InformeVentasPorGrupoController",
    "diagnostico": "controladores.Diagnostico.DiagnosticoController",
    "consulta-cuit": "controladores.ConsultaPadronAfip.ConsultaPadronAfipController",
    "constatacion": "controladores.ConstatacionComprobantes.ConstatacionComprobantesController",
    "consulta-cae": "controladores.ConsultaCAE.ConsultaCAEController",
    "rinde-caea": "controladores.RindeCAEAIndividual.RindeCAEAIndividualController",
    "categorias-mono": "controladores.ABMCategoriasMonotributo.ABMCategoriasMonotributoController",
    "informe-recategorizacion": "controladores.InfRecMonotributo.InfRecMonotributoController",
}

fallas = []
for _, _, items in SECCIONES:
    for clave, etiqueta, _icono in items:
        ruta = controladores.get(clave)
        if not ruta:
            continue
        modulo, clase = ruta.rsplit(".", 1)
        try:
            import importlib
            controlador = getattr(importlib.import_module(modulo), clase)()
            app.processEvents()
            ventana = getattr(controlador, "view", None)
            if ventana is not None and hasattr(ventana, "show"):
                ventana.show()
                app.processEvents()
                ventana.close()
            print("OK    {:<26} {}".format(clave, etiqueta))
        except Exception as e:
            detalle = traceback.format_exc().strip().splitlines()[-1]
            print("FALLA {:<26} {} -> {}".format(clave, etiqueta, detalle))
            fallas.append((clave, etiqueta, detalle))

print()
if fallas:
    print("PANTALLAS QUE NO ABREN:")
    for clave, etiqueta, detalle in fallas:
        print("  - {} ({}): {}".format(clave, etiqueta, detalle))
else:
    print("Todas las pantallas del menu abren.")
