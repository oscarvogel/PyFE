# coding=utf-8
import contextlib
import os
from datetime import date

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
from xlsxwriter.worksheet import (
    Worksheet, cell_number_tuple, cell_string_tuple)
try:
    import win32com.client as win32
    WIN32 = True
except ImportError:
    WIN32 = False

from libs import Ventanas
from libs.Utiles import saveFileDialog, AbrirArchivo, FormatoFecha


class Excel:

    archivo = '' #nombre de archivo
    libro = None
    hoja = None
    cabeceras = {}

    formato = None
    formatos = {
        'moneda':{'num_format':'$#,##0.00'},
        'negrita':{'bold':True},
        'centradoh':{'align':'center'},
    }

    def ArmaCabeceras(self, cabeceras, fila=0, formato=None):
        if formato:
            formato_celda = self.libro.add_format(formato)
        else:
            formato_celda = self.libro.add_format({
                'bold': True,
                'border':2,
                'align':'center',
                'bg_color':'yellow'
            })
        if not self.archivo:
            return
        for k, v in cabeceras.items():
            self.hoja.write(fila, v, k, formato_celda)

        self.cabeceras = cabeceras

    def ObtieneArchivo(self, archivo:str='excel/archivo.xlsx') -> str:
        self.archivo = saveFileDialog(filename=archivo, files="Archivos de Excel (*.xlsx)")

        if not self.archivo.upper().endswith('XLSX'):#si no finaliza con extension de excel la anado
            self.archivo += '.XLSX'

        if self.archivo:
            self.libro = xlsxwriter.Workbook(self.archivo)
            self.hoja = self.libro.add_worksheet()

        return self.archivo

    def Titulo(self, titulo:str = '', desdecol:str = 'A', hastacol:str = 'A',
               fila:int = 0, combina:bool = True, **kwargs) -> None:
        # Create a format to use in the merged range.
        merge_format = self.libro.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        if 'tamanio' in kwargs:
            merge_format.set_size(kwargs['tamanio'])
        else:
            merge_format.set_size(14)
        if combina:
            self.hoja.merge_range('{}{}:{}{}'.format(desdecol, fila + 1, hastacol, fila + 1), titulo, merge_format)
        else:
            self.hoja.write('{}{}'.format(fila, desdecol))

    def Cerrar(self, abre=True):
        try:
            if not WIN32:
                for v in self.cabeceras.values():
                    self.set_column_autowidth(v)
            self.libro.close()
            if WIN32:
                xlautofit(self.archivo)

        except IOError:
            Ventanas.showAlert("Sistema", "No se puede escribir el archivo {} esta abierto. Intente cerrarlo".format(
                self.archivo
            ))
        if abre:
            AbrirArchivo(self.archivo)

    def EscribeFila(self, datos='', fila=1, inicio=0, formato=None, **kwargs):

        col = inicio
        for d in datos:
            if isinstance(d, date):
                item = FormatoFecha(d, formato='dma')
            else:
                item = d
            formato_celda = None
            if formato:
                if col in formato:
                    formato_celda = self.libro.add_format(formato[col])
            if formato_celda:
                if 'formula' in kwargs:
                    self.hoja.write_formula(fila, col, item, formato_celda)
                else:
                    self.hoja.write(fila, col, item, formato_celda)
            else:
                if 'formula' in kwargs:
                    self.hoja.write_formula(fila, col, item)
                else:
                    self.hoja.write(fila, col, item)
            col += 1

    def Totales(self, columnas, desdefila, hastafila, filaformula, formato=None):
        for col in columnas:
            formato_celda = None
            if formato:
                if isinstance(formato, dict):
                    formato_celda = self.libro.add_format(formato)
                else:
                    formato_celda = formato
            if formato_celda:
                self.hoja.write_formula(filaformula, col, '=sum({}{}:{}{})'.format(
                    chr(col + 65), desdefila, chr(col + 65), hastafila
                ), formato_celda)
            else:
                self.hoja.write_formula(filaformula, col, '=sum({}{}:{}{})'.format(
                    chr(col + 65), desdefila, chr(col + 65), hastafila
                ))

    def SubTitulo(self, titulo='', desdecol='A', hastacol='A', fila=0, combina=True):
        self.Titulo(titulo, desdecol, hastacol, fila, combina, tamanio=12)

    def get_column_width(self, column: int):
        """Get the max column width in a `Worksheet` column."""
        worksheet = self.hoja
        strings = getattr(worksheet, '_ts_all_strings', None)
        if strings is None:
            strings = worksheet._ts_all_strings = sorted(
                worksheet.str_table.string_table,
                key=worksheet.str_table.string_table.__getitem__)
        lengths = set()
        for row_id, colums_dict in worksheet.table.items():  # type: int, dict
            data = colums_dict.get(column)
            if not data:
                continue
            if type(data) is cell_string_tuple:
                iter_length = len(strings[data.string])
                if not iter_length:
                    continue
                lengths.add(iter_length)
                continue
            if type(data) is cell_number_tuple:
                iter_length = len(str(data.number))
                if not iter_length:
                    continue
                lengths.add(iter_length)
        if not lengths:
            return None
        return max(lengths)

    def set_column_autowidth(self, column: int):
        """
        Set the width automatically on a column in the `Worksheet`.
        !!! Make sure you run this function AFTER having all cells filled in
        the worksheet!
        """
        maxwidth = self.get_column_width(column=column)
        if maxwidth is None:
            return
        self.hoja.set_column(first_col=column, last_col=column, width=maxwidth)

    def EscribeFilaColumna(self, fila:int = 0, columna:int = 0, valor = None, formato = None, combina=None):
        if formato:
            if isinstance(formato, dict):
                formato_celda = self.libro.add_format(formato)
            else:
                formato_celda = formato
            if combina:
                self.hoja.merge_range(fila, columna, combina[0], combina[1], valor, formato_celda)
            else:
                self.hoja.write(fila, columna, valor, formato_celda)
        else:
            if combina:
                self.hoja.merge_range(fila, columna, combina[0], combina[1], valor)
            else:
                self.hoja.write(fila, columna, valor)

    def AgregaFormato(self):
        self.formato = None
        self.formato = self.libro.add_format()
        return self.formato

    def FormatoNumero(self, formato_numero):
        self.formato.set_num_format(formato_numero)

    def FormatoNegrita(self, negrita=True):
        self.formato.set_bold(negrita)

    def EstableceEncabezado(self, encabezados:dict, imagen='', alineacionimagen='L'):
        alineacionesimagenes = {
            'L':'image_left',
            'C':'image_center',
            'R':'image_right'
        }
        texto = ''
        for k, v in encabezados.items():
            texto += f'&{v}{k}'
        if imagen:
            texto += f'&{alineacionimagen}&[Picture]'
            opciones = {alineacionesimagenes[alineacionimagen]:imagen}
            self.hoja.set_header(texto, opciones)
        else:
            self.hoja.set_header(texto)

    def RepetirFila(self, primera=0, ultima=None):
        if ultima:
            self.hoja.repeat_rows(primera, ultima)
        else:
            self.hoja.repeat_rows(primera)

    def AjustarPaginas(self, ancho=1, alto=0, papel='A4'):
        """
        Ajuste el área impresa a un número específico de páginas tanto vertical como horizontalmente.
        :param ancho Número de páginas horizontalmente
        :param alto Número de páginas verticalmente (si esta en 0 se ajusta al alto necesario)
        :return:
        """
        papeles = {
            'A4':9,
            'Oficio':5,
        }
        self.hoja.set_paper(papeles.get(papel) or 0)
        self.hoja.fit_to_pages(ancho, alto)

    def NombreFilaColumna(self, fila=0, col=0):
        return xl_rowcol_to_cell(row=fila, col=col)

    def CombinaFilaColumna(self, desdefila=0, hastafila=0, desdecol=0, hastacol=0):
        self.hoja.merge_range(desdefila, desdecol, hastafila, hastacol, '')

@contextlib.contextmanager
def load_xl_file(xlfilepath):
    ''' Open an existing Excel file using a context manager
        `xlfilepath`: path to an existing Excel file '''
    xl = win32.DispatchEx("Excel.Application")
    wb = xl.Workbooks.Open(xlfilepath)
    try:
        yield wb
    finally:
        wb.Close(SaveChanges=True)
        xl.Quit()
        xl = None # this actually ends the process

def xlautofit(xlfilepath,skip_first_col=False):
    ''' relies on win32com.client to autofit columns on data sheets

        remember that this is using COM so sheet numbers start at 1 (not 0),
        so to avoid requiring the caller to remember this, we increment

        returns full path (including dir) to file '''
    if os.path.splitext(xlfilepath)[1] not in ('.xls','.xlsx'):
        raise

    autofitbegcol = 1
    if skip_first_col:
        autofitbegcol += 1

    # Autofit every sheet
    with load_xl_file(xlfilepath) as wb:
        for ws in wb.Sheets:
            autofitendcol = ws.UsedRange.Columns.Count
            ws.Range(ws.Cells(1, autofitbegcol),
                     ws.Cells(1, autofitendcol)).EntireColumn.AutoFit()
    return xlfilepath