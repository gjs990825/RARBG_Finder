import logging
import math
import os.path
import sys
import urllib
from pathlib import Path

import pandas as pd
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView, QTableWidgetItem, QMessageBox
from pandas import DataFrame, Series

from rarbg_finder_main_window import Ui_MainWindow

logging.basicConfig(level=logging.INFO)


class RARBGData:
    FILE_PATH = r'resources/data/xrmbcsv.csv'
    CACHE_PATH = r'cache/cache.pkl'

    data: DataFrame = None
    categories = []

    def __init__(self):
        if isinstance(self.data, DataFrame):
            return
        if os.path.isfile(RARBGData.CACHE_PATH):
            self.data = pd.read_pickle(RARBGData.CACHE_PATH)
        else:
            self.data = pd.read_csv(RARBGData.FILE_PATH, parse_dates=['dt'])
            cache_directory = Path(RARBGData.CACHE_PATH).parent
            if not cache_directory.is_dir():
                cache_directory.mkdir()
            self.data.to_pickle(RARBGData.CACHE_PATH)
        self.categories = self.data.cat.unique().tolist()

    def clean_cache(self):
        if os.path.isfile(RARBGData.CACHE_PATH):
            os.remove(RARBGData.CACHE_PATH)

    @staticmethod
    def filter_title(data, name, case=False):
        return data[data['title'].str.contains(name, case=case)]

    @staticmethod
    def filter_imdb(data, imdb):
        return data[data.imdb == imdb]

    @staticmethod
    def filter_datetime(data, before, after):
        result = data
        if before:
            result = result[result.dt < before]
        if after:
            result = result[result.dt > after]
        return result

    @staticmethod
    def filter_categories(data, categories):
        if not categories:
            return data
        return data[data.cat.isin(categories)]

    def find(self, *, title=None, before=None, after=None, categories=None, imdb=None):
        result = self.data
        if title is not None:
            result = self.filter_title(result, title)
        result = self.filter_datetime(result, before, after)
        if categories:
            result = self.filter_categories(result, categories)
        if imdb is not None:
            result = self.filter_imdb(result, imdb)
        return result


def grid_position_gen(cols, rows=None):
    if rows is None:
        rows = math.inf
    r = 0
    while True:
        if r >= rows:
            raise GeneratorExit()
        for c in range(cols):
            yield r, c
        r += 1


def get_torrent_link(hash, name):
    return f'magnet:?xt=urn:btih:{hash}&dn={urllib.parse.quote(name)}'


def pretty_bytes(size):
    if pd.isna(size):
        return ''
    units = ['B', 'kB', 'MB', 'GB', 'TB']
    i = 0 if size == 0 else math.floor(math.log(size) / math.log(1024))
    return str((size / math.pow(1024, i)).__round__(2)) + ' ' + units[i]


class RARBGFinder(QtWidgets.QMainWindow, Ui_MainWindow):
    APP_NAME = 'RARBG Finder'

    def __init__(self, *args, obj=None, **kwargs):
        super(RARBGFinder, self).__init__(*args, **kwargs)

        self.ui_prepare()
        self.rarbg_data = RARBGData()
        self.checkboxes = []
        self.position_gen = grid_position_gen(6)
        for cat in self.rarbg_data.categories:
            cbx = QtWidgets.QCheckBox(cat, parent=self.scrollAreaWidgetContents)
            cbx.setChecked(True)
            self.gridLayout_2.addWidget(cbx, *next(self.position_gen))
            self.checkboxes.append(cbx)

    def get_selected_categories(self):
        return [cbx.text() for cbx in self.checkboxes if cbx.isChecked()]

    def add_row(self, item: Series):
        row = self.resultTable.rowCount()
        self.resultTable.setRowCount(row + 1)
        self.resultTable.setItem(row, 0, QTableWidgetItem(str(item['title'])))
        self.resultTable.setItem(row, 1, QTableWidgetItem(str(item['dt'])))
        self.resultTable.setItem(row, 2, QTableWidgetItem(str(item['cat'])))
        self.resultTable.setItem(row, 3, QTableWidgetItem(pretty_bytes(item['size'])))
        self.resultTable.setItem(row, 4, QTableWidgetItem(str(item['imdb'])))
        self.resultTable.setItem(row, 5, QTableWidgetItem(get_torrent_link(item['hash'], item['title'])))

    def display_results(self, results: DataFrame):
        for _, row in results.iterrows():
            self.add_row(row)
        self.resultTable.sortItems(1, Qt.SortOrder.DescendingOrder)

    def go(self):
        self.resultTable.clearContents()
        self.resultTable.setRowCount(0)
        key = self.inputTextEdit.toPlainText()
        if self.imdbRadioButton.isChecked():
            results = self.rarbg_data.find(imdb=key)
        else:
            categories = self.get_selected_categories()
            results = self.rarbg_data.find(title=key, categories=categories)

        self.display_results(results)

    def clean_cache(self):
        self.rarbg_data.clean_cache()
        QMessageBox.information(self, 'Info', 'Cache file cleared!')

    def check_all(self):
        for cbx in self.checkboxes:
            cbx.setChecked(True)

    def uncheck_all(self):
        for cbx in self.checkboxes:
            cbx.setChecked(False)

    def reverse_check(self):
        for cbx in self.checkboxes:
            cbx.setChecked(not cbx.isChecked())

    def ui_prepare(self):
        # windows and icon
        self.setupUi(self)

        self.goButton.clicked.connect(lambda: self.go())

        self.resultTable.setColumnCount(6)
        self.resultTable.setHorizontalHeaderLabels(['Title', 'Datetime', 'Category', 'Size', 'IMDb', 'Link'])
        self.resultTable.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        icon = QtGui.QIcon('resources/icon/ic_app.png')
        self.setWindowIcon(icon)

        self.actionClearCache.triggered.connect(self.clean_cache)
        self.checkAllButton.clicked.connect(self.check_all)
        self.uncheckAllButton.clicked.connect(self.uncheck_all)
        self.reverseCheckButton.clicked.connect(self.reverse_check)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = RARBGFinder()
    window.show()
    app.exec()
