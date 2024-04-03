
import time
from exchange_interface import *
from market_metrics import *
from basics import *
from typing import Dict, Literal, Optional, List
from validations import Validations

class TrendTakerCore(Validations, Basics):

    def __init__(self, botId:str, exchangeId:str, apiKey:str, secret:str):
        Validations.__init__(self, botId)
        self.exchangeId = exchangeId
        self.exchangeInterface = ExchangeInterface(exchangeId, apiKey, secret, botId)
        self.metrics = MarketMetrics()
        self.validMarkets = None
        self.orderableMarket = None
        self.outQuotes = None     


    def load_markets(self) -> bool:
        '''
        Carga las listas de mercados y cryptomonedas del exchange y sus datos.\n
        return: True si se logran cargar los mercados y monedas. De lo contrario False.
        '''
        if self.exchangeInterface.load_markets_and_currencies():
            countOfCurrencies = len(self.exchangeInterface.get_currencies())          
            countOfMarkets = len(self.exchangeInterface.get_markets())
            self.log.info(self.cmd(f'Total de criptomonedas del exchange: {countOfCurrencies}'))
            self.log.info(self.cmd(f'Total de mercados del exchange: {countOfMarkets}'))
            return True
        else:
            self.log.error(self.cmd('Error: Cargando mercados.'))
            return False
        

    def get_list_of_valid_markets(
            self, 
            quoteCurrency: CurrencyId, 
            blackList: Optional[ListOfCurrenciesId] = None
        ) -> Optional[ListOfMarketsId]:
        '''
        Devuelve una lista con los ID de mercados filtrados de manera que la Quote Currecy del Symbol debe ser 
        la indicada por parametro y el mercado y sus criptos, no deben estar en la lista negra del algoritmo.\n
        param blackList: Lista de cryptomonedas que no deben ser aceptadas. Ej. ['ADA', 'XXX', 'PEPE']
        return: Lista de los mercados validos. Si ocurre error, devuelve None.
        '''
        validMarkets = []
        try:
            markets = self.exchangeInterface.get_markets()
            if markets is None:
                return None
            currencies = self.exchangeInterface.get_currencies()
            if currencies is None:
                return None
            for symbol in markets:
                quote = self.exchangeInterface.quote_of_symbol(symbol)
                if quote == quoteCurrency:
                    symbolData = markets.get(symbol, None)
                    if symbolData is not None:
                        base = self.exchangeInterface.base_of_symbol(symbol)
                        if self.is_valid_market(
                                symbolData,
                                currencies.get(base, None),
                                currencies.get(quote, None),
                                blackList
                            ):
                            validMarkets.append(symbol)
        except Exception as e:
            msg1 = f"Error: Obteniendo la lista de mercados validos. Exception: {str(e)}"
            self.log.exception(self.cmd(msg1))
            return None
        return validMarkets


    def get_ordered_and_filtered_tickers(
            self, 
            validMakets:Optional[ListOfMarketsId], 
            configuration:Optional[ConfigurationData]
        ) -> Optional[ListOfTickers]:
        '''
        Dada una lista de mercados (symols) validos, pide al exchange todos los tickers y devuelve solo los que 
        pertenecen a mercados validos, y que cumplen las condiciones de seleccion del filtro.\n
        Nota: Se recomienda no llamar a esta función de manera muy seguida para evitar ser bloqueado por el exchange.\n
        param validMakets: Lista con los ID de los mercados (symbols) que se consideran validos.
        param configuration: Objeto con la configuracion del algoritmo.
        return: Lista filtrada con los tickers recientes, validos y crecientes. None si ha ocurrido un error.
        '''
        if validMakets is None or configuration is None:
            return None
        selected = []
        try:
            tickers = self.exchangeInterface.get_tickers()
            if tickers is not None:
                for marketId in validMakets:
                    if marketId in tickers:
                        tickerData = tickers[marketId]
                        if self.is_valid_ticker(tickerData, configuration):
                            selected.append(tickerData)
            self.log.info(self.cmd(f'Cantidad de mercados creciendo en las ultimas 24 horas: {len(selected)}', '', '\n'))
            try:
                preselected = configuration.get("preselected", [])
                result = sorted(
                    selected, 
                    key=lambda x: float(x["percentage"]) 
                        if str(self.exchangeInterface.base_of_symbol(x["symbol"])).lower() not in preselected \
                            and str(self.exchangeInterface.base_of_symbol(x["symbol"])).upper() not in preselected
                        else 1000000, 
                    reverse=True
                )
                result = result[0:configuration.get("maxTickersToSelect", 100)]
                for ticker in result:
                    self.cmd(f'{ticker["symbol"]} creciendo en las ultimas 24 horas: {ticker["percentage"]}')
                    time.sleep(0.1)
                self.cmd('\n')
                return result
            except Exception as e:
                self.log.exception(f'{self.cmd("Error: Ordenando los tickers filtrados de mercados validos.")} Exception: {str(e)}')
                return None
        except Exception as e:
            self.log.exception(f'{self.cmd("Error: Leyendo los tickers y filtrando mercados validos.")} Exception: {str(e)}')
            return None
        

    def get_ordered_and_filtered_markets(self, validTickers:ListOfTickers, configuration:Dict) -> Optional[ListOfMarketData]:
        '''
        Dada una lista de tickers de mercados validos, pide al exchange los datos y velas de cada mercado
        para devolver una lista de los mercados con sus velas y datos descriptivos.\n
        Nota: Se recomienda no llamar a esta función de manera muy seguida para evitar ser bloqueado por el exchange.\n
        param validTickers: Lista con los tickers de los mercados (symbols) que se consideran validos.
        param configuration: Objeto con la configuracion del algoritmo.
        return: Lista de mercados con los tickers, ultimas velas y datos descriptivos. None si ha ocurrido un error.
        '''
        marketsData:ListOfMarketData = []
        try:
            preselected = configuration.get("preselected", [])
            cadlesHours = int(configuration.get("candlesDays", 7)) * 24
            maxCount = len(validTickers)
            count = 0
            for ticker in validTickers:
                count += 1
                symbolId = ticker['symbol']
                baseId = self.exchangeInterface.base_of_symbol(symbolId)
                quoteId = self.exchangeInterface.quote_of_symbol(symbolId)
                candles1h = self.exchangeInterface.get_last_candles(symbolId, cadlesHours, "1h")
                if candles1h is not None:
                    market = {
                        "symbolId": symbolId,
                        "baseId": baseId,
                        "quoteId": quoteId,
                        "tickerData": ticker,
                        "symbolData": self.exchangeInterface.get_markets()[symbolId],
                        "baseData": self.exchangeInterface.get_currencies()[baseId],
                        "quoteData": self.exchangeInterface.get_currencies()[quoteId],
                        "candles1h": candles1h,
                        "metrics": self.metrics.calculate(ticker, candles1h, preselected),
                    }              
                    msg1 = f'[{count} de {maxCount}] Se han obtenido los datos del mercado: {symbolId}'
                    if self.is_potential_market(market, configuration):
                        marketsData.append(market)
                        msg1 = f"{msg1}  [POTENCIAL]"
                    self.log.info(self.cmd(msg1))
                    time.sleep(0.1)
            self.log.info(self.cmd(f'Se han preseleccionado {len(marketsData)} mercados con ganancia potencial.', '', '\n'))
            try:
                return sorted(marketsData, key=lambda x: float(x["metrics"]["potential"]), reverse=True)
            except Exception as e:
                self.log.exception(f'{self.cmd("Error: Ordenando la lista de mercados seleccionados.")} Exception: {str(e)}')
                return None
        except Exception as e:
            self.log.exception(f'{self.cmd("Error: Obteniendo los datos descriptivos y velas de los mercados validos.")} Exception: {str(e)}')
            return None
    

    def create_simulated_order(self, side:Side, symbol:MarketId, amount:float) -> Optional[Order]:
        '''
        Devuelve datos ficticios de una orden simulada.
        param side: Tipo de operacion "buy" o "sell".
        param symbol: Identificador del mercado en el que se debe hacer la operacion.
        param amount: Cantidad de currency base que se va a operar.
        return: Devuelve un Dict con datos de operacion ficticios. 
                Devuelve None si ocurre un error.
        '''
        quote = self.exchangeInterface.quote_of_symbol(symbol)
        ticker = self.exchangeInterface.get_ticker(symbol)
        if ticker is not None:
            price = float(ticker["last"])
            return {
                'id': str(ticker["timestamp"]),     # string
                'clientOrderId': 'simulated',       # a user-defined clientOrderId, if any
                'datetime': ticker["datetime"],     # ISO8601 datetime of 'timestamp' with milliseconds
                'timestamp': ticker["timestamp"],   # order placing/opening Unix timestamp in milliseconds
                'lastTradeTimestamp': None,         # Unix timestamp of the most recent trade on this order
                'status': 'closed',                 # 'open', 'closed', 'canceled', 'expired', 'rejected'
                'symbol': symbol,                   # symbol
                'type': 'market',                   # 'market', 'limit'
                'timeInForce': 'GTC',               # 'GTC', 'IOC', 'FOK', 'PO'
                'side': side,                       # 'buy', 'sell'
                'price': price,                     # float price in quote currency (may be empty for market orders)
                'average': price,                   # float average filling price
                'amount': amount,                   # ordered amount of base currency
                'filled': amount,                   # filled amount of base currency
                'remaining': 0,                     # remaining amount to fill
                'cost': float(amount)*price,        # 'filled' * 'price' (filling price used where available)
                'trades': [],                       # a list of order trades/executions
                'fee': {                            # fee info, if available
                    'currency': quote,              # which currency the fee is (usually quote)
                    'cost': float(amount) * 0.002,  # the fee amount in that currency
                    'rate': 0.002,                  # the fee rate (if available)
                }       
            }
        else:
            return None  
            
            
    def execute_market(
            self, 
            side:Side, 
            symbol:MarketId, 
            amount:float, 
            takeProfitPrice:Optional[float]=None, 
            stopLossPrice:Optional[float]=None,
            maxHours:Optional[float]=None, 
            simulated:bool=True
        ) -> Optional[Order]:
        '''
        Ejecuta una orden a precio de mercado.
        param side: Tipo de operacion "buy" o "sell".
        param symbol: Identificador del mercado en el que se debe hacer la operacion.
        param amount: Cantidad de currency base que se va a operar.
        param takeProfitPrice: Precio en el cual se debe ejecutar la venta para obtener ganancias.
        param stopLossPrice: Precio en el cual se debe vender para detener las perdidas.
        param maxHours: Cantidad maxima de horas que se puede poseer el activo. 
        param simulated: En True indica que la operacion solo se debe simular.
        return: Devuelve un Dict que contiene los datos del resultado de la orden. 
                Si la operacion es simulada, devuelve un Dict con datos ficticios.
                Devuelve None si ocurre un error.
        '''
        if simulated: 
            order = self.create_simulated_order(side, symbol, amount) 
        else:   
            params = {}
            if takeProfitPrice is not None:
                params["takeProfit"] = { 'type': 'market', 'triggerPrice': takeProfitPrice }                
            if stopLossPrice is not None:
                params["stopLoss"] = { 'type': 'market', 'triggerPrice': stopLossPrice }                
            if side == "buy":
                order = self.exchangeInterface.execute_market_buy(symbol, amount, params)
            else:
                order = self.exchangeInterface.execute_market_sell(symbol, amount, params)
        if order is not None:
            orderId = order["id"]
            self.log.info(f'Orden de mercado creada: {str(order)}')
            self.cmd(f'\nOrden de mercado creada: {orderId}')
            self.cmd(f'{side.upper()} {self.decimal_string(amount)} en el mercado {symbol} al precio actual:')
            while order is not None: 
                self.log.info(f'estado: {str(order)}')
                self.cmd('{}estado: {}   llenado: {}   remanente: {}   precio promedio: {}   fee:{}'.format(
                    INDENT,
                    order["status"],
                    self.decimal_string(order["filled"]),
                    self.decimal_string(order["remaining"]),
                    self.decimal_string(order["average"]),
                    self.decimal_string(order["fee"]["cost"])
                ))
                if order['status'] != "open":
                    break
                time.sleep(1)
                order = self.exchangeInterface.get_order(orderId, symbol)
            return order
        else:
            self.log.error(self.cmd(f'Error creando orden de mercado {side}.'))
            return None
        


    def sufficient_quote_to_buy(self, amountQuoteToBuy:float, marketId:MarketId):
        '''
        Determina si hay suficiente balance para hacer una compra.\n
        Tiene en cuenta el fee que se debe pagar por la operacion.\n
        param necessaryQuoteAmount: Cantidad de moneda quote que se necesita para comprar la moneda base.
        param marketId: Identificador del mercado (symbol) donde se va a operar.
        return: True si hay suficiente saldo para la operacion. False si no hay suficiente.
        '''
        try:
            currentBalance = self.exchangeInterface.get_balance()
            if currentBalance is not None:
                takerFeeRate = float(self.core.exchangeInterface.get_markets()[marketId]["taker"])
                necessaryCurrencyBalance = amountQuoteToBuy + (amountQuoteToBuy * takerFeeRate)
                currencyId = self.exchangeInterface.quote_of_symbol(marketId)
                availableCurrencyBalance = float(currentBalance['free'][currencyId])
                return availableCurrencyBalance >= necessaryCurrencyBalance
            else:
                self.log.error(self.cmd(f'Error: No se pudo obtener el balance actual de {currencyId}'))
                return False
        except Exception as e:
            self.log.exception(self.cmd(f'Error: Comprobando el balance de {currencyId}'))
            return False
    
    
    
    def calculate_profit_percent(self, metrics:MarketMetrics):
        return None
    
    
    def calculate_max_loss_percent(self, metrics:MarketMetrics):
        return None
    
    
    def calculate_max_hours(self, metrics:MarketMetrics):
        return None
    
    
  
    

# Codigo de ejemplo y test.
if __name__ == "__main__":
    core = TrendTakerCore('TrendTaker1', 'hitbtc', '', '')
    core.load_markets()
    validMarketsIdList = core.get_list_of_valid_markets('USDT', None)
    print(validMarketsIdList)

