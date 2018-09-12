# coding=utf-8
import datetime

from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDateEdit, QFont


class Fecha(QDateEdit):

    proximoWidget = None
    tamanio = 12

    def __init__(self, *args, **kwargs):
        QDateEdit.__init__(self, *args)
        self.setCalendarPopup(True)
        #self.cw = QNCalendarWidget(n=1, columns=1)
        #self.setCalendarWidget(self.cw)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)


    def setFecha(self, fecha=datetime.datetime.today(), format=None):
        if format:
            if format == "Ymd":
                fecha = datetime.date(year=int(fecha[:4]),
                                      month=int(fecha[4:6]),
                                      day=int(fecha[-2:]))
        if isinstance(fecha, int):
            if fecha > 0:
                self.setDate(datetime.date.today() + datetime.timedelta(days=fecha))
            else:
                self.setDate(datetime.date.today() - datetime.timedelta(days=abs(fecha)))
        else:
            self.setDate(fecha)

    def keyPressEvent(self, QKeyEvent, *args, **kwargs):
        teclaEnter = [Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab]
        if QKeyEvent.key() in teclaEnter:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QDateEdit.keyPressEvent(self, QKeyEvent, *args, **kwargs)

    def getFechaSql(self):
        fecha = str(self.text())
        fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        return fecha


class QNCalendarWidget(QtGui.QCalendarWidget):
    def __init__(self, n=3, columns=3, year=None, month=None):
        """set up

        :Parameters:
        - `self`: the widget
        - `n`: number of months to display
        - `columns`: months to display before start a new row
        - `year`: year of first calendar
        - `month`: month of first calendar
        """

        QtGui.QCalendarWidget.__init__(self)

        self.build(n, columns, year=year, month=month)

    def build(self, n=3, columns=3, year=None, month=None):

        self.calendars = []

        if year is None:
            year = datetime.date.today().year
        if month is None:
            month = datetime.date.today().month

        layout = QtGui.QGridLayout()
        while self.layout().count():
            self.layout().removeItem(self.layout().itemAt(0))
        self.layout().addLayout(layout)
        size = self.minimumSizeHint()
        x, y = size.width(), size.height()
        x *= min(n, columns)
        y *= 1 + ((n - 1) // columns)
        self.setMinimumSize(QtCore.QSize(x, y))

        for i in range(n):
            calendar = QtGui.QCalendarWidget()
            calendar.i = i
            calendar.setCurrentPage(year, month)
            month += 1
            if month == 13:
                year += 1
                month = 1
            calendar.currentPageChanged.connect(
                lambda year, month, cal=calendar:
                self.currentPageChanged(year, month, cal))
            calendar.clicked.connect(self.return_result)
            calendar.activated.connect(self.return_result)
            self.calendars.append(calendar)
            layout.addWidget(calendar, i // columns, i % columns)

    def currentPageChanged(self, year, month, cal):
        """currentPageChanged - Handle change of view

        :Parameters:
        - `self`: self
        - `year`: new year
        - `month`: new month
        - `cal`: which calendar
        """

        for i in range(cal.i):
            month -= 1
            if month == 0:
                year -= 1
                month = 12
        for calendar in self.calendars:
            calendar.setCurrentPage(year, month)
            month += 1
            if month == 13:
                year += 1
                month = 1

    activated = QtCore.pyqtSignal(QtCore.QDate)

    def return_result(self, date):
        """return_result - Return result

        :Parameters:
        - `self`: self
        - `cal`: the calendar that was activated
        """

        for i in self.calendars:
            old = i.blockSignals(True)  # stop currentPageChanged firing
            y, m = i.yearShown(), i.monthShown()
            i.setSelectedDate(date)
            i.setCurrentPage(y, m)
            i.blockSignals(old)
        self.activated.emit(date)