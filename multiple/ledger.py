
import os
import datetime
from exchange_interface import *


class Ledger():
    
    def __init__(self, botId:str, directory:str='./', log:Any=None, toLog:bool=True, toConsole:bool=False):
        '''
        Crea un objeto para manejar el fichero del Libro Mayor.
        param fileName: Nombre del fichero del Libro Mayor (ledger).
        '''
        self.headers = ['dateTime', 'symbol', 'side', 'amountAsBase', 'amountAsQuote', 'price', 'feeAsQuote', 'balanceQuote']
        dateTimeLabel = datetime.datetime.now().strftime("%Y%m")
        self.botId = botId
        self.directory = directory
        self.log = log
        self.toLog = toLog
        self.toConsole = toConsole
        self.fileName = f'{self.directory}{self.botId}_ledger_{dateTimeLabel}.csv'
        if not os.path.isfile(self.fileName):
            self._create_ledger_file()


    def write(self, order:Order, balanceQuote:float) -> bool:
        '''
        Escribe una linea con los datos de una orden, en el fichero del Libro Mayor (ledger).
        param order: Datos de una orden creada con la libreria CCXT.
        param balanceQuote: Balance existente en la cuenta de trading.
        return: Devuelve True si logra escribir el dato en Libro Mayor. De lo contrario devuelve False.
        '''
        if not os.path.isfile(self.fileName):
            return self._data_to_file_text(self._csv_line_from(order, balanceQuote), self.fileName)
        else:
            msg1 = f'No existe el Libro Mayor (ledger): "{self.fileName}"'
            if self.toLog: self.log.exception(msg1)
            if self.toConsole: print(msg1)
            return self._create_ledger_file()
    
    
    def _create_ledger_file(self) -> bool:
        '''
        Crea un nuevo fichero de Libro Mayor (ledger).
        return: Devuelve True si logra crear el Libro Mayor. De lo contrario devuelve False.
        '''
        if self._data_to_file_text(self._csv_line(self.headers), self.fileName):
            msg1 = f'Se ha creado un nuevo Libro Mayor (ledger) en: "{self.fileName}"'
            if self.toLog: self.log.exception(msg1)
            if self.toConsole: print(msg1)
            return True
        else:
            return False
        

    def _csv_line_from(self, order:Order, balanceQuote:float) -> str:
        '''
        Crea una linea CSV a partir de los datos de una orden creada con la libreria CCXT.
        param order: Datos de una orden creada con la libreria CCXT.
        param balanceQuote: Balance existente en la cuenta de trading.
        return: Devuelve una cadena con los valores de la orden y balance separados por coma.
        '''
        return self._csv_line([
            str(order["datetime"]), 
            str(order["symbol"]), 
            str(order["side"]), 
            str(order["filled"]), 
            str(float(order["filled"]) * float(order["average"])), 
            str(order["average"]), 
            str(order["fee"]["cost"]), 
            str(balanceQuote)
        ])


    def _csv_line(self, valuesList:List[str], separator:str=",", endLine:str="") -> str:
        '''
        Crea una linea CSV de los valores de la lista, con el separador y final de linea especificados.
        param valuesList: Lista de los valores para crear la linea CSV.
        param separator: Caracter separador de los valores.
        param endLine: Caracter que marca el final de la linea.
        return: Devuelve una cadena en formato CSV con los valores de la lista.        
        '''
        line = separator.join(valuesList)
        return line + endLine + '\n'


    def _data_to_file_text(self, line:str, fileName:str) -> bool:
        '''
        Escribe en un fichero de texto la cadena de texto.
        param line: Cadena que contiene el texto.
        param fileName: Nombre y ruta del fichero que se debe crear.
        return: True si logra crear el fichero. False si ocurre error.
        '''
        try:
            with open(fileName, 'a') as file:
                file.write(line)
                return True
        except Exception as e:
            msg1 = f'Error creando el fichero: "{fileName}".'
            msg2 = f'Exception: {str(e)}'
            if self.toLog:
                self.log.exception(f"{msg1} {msg2}")
            if self.toConsole:
                print(f"{msg1}\n{msg2}")
        return False

        