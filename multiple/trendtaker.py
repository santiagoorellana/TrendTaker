
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
    "ignoreInsufficientBalance": True,  # En True, hace que se ignore el balance insuficiente.
    "simulateOrderExecution": True,     # En True, hace que las ordenes de compra y venta sean simuladas.    
    "onlyBuyAndSell": None              # Ejecuta una compra y venta e el mercado especificado. Se desactiva con None.
}


class TrendTaker(Basics):
    
    def __init__(self, botId:str, exchangeId:str, apiKey:str, secret:str):
        self.botId = botId
        self.exchangeId = exchangeId
        self.apiKey = apiKey
        self.secret = secret
        
        self.listOfValidMarketsId:Optional[ListOfMarketsId] = None
        self.config = Configuration(botId)
        self.initialBalance:Balance = {}
        self.currentBalance:Optional[Balance] = None
        self.currentInvestments:CurrentInvestments = {}
        self.totalFeeAsQuote:float = 0
        
    
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



    ####################################################################################################
    # METODOS PARA PEDIR DATOS AL EXCHANGE
    ####################################################################################################
    
    
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
                if quoteBalance < float(self.config.data.get(param, 10)) * 2.5 and not DEBUG_MODE["ignoreInsufficientBalance"]:
                    self.log.error(self.cmd(f'El balance libre actual de {quote} en la cuenta no es suficiente para operar.'))
                    self.log.info(self.cmd(f'Debe reducir el valor del parametro "{param}" o aumentar el balance de la cuenta.'))
                    return False
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
            str(self.config.data.get('currencyQuote', 'USDT')),
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




    ####################################################################################################
    # METODOS PARA COTROLAR LAS ENTRADAS Y SALIDAS DE LAS INVERSIONES
    ####################################################################################################
    
    
    def invest_in(
            self, 
            symbolId:MarketId, 
            amountAsBase:float, 
            profitPercent:Optional[float]=None, 
            maxLossPercent:Optional[float]=None, 
            maxHours:Optional[float]=None,
            trailingStop:bool=False 
        ) -> bool:
        '''
        Abre una inversion nueva comprando el activo.\n
        Permite colocar precios de TakeProfit, StopLoss, TrailingStop y limite temporal que son 
        implementados directamente por el Bot o son implementados por el exchange mediante CCXT.\n
        param symbolId: Identificador del mercado en el que se debe invertir.
        param amountAsBase: Cantidad de moneda base que se debe comprar para invertir.
        param profitPercent: Porciento de ganancia con que se espera cerrar la inversion.
        param maxLossPercent: Maximo porciento de perdida que se va a tolerar.
        param maxHours: Cantidad maxima de horas que puede estar abierta la inversion.
        param trailingStop: En True indica que maxLossPercent se debe comportar como un trailingStop. 
        return: True si logra abrir la inversion. False si no la abre.
        '''
        if maxHours is None:
            maxHours = int(self.config.data["candlesDays"]) * 24
        market = self.core.exchangeInterface.get_markets()[symbolId]
        if market is not None:
            ticker = self.core.exchangeInterface.get_ticker(symbolId)
            if ticker is not None:
                base = self.core.exchangeInterface.base_of_symbol(symbolId)
                quote = self.core.exchangeInterface.quote_of_symbol(symbolId)
                self.currentBalance = self.core.exchangeInterface.get_balance()
                if self.currentBalance is None:
                    self.log.error(self.cmd('Error: No se pudo obtener el balance actual de la cuenta.'))
                    balanceQuote = float(0)
                else:
                    balanceQuote = float(self.currentBalance["free"][quote])
                
                lastPrice = float(ticker.get("last", 0))
                if lastPrice > 0:
                    if self.core.check_market_limits(market, amountAsBase, lastPrice):
                        amountAsBase = self.core.exchangeInterface.round_to_precision(amountAsBase, symbolId, "amount")
                        
                        # aqui se deberia comprobar si el amount a invertir supera al balance disponible.
                        
                        # Calcula el precio de toma de ganancias.
                        takeProfitPrice = None
                        if profitPercent is not None:
                            takeProfitPrice = lastPrice * (1 + (profitPercent / 100)) 
                        
                        # Calcula el precio de salida para evitar mas perdidas.
                        stopLossPrice = None
                        if maxLossPercent is not None:
                            if maxLossPercent > 0: maxLossPercent *= -1     # porciento debe ser negativo.
                            stopLossPrice = lastPrice * (1 + (maxLossPercent / 100)) 

                        # Ejecuta la orden de compra a precio de mercado, especificando takeProfit y stopLoss.
                        debug = bool(DEBUG_MODE.get("simulateOrderExecution", False))
                        order = self.core.execute_market('buy', symbolId, amountAsBase, takeProfitPrice, stopLossPrice, maxHours, debug)   
                                             
                        if order is not None:                        
                            self.currentInvestments[symbolId] = {
                                "orderId": order["id"],
                                "symbol": symbolId,
                                "lastTickerPrice": lastPrice,
                                "initialPrice": order["average"],
                                "amountAsBase": order["amount"],
                                "initialDateTimeAsSeconds": self.core.exchangeInterface.exchange.seconds(),
                                "fee": order["fee"]["cost"],
                                "profitPercent": profitPercent, 
                                "maxLossPercent": maxLossPercent, 
                                "trailingStop": trailingStop,
                                "takeProfitPrice": takeProfitPrice,
                                "stopLossPrice": stopLossPrice,
                                "maxHours": maxHours
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
                        balanceQuote = float(0)
                    else:
                        balanceQuote = float(self.currentBalance["free"][quote])
                    
                    amountAsBase = float(investment['amountAsBase'])
                    lastPrice = float(ticker.get("last", 0))
                    if lastPrice > 0:
                        initialPrice = float(investment['initialPrice'])

                        order = self.core.execute_market('sell', symbolId, amountAsBase, bool(DEBUG_MODE.get("simulateOrderExecution", False)))
                        if order is not None:                        
                            try:
                                profit = round((float(order["average"]) - initialPrice) / initialPrice * 100, 2)
                            except:
                                profit = None
                            try:
                                initial = float(self.initialBalance['free'][quote])
                                current = float(self.currentBalance['free'][quote]) if self.currentBalance is not None else initial
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


    
        
    def load_current_investments(self) -> bool:
        '''
        Carga desde un fichero los datos de las inversiones actuales en curso.\n
        return: True si encuentra un fichero y logra cargar los datos. False si no se cargan datos.
        '''
        currentInvestmentsData = FileManager.data_from_file_json(self.currentInvestmentsFileName, False, self.log)
        if currentInvestmentsData is not None:
            msg1 = f'Se ha encontrado un fichero de datos de inversiones actuales": "{self.currentInvestmentsFileName}"'
            self.log.info(self.cmd(msg1))
            if type(currentInvestmentsData) != Dict:
                self.log.error(self.cmd('Error: La estructura del fichero de datos de inversiones actuales no es correcta.'))
                return False
            if len(currentInvestmentsData) == 0:
                self.log.error(self.cmd('El fichero de datos de inversiones actuales no contiene datos.'))
                return True
            else:
                self.log.error(self.cmd(f'Cantidad de inversiones actuales: {len(currentInvestmentsData)}'))
            for key in currentInvestmentsData.keys():
                investment = currentInvestmentsData[key]
                if self.core.is_valid_current_investment_structure(investment): 
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




    def actualize_current_investments(self) -> bool:
        '''
        Actualiza el estado de las inversiones actuales en curso.\n
        Ejecuta las operaciones de venta de los activos cuyo precio a cruzado los umbrales de 
        Take Profit o Stop Loss. Tambien ejecuta la venta si la inversion supera el tiempo maximo
        permitido para la inversion.\n
        return: True si encuentra un fichero y logra cargar los datos. False si no se cargan datos.
        '''
        if self.currentInvestments is not None:
            listOfMarketsId = ListOfMarketsId(self.currentInvestments.keys())
            for marketId in listOfMarketsId:
                investment = self.currentInvestments[marketId]
                openInvesting = True
                ticker = self.core.exchangeInterface.get_ticker(marketId)
                if ticker is not None:
                    actualPrice = float(ticker["last"])
                    
                    if openInvesting:
                        if investment["trailingStop"]:
                            if investment["maxLossPercent"] is not None:
                                trailingStopPrice = actualPrice * (1 + (float(investment["maxLossPercent"]) / 100))
                                if actualPrice <= float(trailingStopPrice):
                                    self.log.info(self.cmd(f'TRAILING STOP LOSS activado en {marketId}', '\n'))
                                    openInvesting = not self.close_investment(marketId)
                        else:
                            if investment["stopLossPrice"] is not None:
                                if actualPrice <= float(investment["stopLossPrice"]):
                                    self.log.info(self.cmd(f'STOP LOSS activado en {marketId}', '\n'))
                                    openInvesting = not self.close_investment(marketId)
                                    
                    if openInvesting and investment["takeProfitPrice"] is not None:
                        if actualPrice >= float(investment["takeProfitPrice"]):
                            self.log.info(self.cmd(f'TAKE PROFIT activado en {marketId}', '\n'))
                            openInvesting = not self.close_investment(marketId)
                            
                    if openInvesting:
                        if investment["maxHours"] is not None:
                            maxHours = float(investment["maxHours"])
                        else:
                            maxHours = int(self.config.data["candlesDays"]) * 24
                        dateTimeAsSeconds = self.core.exchangeInterface.exchange.seconds()
                        initialDateTimeAsSeconds = int(investment["initialDateTimeAsSeconds"])
                        hours = float((dateTimeAsSeconds - initialDateTimeAsSeconds) / 60 / 60)
                        if hours >= maxHours:
                            self.log.info(self.cmd(f'TIME STOP activado en {marketId}', '\n'))
                            openInvesting = not self.close_investment(marketId)
                else:
                    self.log.warning(self.cmd(f'Error: No se pudo obtener el ticker del mercado {marketId}', '\n'))
                time.sleep(0.2)
            return True
        return False

    
        
        
    ####################################################################################################
    # METODOS PARA COTROL DE LA LOGICA PRINCIPAL DEL BOT
    ####################################################################################################
    
    
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
            
            if self.core.exchangeInterface.check_exchange_methods(True):
                self.ledger = Ledger(self.botId, DIRECTORY_LEDGER)            
                if self.config.load():
                    time.sleep(1)
                    if self.get_current_balance():
                        time.sleep(1)
                        if self.core.load_markets():
                            if self.get_list_of_valid_markets():
                                self.initialExecutionDateTimeAsSeconds = self.core.exchangeInterface.exchange.seconds()
                                self.currentInvestmentsFileName = f'./{self.botId}_current_investment.json'
                                self.load_current_investments()
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
        #marketId = DEBUG_MODE.get("onlyInvestIn", None)
        #if marketId is not None:
        #    self.invest_in(str(marketId), 1, -1, 24)
        #    self.log.info(self.cmd('Terminado'))
        #    return True
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
            if len(self.currentInvestments.keys()) < int(self.config.data["maxCurrenciesToInvest"]):
                symbolId = marketData["symbolId"]
                percentage = float(marketData['tickerData']['percentage'])
                msg1 = f"Mercado potencial en: {symbolId}  crecimiento en 24h: {round(percentage, 2)} %"
                self.log.info(self.cmd(msg1))                                
                lastPrice = float(marketData["tickerData"]["last"])
                amountToInvestAsQuote = float(self.config.data["amountToInvestAsQuote"])
                amountToInvestAsBase = amountToInvestAsQuote / lastPrice 
                if self.core.check_market_limits(marketData["symbolData"], amountToInvestAsBase, lastPrice):
                    graphFileName = report.create_unique_filename()
                    graphTitle = f'{self.botId} {self.exchangeId} {symbolId}'
                    report.create_graph(marketData["candles1h"], graphTitle, graphFileName, marketData["metrics"], False)           
                    category:Category = "potentialMarket"             
                    if symbolId not in self.currentInvestments:
                        if self.core.sufficient_quote_to_buy(amountToInvestAsQuote, symbolId):
                            if self.config.data["modeActive"]["enable"]:
                                if self.invest_in(
                                        symbolId, 
                                        amountToInvestAsBase, 
                                        self.core.calculate_profit_percent(marketData["metrics"]), 
                                        self.core.calculate_max_loss_percent(marketData["metrics"]),
                                        self.core.calculate_max_hours(marketData["metrics"]),
                                        self.config.data["modeActive"]["trailingStopEnable"]
                                    ):
                                    category = "openInvest"
                            else:
                                if self.invest_in(symbolId, amountToInvestAsBase):
                                    category = "openInvest"                                
                    report.append_market_data(graphFileName, marketData["metrics"], category)
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
 