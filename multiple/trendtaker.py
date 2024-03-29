
import time
import datetime
from trendtaker_core import *
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import regex # type: ignore
import datetime
import requests # type: ignore
from report import *
from ledger import Ledger
from exchange_interface import *
from configuration import *
from file_manager import *

DIRECTORY_LOGS = "./logs/"
DIRECTORY_LEDGER = "./ledger/"
DIRECTORY_GRAPHICS = "./graphics/"


DEFAULT_CURRENT_INVESTMENT = {
    "symbol": None,
    "initialPrice": None,
    "amountAsBase": None,
    "initialDateTimeAsSeconds": None,
    "ticker": None,
    "balance": None
}


DEBUG_MODE = {
    # En True, hace que se ignore el balance insuficiente.
    # Se hace para comprobar el funcionamiento del bot, sin tener en cuenta el balance.
    "ignoreInsufficientBalance": True,
    
    # En True, hace que las ordenes de compra y venta sean simuladas.
    # Esto se hace para comprobar el funcionamiento del bot, sin tener 
    # que enviar ordenes reales al exchange.
    "simulateOrderExecution": True,     
    
    # En True, hace que los mercados sean ordenados aleatoriamente, para 
    # simular como si los profits estuviesen cambiando constantemente.
    "randomMarketOrdering": False,
    
    # En True, hace que los mercados sean aceptados todos sin verificar su 
    # liquidez y crecimiento. Esto se hace para comprobar el funcionamiento 
    # del bot con los datos de los mercados, sin tener que esperar a que 
    # se encuentre un mercado que realmente sea creciente y liquido.
    "skipLiquidAndGrowingMarketCheck": True,
    
    # Para ejecutar una orden de compra con los parametros de la configuracion
    # y luego ejecutar una orden de venta para salir de la inversion y terminar. 
    # Esto se hace para comprobar el funcionamiento de las compras y ventas. 
    # Para activarlo, se debe poner el identificador del mercado. Ej: "HTH/USDT"
    # Para desactivarlo, se debe poner None
    "onlyBuyAndSell": None
}
# Esto se hace porque utilizar "randomMarketOrdering" o "skipLiquidAndGrowingMarketCheck" 
# en el mercado con ordenes reales, pues puede causar perdidas de capital.
if DEBUG_MODE["randomMarketOrdering"] or DEBUG_MODE["skipLiquidAndGrowingMarketCheck"]:
    DEBUG_MODE["simulateOrderExecution"] = True


class TrendTaker():
    
    def __init__(self, botId:str, exchangeId:str, apiKey:str, secret:str, toConsole:bool=False, toLog:bool=True):
        self.botId = botId
        self.exchangeId = exchangeId
        self.apiKey = apiKey
        self.secret = secret
        self.toConsole = toConsole
        self.toLog = toLog
        
        self.secondsToNextCheck = 5 #60
        self.listOfValidMarketsId = None
        self.config = Configuration(botId, None, None, toLog, toConsole)
        self.initialBalance = {}
        self.currentBalance = None
        self.currentInvestments = {}
        self.totalFeeAsQuote = 0


    def create_logger(self, name:str, fileName:str, filesCount:int, debugMode:bool) -> Any:
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
        
        
    def write_beat(self, fileName:str) -> bool:
        '''
        Escribe un fichero beat que contiene la fecha y hora de la escritura.\n
        Se escribe en la primera linea con el formato: year-month-day hour:minute:seconds \n
        param fileName: Nombre y ruta del fichero beat.
        param toLog: Poner a True para que se registren en el fichero log los mensajes que se generan.
        param toConsole: Poner a True para que se muestre e consola los mensajes que se generan.
        return: True si logra crear el fichero beat. False si ocurre error.
        '''
        try:
            dateTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")    
            with open(fileName, 'w') as file:
                file.write(dateTime)
                return True
        except Exception as e:
            msg1 = f'Error creando el fichero beat: "{fileName}".'
            msg2 = f'Exception: {str(e)}'
            if self.toLog:
                self.log.exception(f"{msg1} {msg2}")
            if self.toConsole:
                print(f"{msg1}\n{msg2}")
        return False


    def send_to_telegram(self, message:str, emoji:str=None, toConsole:bool=False, toLog:bool=True) -> Optional[Any]:
        '''
        Envia un mensaje a un canal, grupo o usuario.\n
        param message: String con el mensaje que se desea enviar.
        param emoji: String con los caracteres o codigos de los emojis. Ej: '\U0001F534'
        param toConsole: Poner a True para que se registren en el fichero log los mensajes que se generan.
        param toLog: Poner a True para que se muestre e consola los mensajes que se generan.
        return: Respuesta del API de Telegram o None si ocurre un error.
        '''
        if emoji is not None:
            message = emoji + message 
        try:
            response = requests.post(
                'https://api.telegram.org/bot{}/sendMessage'.format(self.config.data.get("telegramToken")), 
                json={
                    'chat_id': self.config.data.get("telegramChatId"), 
                    'text': message
                }
            )   
            return True     
        except Exception as e:
            # Informa con ERROR para no llenar el fichero log innnecesariamente con el trace back de un error de conexion.
            msg1 = f'Error enviando mensaje por Telegram.'
            msg2 = f'Exception: {str(e)}'
            if toLog:
                self.log.error(f"{msg1} {msg2}")
            if toConsole:
                print(f"{msg1}\n{msg2}")
        return False


    def create_handler_of_logging(self) -> bool:
        '''
        Crea un objeto para manejar los ficheros log\n
        Los ficheros los son creados con el nombre del bot.
        Se crea un fichero por cada dia y se mantienen por 7 dias antes de ser eliminados.
        Puede mostrar mensajes por pantalla, segun la configuracion.\n
        return: True si logra crear el manejador. False si ocurre error.
        '''
        msg1 = f'Error creando el handler del logging del bot "{self.botId}"'
        try:
            self.log = self.create_logger(self.botId, f'{DIRECTORY_LOGS}{self.botId}.log', 7, True)    
        except OSError as e: 
            if self.toConsole:
                print(f"{msg1}\OSError: {str(e)}")
            return False
        except Exception as e:
            if self.toConsole:
                print(f"{msg1}\Exception: {str(e)}")
            return False
        return True


    def get_current_balance(self) -> bool:
        '''
        Obtiene el balance actual de la cuenta y lo guarda en la propiedad "currentBalance" del la clase.
        Puede mostrar mensajes por pantalla y registrar en el log, segun la configuracion.\n
        return: True si logra obtener el balance. False si ocurre error o no lo obtiene.
        '''
        self.currentBalance = self.core.exchangeInterface.get_balance()
        if self.currentBalance is None:
            msg1 = 'Error: No se pudo obtener el balance actual de la cuenta.'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            return False
        else:
            if self.initialBalance == {}:
                self.initialBalance = self.currentBalance
            quote = self.config.data['currencyQuote']
            quoteBalance = float(self.currentBalance['free'][quote])
            msg1 = 'El balance libre actual de la cuenta es:'
            msg2 = f'El balance libre actual de {quote} es: {round(quoteBalance, 10)}'
            if self.toLog: 
                self.log.info(f"{msg1} {str(self.currentBalance)}")
                self.log.info(msg2)
            if self.toConsole: 
                TrendTakerCore.show_object(self.currentBalance['free'], f"\n{msg1}") 
                print(f"\n{msg2}")
            if not self.config.data.get("amountIsPercentOfBalance", True):
                param = "amountToInvestAsQuote"
                if quoteBalance < float(self.config.data.get(param, 10))*2 and not DEBUG_MODE["ignoreInsufficientBalance"]:
                    msg1 = f'El balance libre actual de {quote} en la cuenta no es suficiente para operar.'
                    msg2 = f'Debe reducir el valor del parametro "{param}" o aumentar el balance de la cuenta.'
                    if self.toLog: 
                        self.log.error(msg1)
                        self.log.info(msg2)
                    if self.toConsole: 
                        print(msg1)
                        print(msg2)
                    return False
            return True


    def load_markets(self) -> bool:
        '''
        Carga los datos de mercado y sus criptomonedas.\n
        Puede mostrar mensajes por pantalla y registrar en el log, segun la configuracion.\n
        return: True si logra cargar los datos de mercado. False si ocurre error o no los carga.
        '''
        if not self.core.load_markets():
            msg1 = 'Error: Cargando mercados.'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            return False
        else:
            countOfCurrencies = len(self.core.exchangeInterface.get_currencies())          
            countOfMarkets = len(self.core.exchangeInterface.get_markets())
            msg1 = f'Total de criptomonedas del exchange: {countOfCurrencies}'
            msg2 = f'Total de mercados del exchange: {countOfMarkets}'
            if self.toLog: 
                self.log.info(msg1)
                self.log.info(msg2)
            if self.toConsole: 
                print(msg1)
                print(msg2)
            return True
                
                
    def get_list_of_valid_markets(self) -> bool:
        '''
        Obtiene la lista de los mercados validos y la guarda en la propiedad "listOfValidMarketsId" de la clase.
        Los mercados validos son:\n
        - Los mercados spot en los que se puede operar compras y ventas.
        - No estan en la lista negra de mercados ni sus criptomonedas estan en la lista negra de criptomonedas.
        - Su currency quote es la seleccionada en la configuracion del bot.\n
        Puede mostrar mensajes por pantalla y registrar en el log, segun la configuracion.\n
        return: True si logra cargar los datos de mercado. False si ocurre error o no los carga.
        '''
        self.listOfValidMarketsId = self.core.get_list_of_valid_markets(
            str(self.config.data['currencyQuote']),
            self.config.data.get("blackList", None)
            )
        if self.listOfValidMarketsId is None:
            msg1 = 'Error: Filtrando mercados validos y operables.'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            return False
        else:
            countOfValidMarkets = len(self.listOfValidMarketsId)
            msg1 = f'Total de mercados validos y operables encontrados: {countOfValidMarkets}'
            msg2 = f'Mercados validos y operables encontrados: {str(self.listOfValidMarketsId)}'
            if self.toLog: 
                self.log.info(msg1)
                self.log.info(msg2)
            if self.toConsole: print(msg1)
            if countOfValidMarkets == 0:
                msg1 = 'Se necesita al menos un mercado valido y operable.'
                if self.toLog: self.log.error(msg1)
                if self.toConsole: print(msg1)
                return False
            return True

    
    def invest_in(self, symbolId:MarketId, amountAsBase:float) -> bool:
        '''
        Abre una inversion nueva comprando el activo.\n
        param symbolId: Identificador del mercado en el que se debe invertir.
        return: True si logra abrir la inversion. False si no la abre.
        '''
        market = self.core.exchangeInterface.get_markets()[symbolId]
        if market is not None:
            ticker = self.core.exchangeInterface.get_ticker(symbolId)
            if ticker is not None:
                base = self.core.exchangeInterface.base_of_symbol(symbolId)
                quote = self.core.exchangeInterface.quote_of_symbol(symbolId)
                self.currentBalance = self.core.exchangeInterface.get_balance()
                if self.currentBalance is None:
                    msg1 = 'Error: No se pudo obtener el balance actual de la cuenta.'
                    if self.toLog: self.log.error(msg1)
                    if self.toConsole: print(msg1)
                    balanceQuote = None
                else:
                    balanceQuote = self.currentBalance["free"][quote]
                
                lastPrice = float(ticker.get("last", 0))
                if lastPrice > 0:
                    if self.core.check_market_limits(market, amountAsBase, lastPrice):
                        amountAsBase = self.core.exchangeInterface.round_to_precision(amountAsBase, symbolId, "amount")
                        
                        # aqui se deberia comprobar si el amount a invertir supera al balance disponible.
                        
                        order = self.core.execute_market('buy', symbolId, amountAsBase, DEBUG_MODE["simulateOrderExecution"])
                        if order is not None:                        
                            self.currentInvestments[symbolId] = {
                                "symbol": symbolId,
                                "initialPrice": order["average"],
                                "amountAsBase": order["amount"],
                                "initialDateTimeAsSeconds": self.core.exchangeInterface.exchange.seconds(),
                                "fee": order["fee"]["cost"],
                                "ticker": ticker,
                                "balance": self.currentBalance
                            }
                            FileManager.data_to_file_json(self.currentInvestments, self.currentInvestmentsFileName, self.log, self.toConsole)
                            self.totalFeeAsQuote += float(order["fee"]["cost"])
                            
                            self.ledger.write(order, balanceQuote)
                            
                            msg1 = f'INVERSION ABIERTA en {symbolId}'
                            msg2 = f'cantidad comprada: {order["filled"]} {base}'
                            msg3 = f'valor aproximado: {float(order["filled"]) * float(order["average"])} {quote}'
                            msg4 = f'precio de compra: {order["average"]} {quote}'
                            if self.toLog: 
                                self.log.info(f'{msg1} {msg2} {msg3} {msg4}')
                            if self.toConsole: 
                                print(f'\n{msg1}\n   {msg2}\n   {msg3}\n   {msg4}\n')
                            return True
                else:
                    msg1 = f'Error: No se pudo obtener el precio del ticker del mercado {symbolId}'
                    if self.toLog: self.log.error(f'{msg1}. Ticker: {ticker}')
                    if self.toConsole: print(msg1)
            else:
                msg1 = f'Error: No se pudo obtener el ticker del mercado {symbolId}'
                if self.toLog: self.log.error(msg1)
                if self.toConsole: print(msg1)
        else:
            msg1 = f'Error: No se pudieron obtener los datos del mercado {symbolId}'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
        msg1 = f'Error: No se pudo invertir en el mercado {symbolId}'
        if self.toLog: self.log.error(msg1)
        if self.toConsole: print(msg1)
        #Se deberia informar esto por otra via adicional.
        return False

    
    def close_current_investment(self, symbolId:MarketId) -> bool:
        '''
        Cierra la inversion actual vendiendola al instante.
        Vende la misma cantidad de activo que se compro al momento de invertir.\n
        return: True si logra cerrar la inversion. False si no la cierra.
        '''
        if symbolId not in self.currentInvestments:
            msg1 = f'Error: No se encuentran datos de la inversion actual en el mercado {symbolId}'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            return False
        investment = self.currentInvestments[symbolId]
        if symbolId is not None:
            market = self.core.exchangeInterface.get_markets()[symbolId]
            if market is not None:
                ticker = self.core.exchangeInterface.get_ticker(symbolId)
                if ticker is not None:
                    base = self.core.exchangeInterface.base_of_symbol(symbolId)
                    quote = self.core.exchangeInterface.quote_of_symbol(symbolId)
                    self.currentBalance = self.core.exchangeInterface.get_balance()
                    if self.currentBalance is None:
                        msg1 = 'Error: No se pudo obtener el balance actual de la cuenta.'
                        if self.toLog: self.log.error(msg1)
                        if self.toConsole: print(msg1)
                        balanceQuote = None
                    else:
                        balanceQuote = self.currentBalance["free"][quote]
                    
                    amountAsBase = float(investment['amountAsBase'])
                    lastPrice = float(ticker.get("last", 0))
                    if lastPrice > 0:
                        initialPrice = float(investment['initialPrice'])

                        order = self.core.execute_market('sell', symbolId, amountAsBase, DEBUG_MODE["simulateOrderExecution"])
                        if order is not None:                        
                            try:
                                profit = round((float(order["average"]) - initialPrice) / initialPrice * 100, 2)
                            except:
                                profit = None
                            try:
                                current = float(self.currentBalance['free'][quote])
                                initial = float(self.initialBalance['free'][quote])
                                profitTotal = round((current - initial) / initial * 100, 2)
                            except:
                                profitTotal = None
                            dateTimeAsSeconds = self.core.exchangeInterface.exchange.seconds()
                            hours = (dateTimeAsSeconds - investment['initialDateTimeAsSeconds']) / (60 * 60)
                            hoursTotal = (dateTimeAsSeconds - self.initialExecutionDateTimeAsSeconds) / (60 * 60)
                            
                            del self.currentInvestments[symbolId]
                            FileManager.data_to_file_json(self.currentInvestments, self.currentInvestmentsFileName, self.log, self.toConsole)
                            self.totalFeeAsQuote += float(order["fee"]["cost"])

                            self.ledger.write(order, balanceQuote)
                            
                            msg1 = f'INVERSION CERRADA en {symbolId}'
                            msg2 = f'cantidad vendida: {order["filled"]} {base}'
                            msg3 = f'valor aproximado: {float(order["filled"]) * float(order["average"])} {quote}'
                            msg4 = f'precio de compra: {initialPrice} {quote}'
                            msg5 = f'precio de venta: {order["average"]} {quote}'
                            msg6 = f'profit de inversion: {profit}% en {round(hours, 2)} horas'
                            msg7 = f'profit total: {profitTotal}% en {round(hoursTotal, 2)} horas'
                            msg8 = f'fee total: {round(self.totalFeeAsQuote, 2)} {quote} en {round(hoursTotal, 2)} horas'
                            if self.toLog: 
                                self.log.info(f'{msg1} {msg2} {msg3} {msg4} {msg5} {msg6} {msg7} {msg8}')
                            if self.toConsole: 
                                print(f'\n{msg1}\n   {msg2}\n   {msg3}\n   {msg4}\n   {msg5}\n   {msg6}\n   {msg7}\n   {msg8}\n')
                            return True
                    else:
                        msg1 = f'Error: No se pudo obtener el precio del ticker del mercado {symbolId}'
                        if self.toLog: self.log.error(f'{msg1}. Ticker: {ticker}')
                        if self.toConsole: print(msg1)                    
                else:
                    msg1 = f'Error: No se pudo obtener el ticker del mercado {symbolId}'
                    if self.toLog: self.log.error(msg1)
                    if self.toConsole: print(msg1)
            else:
                msg1 = f'Error: No se pudieron obtener los datos del mercado {symbolId}'
                if self.toLog: self.log.error(msg1)
                if self.toConsole: print(msg1)
            msg1 = f'Error: No se pudo cerrar la inversion en el mercado {symbolId}'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            #Se deberia informar esto por otra via adicional.
            return False
        else:
            return True
    
    
    def is_valid_current_investment_structure(self, data) -> bool:
        '''
        Verifica que la estructura de los datos de la inversion actual sea correcta.
        Se comprueba que existan todos los parametros.\n
        param data: Datos a los que se les debe verificar y comprobar la estructura.
        return: True si los datos son correctos. De lo contrario devuelve False.
        '''
        try:
            if data.get("symbol", None) is None: return False
            if data.get("initialPrice", None) is None: return False
            if data.get("amountAsBase", None) is None: return False
            if data.get("initialDateTimeAsSeconds", None) is None: return False
            if data.get("fee", None) is None: return False
            if data.get("ticker", None) is None: return False
            if data.get("balance", None) is None: return False
            return True
        except Exception as e:
            msg1 = f'Error en los datos de la inversion actual. Exception: {str(e)}'
            if self.toLog: self.log.exception(msg1)
            if self.toConsole: print(msg1)
            return False
    
    
    def load_current_investment(self) -> bool:
        '''
        Carga desde un fichero los datos de la inversion actual en curso.\n
        Esto permite que si el bot es detenido despues de abriri una inversion, al iniciarse
        nuevamente pueda retomar el funcionamiento y continuar verificando la inversion o 
        cerrarla en caso que sea necesario.\n
        return: True si encuentra un fichero y logra cargar los datos. False si no se cargan datos.
        '''
        currentInvestmentData = FileManager.data_from_file_json(self.currentInvestmentsFileName, False, self.log, self.toConsole)
        if currentInvestmentData is not None:
            msg1 = f'Se ha encontrado un fichero de datos de inversiones actuales": "{self.currentInvestmentsFileName}"'
            if self.toLog: self.log.info(msg1)
            if self.toConsole: print(msg1)
            if type(currentInvestmentData) != Dict:
                msg1 = 'Error: La estructura del fichero de datos de inversiones actuales no es correcta.'
                if self.toLog: self.log.error(msg1)
                if self.toConsole: print(msg1)
                return False
            if len(currentInvestmentData) == 0:
                msg1 = 'El fichero de datos de inversiones actuales no contiene datos.'
                if self.toLog: self.log.error(msg1)
                if self.toConsole: print(msg1)
                return True
            else:
                msg1 = f'Cantidad de inversiones actuales: {len(currentInvestmentData)}'
                if self.toLog: self.log.error(msg1)
                if self.toConsole: print(msg1)
            for index in currentInvestmentData.keys():
                investment = currentInvestmentData[index]
                if self.is_valid_current_investment_structure(investment): 
                    symbolId = investment["symbol"]
                    base = self.core.exchangeInterface.base_of_symbol(investment["symbol"])
                    quote = self.core.exchangeInterface.quote_of_symbol(investment["symbol"])                                
                    msg1 = f'Inversion actual en {investment["symbol"]}'
                    msg2 = f'cantidad comprada: {investment["amountAsBase"]} {base}'
                    msg3 = f'precio de compra: {investment["initialPrice"]} {quote}'
                    if self.toLog: 
                        self.log.info(f'{msg1} {msg2} {msg3}')
                    if self.toConsole: 
                        print(f'\n{msg1}\n   {msg2}\n   {msg3}\n')

                    self.currentInvestments[symbolId] = investment
                    #self.initialExecutionDateTimeAsSeconds = data["initialDateTimeAsSeconds"] # debe quedarse con el mas antiguo.
                    msg1 = f'Se han cargado los datos de la iversion actual en {symbolId}.'
                    if self.toLog: self.log.info(msg1)
                    if self.toConsole: print(msg1)
                else:
                    msg1 = f'Error en los datos de la inversion en el mercado {symbolId}'
                    if self.toLog: self.log.error(msg1)
                    if self.toConsole: print(msg1)
        return False
    
        
    def prepare_execution(self) -> bool:
        '''
        - Prepara e inicia las variables del algoritmo para su ejecucion.
        - Crea los directorios necesarios si no existen.
        - Crea el handler de los ficheros log.
        - Crea el objeto core que contiene funciones basicas y de acceso al exchange.
        - Inicia el libro mayor (ledger)
        - Carga la configuracion desde un fichero si existe.
        - Obtiene el balance inicial de la cuenta.
        - Carga la lista de los mercados del exchange y filtra los validos.
        - Carga desde un fichero los datos de la inversion actual en curso.\n
        return: True si logra preparar la ejecucion. False si ocurre error y se debe abortar.
        '''
        Report.prepare_directory(DIRECTORY_LOGS)
        Report.prepare_directory(DIRECTORY_LEDGER)
        Report.prepare_directory(DIRECTORY_GRAPHICS)
        
        if self.create_handler_of_logging():
            msg1 = f'Iniciando bot: {self.botId}'
            if self.toLog: self.log.info(msg1)
            if self.toConsole: print(f'\n{msg1}')
            self.core = TrendTakerCore(self.exchangeId, self.apiKey, self.secret, self.log, self.toLog, self.toConsole)
            msg1 = f'exchangeId: {self.exchangeId}'
            if self.toLog: self.log.info(msg1)
            if self.toConsole: print(msg1)
            self.config.log = self.log
            self.config.core = self.core
            
            if self.core.exchangeInterface.check_exchange_methods(True):
                self.ledger = Ledger(self.botId, DIRECTORY_LEDGER, self.log, self.toLog, self.toConsole)            
                if self.config.load():
                    time.sleep(1)
                    if self.get_current_balance():
                        time.sleep(1)
                        if self.load_markets():
                            if self.get_list_of_valid_markets():
                                self.initialExecutionDateTimeAsSeconds = self.core.exchangeInterface.exchange.seconds()
                                self.currentInvestmentsFileName = f'./{self.botId}_current_investment.json'
                                if self.load_current_investment():
                                    time.sleep(1)
                                    '''
                                    self.currentBalance = self.currentInvestment["balance"]
                                    self.totalFeeAsQuote = self.currentInvestment["fee"]
                                    self.initialBalance = self.currentBalance
                                    quote = self.config.data['currencyQuote']
                                    quoteBalance = float(self.initialBalance['free'][quote])
                                    msg1 = 'Los calculos de profit seran realizados con los datos de la iversion actual en curso.'                                
                                    msg2 = 'El balance libre al inicio de la iversion actual es:'
                                    msg3 = f'El balance libre de {quote} al inicio de la iversion actual es: {round(quoteBalance, 10)}'
                                    if self.toLog: 
                                        self.log.info(msg1)
                                        self.log.info(f"{msg2} {str(self.initialBalance)}")
                                        self.log.info(msg3)
                                    if self.toConsole: 
                                        print(f"{msg1}")                                
                                        TrendTakerCore.show_object(self.initialBalance['free'], f"\n{msg2}") 
                                        print(f"\n{msg3}")         
                                        time.sleep(1)       
                                    time.sleep(1)
                                    '''           
                                return True
        msg1 = 'Terminado: No se puede continuar.'
        if self.toLog: self.log.info(msg1)
        if self.toConsole: print(msg1)
        return False


    def only_buy_and_sell(self):
        '''
        Hace pruebas de operaciones de compra y venta\n
        Si en DEBUG_MODE esta establecido el parametro el "onlyBuyAndSell", se ejecuta una orden de compra 
        con los parametros de la configuracion y luego ejecutar una venta para salir de la inversion y terminar.\n
        Nota: Esto se hace para comprobar el funcionamiento de las compras y ventas.\n
        return: True si logra ejecutar las ordenes de compra y venta correctamente. False si ocurre error.
        '''
        if DEBUG_MODE["onlyBuyAndSell"] is not None:
            self.invest_in(str(DEBUG_MODE["onlyBuyAndSell"]))
            time.sleep(1)
            self.close_current_investment()  
            if self.toLog: self.log.info('Terminado')
            if self.toConsole: print('Terminado')
            return True
        return False
            

    def force_close_investment_and_exit(self):
        '''
        Cierra todas las inversiones abiertas\n
        Si en la configuracion esta establecido el parametro el "forceCloseInvestmentAndExit", 
        se ejecutan ordenes de venta para cerrar todas las las inversiones abiertas.\n
        return: True si logra cerrar correctamente las inversiones abiertas. False si ocurre error.
        '''
        if self.config.data.get("forceCloseInvestmentAndExit", False):
            msg1 = '\nATENCION: La configuracion del bot indica que deben cerrarse todas las inversiones inmediatamente.'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            if len(self.currentInvestments) > 0:
                for symbolId in self.currentInvestments.keys():
                    self.close_current_investment(symbolId)
            msg1 = 'Terminado: Se ha finalizado la ejecucion.'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            return True
        return False
        

    def execute(self) -> bool:
        '''
        Ejecuta el algoritmo de inversion del bot.\n
        Primero prepara las variables y recursos necesarios para iniciar la ejecucion y luego 
        entra en un bucle infinito donde se obtienen regularmente datos del mercado y se determina
        si se debe invertir o no en un activo.
        '''
        if not self.prepare_execution():
            return False
        if self.only_buy_and_sell():
            return True
        if self.force_close_investment_and_exit():
            return True
        report = Report(self.core, self.botId, self.exchangeId, self.log, self.toLog, self.toConsole, DIRECTORY_GRAPHICS, "png")
        validTickers = self.core.get_ordered_and_filtered_tickers(self.listOfValidMarketsId, self.config.data)
        if validTickers is None: 
            return False
        orderedMarkets = self.core.get_ordered_and_filtered_markets(validTickers, self.config.data)
        if orderedMarkets is None: 
            return False
        for marketData in orderedMarkets:
            symbolId = marketData["symbolId"]
            msg1 = f"Mercado potencial en: {symbolId}  crecimiento en 24h: {round(float(marketData['tickerData']['percentage']), 2)} %"
            if self.toConsole: print(msg1)
            if self.toLog: self.log.info(msg1)                                
            lastPrice = float(marketData["tickerData"]["last"])
            amountToInvestAsQuote = float(self.config.data.get("amountToInvestAsQuote", 10))
            amountToInvestAsBase = amountToInvestAsQuote / lastPrice 
            if not self.core.check_market_limits(marketData["symbolData"], amountToInvestAsBase, lastPrice):
                fileName = report.create_unique_filename()
                title = f'{self.botId} {self.exchangeId} {symbolId}'
                report.create_graph(marketData["candles1h"], title, fileName, marketData["metrics"], False) 
                #if report.count_market_data() >= 10: break              
                category:Category = "potentialMarket"             
                if symbolId in self.currentInvestments:
                    # Si el mercado potencial seleccionado es el mismo en el que ya se ha invertido, no se hace nada y se procede a continuar verificando el estado de esa inversion.
                    pass
                    # Si ha superado el tiempo especifico para la imversio, deve termimarlo
                    #if not self.close_current_investment(symbolId):   
                    #    category = "closedInvest"  
                else:
                    pass
                    #if self.invest_in(symbolId, amountToInvestAsBase):
                    #    category = "openInvest"
                report.append_market_data(fileName, marketData["metrics"], category)
        if self.config.data["createWebReport"]:
            report.create_web(self.config.data["showWebReport"])
        if len(self.currentInvestments) == 0:
            msg1 = 'SIN INVERTIR: No se han encontrado mercados favorables.'
            if self.toLog: self.log.info(msg1)
            if self.toConsole: print(msg1)
        if self.toLog: self.log.info('Terminado')
        if self.toConsole: print('Terminado')
        return True


if __name__ == "__main__":
    credentials = json.loads(open('D:/1-Lineas/2 - Cryptos/automatic 2024/credential_hitbtc.json').read())
    #credentials = json.loads(open('D:/1-Lineas/2 - Cryptos/automatic 2024/credential_bingx.json').read())
    bot = TrendTaker('TrendTaker1', credentials['exchange'], credentials['key'], credentials['secret'], True, True)
    bot.execute()    
