
import datetime
from exchange_interface import *
from file_manager import *
from basics import *
import logging
from csv_base import CsvBase


class FileInvestments(CsvBase):
    
    def __init__(self, botId:str, directory:str='./'):
        '''
        Crea un objeto para manejar el fichero de inversiones.
        param fileName: Nombre del fichero de inversiones.
        '''
        self.botId = botId
        self.directory = directory
        dateTimeLabel = datetime.datetime.now().strftime("%Y%m")
        CsvBase.__init__(
            self,
            f'{self.directory}{self.botId}_investments_{dateTimeLabel}.csv', 
            ['datetimeUTC', 'hours', 'symbol', 'profitAsPercent', 'profitAsQuote', 'priceOpen', 'priceClose'], 
            logging.getLogger(botId)
        )

    
            

    def _csv_line_from(self, data) -> str:
        '''
        Crea una linea CSV a partir de los datos de una inversion.
        param argv: Datos de una inversion realizada. 
        return: Devuelve una cadena con los valores de la inversion separados por coma.
        '''
        return self._csv_line([
            str(data["initial"]["datetimeUTC"]), 
            str(data["result"]["hours"]), 
            str(data["symbol"]), 
            str(data["result"]["profitAsPercent"]), 
            str(data["result"]["profitAsQuote"]), 
            str(data["buy"]["price"]), 
            str(data["sell"]["price"])
        ])

