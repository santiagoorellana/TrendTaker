
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import regex # type: ignore
from typing import List, Any, Dict, Union, Literal, Optional

INDENT = str("   ")

# Definiciones de datos de la libreria CCXT

Candle = List[Union[int, float]]
ListOfCandles = List[Candle]

Ticker = Dict
DictOfTickers = Dict

SymbolId = str
MarketId = SymbolId
ListOfMarketsId = List[MarketId]
Market = Dict
DictOfMarkets = Dict

CurrencyId = str
ListOfCurrenciesId = List[CurrencyId]
Currency = Dict
DictOfCurrencies = Dict

Balance = Dict
Order = Dict

PrecisionType = Literal["price", "amount", "cost"]
Side = Literal["buy", "sell"]
AmountLimit = Literal["min", "max"]

# Definiciones de datos propios del TrendTaker

ListOfTickers = List[Ticker]
CurrentInvestments = Dict
ConfigurationData = Dict
Filters = Dict
MarketData = Dict
ListOfMarketData = List[MarketData]
ComparisonCondition = Literal["above", "below"]
Slice = Literal["whole", "lastHalf", "lastQuarter"]
Category = Literal["potentialMarket", "openInvest", "closedInvest"]
Formats = Literal["png", "jpg", "jpeg", "webp", "svg", "pdf"]


class Basics():
    
    @staticmethod 
    def cmd(message:str, prefix:str="", suffix:str=""):
        '''
        Imprime en consola un mensaje de texto.
        param message: Mensaje de texto que se debe mostrar en la consola CMD.
        param prefix: Cadena de texto que solo se agrega delante del texto que se imprime en pantalla.
        param suffix: Cadena de texto que solo se agrega detras del texto que se imprime en pantalla.
        return: Devuelve el mismo mensaje.
        '''
        print(f"{prefix}{message}{suffix}")
        return message


    @staticmethod 
    def create_logger(name:str, fileName:str, filesCount:int, debugMode:bool) -> logging.Logger:
        '''
        Prepara la configuracion del logging para guardar mensajes en fichero
        de manera que se crea un fichero por cada dia de la semana.
        La linea que se agrega al fichero logging, contendra el nombre del script,
        la funcion o metodo y el numero de la linea donde se reporta el mensaje.\n
        param fileName: jhgjh
        param filesCount: jhgjhg
        param debugMode: jhgjh
        return: kgjh
        '''
        LOG_FORMAT = '%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)04d - %(message)s'
        handler = TimedRotatingFileHandler(fileName, when="midnight", backupCount=filesCount) 
        handler.setLevel(logging.DEBUG if debugMode else logging.INFO)
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        handler.suffix = "%Y%m%d"       # Este es el sufijo del nombre de fichero.
        handler.extMatch = regex.compile(r"^\d{8}$")   
        log = logging.getLogger(name)
        logging.root.setLevel(logging.NOTSET)
        log.addHandler(handler)
        return log


    @staticmethod
    def decimal_string(value:float) -> str:
        '''
        Devuelve la cadena que representa al valor solo con los decimales sigificativos.
        Esta funcion garantiza tambien que el numero no sea mostrado como notacion cientifica.
        param value: Numero con decimales que se debe representar como cadena.
                    Solo se representan hasta 15 decimales. Cualquier valor con
                    mas de 15 decimales, sera redondeado a 15 decimales.
        return: Devuelve una cadena qeu representa al numero con solo los decimales significativos.
        '''
        completed = False
        result = ""
        valueStr = "{:.15f}".format(value).strip()[::-1]
        for index in range(len(valueStr)):
            char = valueStr[index]
            if char == "." and not completed:
                result += "0"
                completed = True
            if char != "0" or completed:
                result += char
                completed = True
        return str(result[::-1])


    @staticmethod
    def show_object(data:Any, title:str="", ident:str=INDENT, level:int=1) -> bool:
        """
        Muestra los datos de un json. 
        param data: Objeto que se debe mostrar en consola.
        param title: Titulo que precede a los datos del objeto que se muestra.
        param ident: Caracteres que se ponen delante de cada linea para indentar.
        param level: Nivel de indentacion en que se muestran los datos.
        return: True si logra mostrar los datos del objeto. False si ocurre error.
        """
        try:
            if type(data) == dict or type(data) == list or type(data) == tuple:
                if title != "":
                    print(f"{str(ident) * (level - 1)}{title}")
                if type(data) == dict:
                    for key in data.keys():
                        time.sleep(0.1)
                        Basics.show_object(data[key], key, ident=ident, level=level+1)
                else:
                    count = 0
                    for element in data:
                        time.sleep(0.1)
                        Basics.show_object(element, f'elemento {count}', ident=ident, level=level+1) 
                        count += 1
            else:
                print(f"{str(ident) * (level - 1)}{title}: {str(data)}") 
            return True
        except:
            return False               


