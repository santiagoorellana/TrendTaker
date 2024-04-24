

import datetime
from exchange_interface import *
from file_manager import *
from basics import *
import logging
from csv_base import CsvBase


class FileLedger(CsvBase):
    
    def __init__(self, botId:str, directory:str='./'):
        '''
        Crea un objeto para manejar el fichero del Libro Mayor.
        param fileName: Nombre del fichero del Libro Mayor (ledger).
        '''
        self.botId = botId
        self.directory = directory
        dateTimeLabel = datetime.datetime.now().strftime("%Y%m")
        CsvBase.__init__(
            self,
            f'{self.directory}{self.botId}_ledger_{dateTimeLabel}.csv', 
            ['datetimeUTC', 'symbol', 'side', 'amountAsBase', 'amountAsQuote', 'price', 'feeAsQuote'], 
            logging.getLogger(botId)
        )

    
            

    def _csv_line_from(self, data) -> str:
        '''
        Crea una linea CSV a partir de los datos de una orden creada con la libreria CCXT.
        param argv: Debe contener dos parametros: El primero son los datos de una orden creada 
        con la libreria CCXT. El segundo es el balance existente en la cuenta de trading.
        return: Devuelve una cadena con los valores de la orden y balance separados por coma.
        '''
        return self._csv_line([
            str(data["datetime"]), 
            str(data["symbol"]), 
            str(data["side"]), 
            str(data["filled"]), 
            str(float(data["filled"]) * float(data["average"])), 
            str(data["average"]), 
            str(data["fee"]["cost"])
        ])

        