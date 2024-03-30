
import time
from trendtaker_core import *
import json
from report import *
from ledger import Ledger
from exchange_interface import *
from configuration import *
from file_manager import *
from basics import *

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


class TrendTaker(Basics):
    
    def __init__(self, botId:str, exchangeId:str, apiKey:str, secret:str):
        self.botId = botId
        self.exchangeId = exchangeId
        self.apiKey = apiKey
        self.secret = secret
        
        self.secondsToNextCheck = 5 #60
        self.listOfValidMarketsId = None
        self.config = Configuration(botId, None)
        self.initialBalance = {}
        self.currentBalance = None
        self.currentInvestments = {}
        self.totalFeeAsQuote = 0
        
    
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
            self.cmd(f"{msg1}\OSError: {str(e)}")
            return False
        except Exception as e:
            self.cmd(f"{msg1}\Exception: {str(e)}")
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
            self.log.error(self.cmd(msg1))
            return False
        else:
            if self.initialBalance == {}:
                self.initialBalance = self.currentBalance
            quote = self.config.data['currencyQuote']
            quoteBalance = float(self.currentBalance['free'][quote])
            msg1 = 'El balance libre actual de la cuenta es:'
            self.log.info(f"{msg1} {str(self.currentBalance)}")
            TrendTakerCore.show_object(self.currentBalance['free'], f"\n{msg1}") 
            self.log.info(self.cmd(f'El balance libre actual de {quote} es: {round(quoteBalance, 10)}', "\n"))
            if not self.config.data.get("amountIsPercentOfBalance", True):
                param = "amountToInvestAsQuote"
                if quoteBalance < float(self.config.data.get(param, 10))*2 and not DEBUG_MODE["ignoreInsufficientBalance"]:
                    self.log.error(self.cmd(f'El balance libre actual de {quote} en la cuenta no es suficiente para operar.'))
                    self.log.info(self.cmd(f'Debe reducir el valor del parametro "{param}" o aumentar el balance de la cuenta.'))
                    return False
            return True


    def load_markets(self) -> bool:
        '''
        Carga los datos de mercado y sus criptomonedas.\n
        return: True si logra cargar los datos de mercado. False si ocurre error o no los carga.
        '''
        return self.core.load_markets()
                
                
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
            self.log.error(self.cmd('Error: Filtrando mercados validos y operables.'))
            return False
        else:
            countOfValidMarkets = len(self.listOfValidMarketsId)
            self.log.info(self.cmd(f'Total de mercados validos y operables encontrados: {countOfValidMarkets}'))
            self.log.info(f'Mercados validos y operables encontrados: {str(self.listOfValidMarketsId)}')
            if countOfValidMarkets == 0:
                self.log.error(self.cmd('Se necesita al menos un mercado valido y operable.'))
                return False
            return True

    
    def invest_in(
            self, 
            symbolId:MarketId, 
            amountAsBase:float=None, 
            profitPercent:float=None, 
            maxLossPercent:float=None, 
            maxHours:float=None
        ) -> bool:
        '''
        Abre una inversion nueva comprando el activo.\n
        param symbolId: Identificador del mercado en el que se debe invertir.
        param amountAsBase: Cantidad de moneda base que se debe comprar para invertir.
        param profitPercent: Porciento de ganancia con que se espera cerrar la inversion.
        param maxLossPercent: Maximo porciento de perdida que se va a tolerar.
        param maxHours: Cantidad maxima de horas que puede estar abierta la inversion.
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
                    self.log.error(self.cmd('Error: No se pudo obtener el balance actual de la cuenta.'))
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
                            FileManager.data_to_file_json(self.currentInvestments, self.currentInvestmentsFileName, self.log)
                            self.totalFeeAsQuote += float(order["fee"]["cost"])
                            
                            self.ledger.write(order, balanceQuote)
                            
                            msg1 = f'INVERSION ABIERTA en {symbolId}'
                            msg2 = f'cantidad comprada: {order["filled"]} {base}'
                            msg3 = f'valor aproximado: {float(order["filled"]) * float(order["average"])} {quote}'
                            msg4 = f'precio de compra: {order["average"]} {quote}'
                            self.log.info(f'{msg1} {msg2} {msg3} {msg4}')
                            self.cmd(f'\n{msg1}\n   {msg2}\n   {msg3}\n   {msg4}\n')
                            return True
                else:
                    msg1 = f'Error: No se pudo obtener el precio del ticker del mercado {symbolId}'
                    self.log.error(f'{self.cmd(msg1)}. Ticker: {ticker}')
            else:
                self.log.error(self.cmd(f'Error: No se pudo obtener el ticker del mercado {symbolId}'))
        else:
            self.log.error(self.cmd(f'Error: No se pudieron obtener los datos del mercado {symbolId}'))
        self.log.error(self.cmd(f'Error: No se pudo invertir en el mercado {symbolId}'))
        return False

    
    def close_investment(self, symbolId:MarketId) -> bool:
        '''
        Cierra la inversion actual vendiendola al instante.
        Vende la misma cantidad de activo que se compro al momento de invertir.\n
        return: True si logra cerrar la inversion. False si no la cierra.
        '''
        if symbolId not in self.currentInvestments:
            self.log.error(self.cmd(f'Error: No se encuentran datos de la inversion actual en el mercado {symbolId}'))
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
                        self.log.error(self.cmd('Error: No se pudo obtener el balance actual de la cuenta.'))
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
                            FileManager.data_to_file_json(self.currentInvestments, self.currentInvestmentsFileName, self.log)
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
                            self.log.info(f'{msg1} {msg2} {msg3} {msg4} {msg5} {msg6} {msg7} {msg8}')
                            self.cmd(f'\n{msg1}\n   {msg2}\n   {msg3}\n   {msg4}\n   {msg5}\n   {msg6}\n   {msg7}\n   {msg8}\n')
                            return True
                    else:
                        msg1 = f'Error: No se pudo obtener el precio del ticker del mercado {symbolId}'
                        self.log.error(f'{self.cmd(msg1)}. Ticker: {ticker}')                 
                else:
                    self.log.error(self.cmd(f'Error: No se pudo obtener el ticker del mercado {symbolId}'))
            else:
                self.log.error(self.cmd(f'Error: No se pudieron obtener los datos del mercado {symbolId}'))
            self.log.error(self.cmd(f'Error: No se pudo cerrar la inversion en el mercado {symbolId}'))
            return False
        else:
            return True
    
        
    def load_current_investment(self) -> bool:
        '''
        Carga desde un fichero los datos de la inversion actual en curso.\n
        Esto permite que si el bot es detenido despues de abriri una inversion, al iniciarse
        nuevamente pueda retomar el funcionamiento y continuar verificando la inversion o 
        cerrarla en caso que sea necesario.\n
        return: True si encuentra un fichero y logra cargar los datos. False si no se cargan datos.
        '''
        currentInvestmentData = FileManager.data_from_file_json(self.currentInvestmentsFileName, False, self.log)
        if currentInvestmentData is not None:
            msg1 = f'Se ha encontrado un fichero de datos de inversiones actuales": "{self.currentInvestmentsFileName}"'
            self.log.info(self.cmd(msg1))
            if type(currentInvestmentData) != Dict:
                self.log.error(self.cmd('Error: La estructura del fichero de datos de inversiones actuales no es correcta.'))
                return False
            if len(currentInvestmentData) == 0:
                self.log.error(self.cmd('El fichero de datos de inversiones actuales no contiene datos.'))
                return True
            else:
                self.log.error(self.cmd(f'Cantidad de inversiones actuales: {len(currentInvestmentData)}'))
            for index in currentInvestmentData.keys():
                investment = currentInvestmentData[index]
                if self.is_valid_current_investment_structure(investment): 
                    symbolId = investment["symbol"]
                    base = self.core.exchangeInterface.base_of_symbol(investment["symbol"])
                    quote = self.core.exchangeInterface.quote_of_symbol(investment["symbol"])                                
                    msg1 = f'Inversion actual en {investment["symbol"]}'
                    msg2 = f'cantidad comprada: {investment["amountAsBase"]} {base}'
                    msg3 = f'precio de compra: {investment["initialPrice"]} {quote}'
                    self.log.info(f'{msg1} {msg2} {msg3}')
                    self.cmd(f'\n{msg1}\n   {msg2}\n   {msg3}\n')

                    self.currentInvestments[symbolId] = investment
                    #self.initialExecutionDateTimeAsSeconds = data["initialDateTimeAsSeconds"] # debe quedarse con el mas antiguo.
                    self.log.info(self.cmd(f'Se han cargado los datos de la iversion actual en {symbolId}.'))
                else:
                    self.log.error(self.cmd(f'Error en los datos de la inversion en el mercado {symbolId}'))
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
            self.log.info(self.cmd(f'Iniciando bot: {self.botId}', '\n'))
            self.core = TrendTakerCore(self.botId, self.exchangeId, self.apiKey, self.secret)
            self.log.info(self.cmd(f'exchangeId: {self.exchangeId}'))
            self.config.core = self.core
            
            if self.core.exchangeInterface.check_exchange_methods(True):
                self.ledger = Ledger(self.botId, DIRECTORY_LEDGER)            
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
                                    self.log.info(msg1)
                                    self.log.info(f"{msg2} {str(self.initialBalance)}")
                                    self.log.info(msg3)
                                    print(f"{msg1}")                                
                                    TrendTakerCore.show_object(self.initialBalance['free'], f"\n{msg2}") 
                                    print(f"\n{msg3}")         
                                    time.sleep(1)       
                                    time.sleep(1)
                                    '''           
                                return True
        self.log.info(self.cmd('Terminado: No se puede continuar.'))
        return False


    def only_buy_and_sell(self):
        '''
        Hace pruebas de operaciones de compra y venta\n
        Si en DEBUG_MODE esta establecido el parametro el "onlyBuyAndSell", se ejecuta una orden de compra 
        con los parametros de la configuracion y luego ejecutar una venta para salir de la inversion y terminar.\n
        Nota: Esto se hace para comprobar el funcionamiento de las compras y ventas.\n
        return: True si logra ejecutar las ordenes de compra y venta correctamente. False si ocurre error.
        '''
        marketId = DEBUG_MODE.get("onlyBuyAndSell", None)
        if marketId is not None:
            print('satiago', marketId, marketId is not None)
            self.invest_in(str(marketId))
            time.sleep(1)
            self.close_investment()  
            self.log.info(self.cmd('Terminado'))
            return True
        return False
            

    def only_invest(self):
        '''
        Hace prueba de invertir en un mercado introduciendo una orden de compra con takeProfit y stopLoss.\n
        Si en DEBUG_MODE esta establecido el parametro el "onlyInvestIn", se ejecuta una orden de compra 
        con los parametros de la configuracion, con su takeProfit y stopLoss.\n
        Nota: Esto se hace para comprobar el funcionamiento de las compras y ventas.\n
        return: True si logra ejecutar las ordenes de compra y venta correctamente. False si ocurre error.
        '''
        marketId = DEBUG_MODE.get("onlyInvestIn", None)
        if marketId is not None:
            self.invest_in(str(marketId), 1, -1, 24)
            self.log.info(self.cmd('Terminado'))
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
            self.log.error(self.cmd('ATENCION: La configuracion del bot indica que deben cerrarse todas las inversiones inmediatamente.', '\n'))
            if len(self.currentInvestments) > 0:
                for symbolId in self.currentInvestments.keys():
                    self.close_investment(symbolId)
            self.log.error(self.cmd('Terminado: Se ha finalizado la ejecucion.'))
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
        if self.only_invest():
            return True
        if self.force_close_investment_and_exit():
            return True
        report = Report(self.core, self.botId, self.exchangeId, DIRECTORY_GRAPHICS, "png")
        validTickers = self.core.get_ordered_and_filtered_tickers(self.listOfValidMarketsId, self.config.data)
        if validTickers is None: 
            return False
        orderedMarkets = self.core.get_ordered_and_filtered_markets(validTickers, self.config.data)
        if orderedMarkets is None: 
            return False
        for marketData in orderedMarkets:
            symbolId = marketData["symbolId"]
            msg1 = f"Mercado potencial en: {symbolId}  crecimiento en 24h: {round(float(marketData['tickerData']['percentage']), 2)} %"
            self.log.info(self.cmd(msg1))                                
            lastPrice = float(marketData["tickerData"]["last"])
            amountToInvestAsQuote = float(self.config.data.get("amountToInvestAsQuote", 10))
            amountToInvestAsBase = amountToInvestAsQuote / lastPrice 
            if self.core.check_market_limits(marketData["symbolData"], amountToInvestAsBase, lastPrice):
                fileName = report.create_unique_filename()
                title = f'{self.botId} {self.exchangeId} {symbolId}'
                report.create_graph(marketData["candles1h"], title, fileName, marketData["metrics"], False) 
                #if report.count_market_data() >= 10: break              
                category:Category = "potentialMarket"             
                if symbolId not in self.currentInvestments:
                    pass
                    #marketData["invest"]
                    #if self.invest_in(symbolId, amountToInvestAsBase):
                    #    category = "openInvest"
                else:
                    # Si el mercado potencial seleccionado es el mismo en el que ya se ha invertido, no se hace nada y se procede a continuar verificando el estado de esa inversion.
                    pass
                    # Si ha superado el tiempo especifico para la imversio, deve termimarlo
                    #if not self.close_investment(symbolId):   
                    #    category = "closedInvest"  
                report.append_market_data(fileName, marketData["metrics"], category)
        if self.config.data["createWebReport"]:
            report.create_web(self.config.data["showWebReport"])
        if len(self.currentInvestments) == 0:
            self.log.info(self.cmd('SIN INVERTIR: No se han encontrado mercados favorables.'))
        self.log.info(self.cmd('Terminado'))
        return True


if __name__ == "__main__":
    credentials = json.loads(open('D:/1-Lineas/2 - Cryptos/automatic 2024/credential_hitbtc.json').read())
    #credentials = json.loads(open('D:/1-Lineas/2 - Cryptos/automatic 2024/credential_bingx.json').read())
    bot = TrendTaker('TrendTaker1', credentials['exchange'], credentials['key'], credentials['secret'])
    bot.execute()    
