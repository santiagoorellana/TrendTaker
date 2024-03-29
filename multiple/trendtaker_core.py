
import time
import json
import random
from exchange_interface import *
from market_metrics import *
from typing import Any, Dict, Literal, Optional, List

MarketData = Dict
Filters = Dict
ListOfMarketData = List[MarketData]
ComparisonCondition = Literal["above", "below"]
Slice = Literal["whole", "lastHalf", "lastQuarter"]
AmountLimit = Literal["min", "max"]


INDENT = str("   ")

class TrendTakerCore():

    def __init__(self, exchangeId, apiKey, secret, log=None, toLog=True, toConsole=False):
        self.exchangeId = exchangeId
        self.log = log  
        self.toLog = toLog
        self.toConsole = toConsole
        self.exchangeInterface = ExchangeInterface(exchangeId, apiKey, secret, log=log, toLog=toLog, toConsole=toConsole)
        self.metrics = MarketMetrics()
        self.validMarkets = None
        self.orderableMarket = None
        self.outQuotes = None      


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
                        TrendTakerCore.show_object(data[key], key, ident=ident, level=level+1)
                else:
                    count = 0
                    for element in data:
                        time.sleep(0.1)
                        TrendTakerCore.show_object(element, f'elemento {count}', ident=ident, level=level+1) 
                        count += 1
            else:
                print(f"{str(ident) * (level - 1)}{title}: {str(data)}") 
            return True
        except:
            return False               


    def load_markets(self) -> bool:
        '''
        Carga las listas de mercados y cryptomonedas del exchange y sus datos.\n
        return: True si se logran cargar los mercados y monedas. De lo contrario False.
        '''
        if self.exchangeInterface.load_markets_and_currencies():
            return True
        return False
        

    def is_valid_market(
            self, 
            dataMarket: Optional[Market], 
            dataCurrencyBase: Optional[Currency], 
            dataCurrencyQuote: Optional[Currency], 
            blackList: Optional[ListOfCurrenciesId] = None
        ) -> bool:
        '''
        Comprueba si el mercado está activo en el exchange y si es tipo spot.\n
        Verifica también si está incluido en las listas negras o si alguna
        de sus cryptomonedas está incluida en la lista negra.\n
        param dataMarket: Estructura de la librería CCXT con los datos del mercado.
        param dataCurrencyBase: Estructura de la librería CCXT con los datos de la crypto base.
        param dataCurrencyQuote: Estructura de la librería CCXT con los datos de la crypto quote.
        param blackList: Lista de cryptomonedas que no deben ser aceptadas. 
        return: True si el mercado es válido. De lo contrario devuelve False.
        '''
        try:
            if dataMarket is None or dataCurrencyBase is None or dataCurrencyQuote is None:
                return False
            if blackList is not None:
                if str(dataMarket['base']).upper() in blackList or str(dataMarket['base']).lower() in blackList:
                    return False
            if dataMarket['active'] == False or dataMarket['spot'] == False or dataMarket['type'] != 'spot':
                return False
            if dataCurrencyBase['active'] == False or dataCurrencyQuote['active'] == False:
                return False
        except Exception as e:
            msg1 = f"Error: Validando el mercado {dataMarket['symbol'] if dataMarket is not None else ''}. Exception: {str(e)}"
            if self.toLog: self.log.exception(msg1)
            if self.toConsole: print(msg1)
            return False
        return True

        
    def get_list_of_valid_markets(
            self, 
            quoteCurrency: CurrencyId = 'USDT', 
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
            if self.toLog: self.log.exception(msg1)
            if self.toConsole: print(msg1)
            return None
        return validMarkets


    def check(self, value:Optional[float], condition:ComparisonCondition, limit:Optional[float]):
        '''
        Compara un valor con respecto a un limite y devuelve True si se cumple la condicion.
        param value: Valor que se debe comparar con un limite.
        param condition: Condicion que se debe aplicar para realizar la comparacion.
        param limit: Limite con el que se debe compara el valor.
        return: True si la condicion se cumple. De lo contrario, devuelve False.
        '''
        if value is not None and limit is not None:
            if condition == 'above':
                return value >= limit
            elif condition == 'below':
                return value < limit 
            else:
                return False
        else:
            return False   


    def is_valid_ticker(self, tickerData:Ticker, configuration:Dict) -> bool:
        '''
        Verifica si el ticker pertenecen a un mercado valido que cumple las condiciones de seleccion del filtro.\n
        param tickerData: Objeto ticker obtenido del exchange, mediante la librería ccxt. 
        param configuration: Objeto con la configuracion del algoritmo.
        return: True si el ticker es un mercado valido que cumple las con el filtro. De lo contrario False.
        '''
        preselected = configuration.get("preselected", [])
        base = str(self.exchangeInterface.base_of_symbol(tickerData["symbol"]))
        if base.upper() in preselected or base.lower() in preselected:
            return True
        if tickerData is None:
            return False
        filters = configuration["filters"]["tickers"]
        
        valueLimit = float(filters.get("minProfit", None))
        if valueLimit is not None:
            if float(tickerData.get('percentage', 0)) < valueLimit:
                return False

        valueLimit = float(filters.get("maxSpreadOverProfit", None))
        if valueLimit is not None:
            if float(self.metrics.ticker_spread(tickerData)) > valueLimit:
                return False

        valueLimit = float(filters.get("minProfitOverAmplitude", None))
        if valueLimit is not None:
            if float(self.metrics.ticker_profit_over_amplitude(tickerData)) < valueLimit:
                return False
        return True


    def get_ordered_and_filtered_tickers(self, validMakets:ListOfMarketsId, configuration:Dict) -> Optional[ListOfTickers]:
        '''
        Dada una lista de mercados (symols) validos, pide al exchange todos los tickers y devuelve solo los que 
        pertenecen a mercados validos, y que cumplen las condiciones de seleccion del filtro.\n
        Nota: Se recomienda no llamar a esta función de manera muy seguida para evitar ser bloqueado por el exchange.\n
        param validMakets: Lista con los ID de los mercados (symbols) que se consideran validos.
        param configuration: Objeto con la configuracion del algoritmo.
        return: Lista filtrada con los tickers recientes, validos y crecientes. None si ha ocurrido un error.
        '''
        selected = []
        try:
            tickers = self.exchangeInterface.get_tickers()
            for marketId in validMakets:
                if marketId in tickers:
                    tickerData = tickers[marketId]
                    if self.is_valid_ticker(tickerData, configuration):
                        selected.append(tickerData)
            msg1 = f'Cantidad de mercados creciendo en las ultimas 24 horas: {len(selected)}'
            if self.toLog: self.log.info(msg1)
            if self.toConsole: print(f'{msg1}\n')
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
                    print(f'{ticker["symbol"]} creciendo en las ultimas 24 horas: {ticker["percentage"]}')
                    time.sleep(0.1)
                print('\n')
                return result
            except Exception as e:
                msg1 = f"Error: Ordenando los tickers filtrados de mercados validos."
                if self.toLog: self.log.exception(f'{msg1} Exception: {str(e)}')
                if self.toConsole: print(f'{msg1}\n')
                return None
        except Exception as e:
            msg1 = f"Error: Leyendo los tickers y filtrando mercados validos."
            if self.toLog: self.log.exception(f'{msg1} Exception: {str(e)}')
            if self.toConsole: print(f'{msg1}\n')
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
                    if self.toLog: self.log.error(msg1)
                    if self.toConsole: print(msg1)
                    time.sleep(0.1)
            msg1 = f'Se han preseleccionado {len(marketsData)} mercados con ganancia potencial.'
            if self.toLog: self.log.info(msg1)
            if self.toConsole: print(f'{msg1}\n')
            try:
                return sorted(marketsData, key=lambda x: float(x["metrics"]["potential"]), reverse=True)
            except Exception as e:
                msg1 = f"Error: Ordenando la lista de mercados seleccionados."
                if self.toLog: self.log.exception(f'{msg1} Exception: {str(e)}')
                if self.toConsole: print(msg1)
                return None
        except Exception as e:
            msg1 = f"Error: Obteniendo los datos descriptivos y velas de los mercados validos."
            if self.toLog: self.log.exception(f'{msg1} Exception: {str(e)}')
            if self.toConsole: print(msg1)
            return None
    

    def is_potential_market(self, marketData, configuration:Dict) -> bool:
        '''
        Devuelve true si el mercado tiene suficiente liquidez y potencial de crecimiento.\n
        param metrics: Datos y parametros del mercado que se deben comprobar.
        param configuration: Objeto con la configuracion del algoritmo.
        return: Devuelve True si el mercado tiene liquidez y potencial de crecimiento. De lo contrario, devuelve False.
        '''        
        preselected = configuration.get("preselected", [])
        base = str(marketData["baseId"])
        if base.upper() in preselected or base.lower() in preselected:
            return True
        filters = configuration["filters"]["candles"]
        candlesWhole = marketData["metrics"]["candles"]["whole"]["percent"]
        candlesLastHalf = marketData["metrics"]["candles"]["lastHalf"]["percent"]
        candlesLastQuarter = marketData["metrics"]["candles"]["lastQuarter"]["percent"]
        # Verifica si el porciento de velas colapsadas es minimo.
        if not self.check(candlesWhole["colapses"], "below", filters.get("maxColapses", None)):
            return False
        # Verifica si el porciento de completado del rango de velas es adecuado.
        if not self.check(candlesWhole["completion"], "above", filters.get("minCompletion", None)):
            return False
        # Verifica si el profit del rango completo de velas es adecuado.
        if not self.check(candlesWhole["changeOpenToAverage"], "above", filters.get("minProfitWhole", None)):
            return False
        # Verifica si el profit de la ultima mitad del rango de velas es adecuado.
        if not self.check(candlesLastHalf["changeOpenToAverage"], "above", filters.get("minProfitLastHalf", None)):
            return False
        # Verifica si el profit del ultimo cuarto del rango de velas es adecuado.
        if not self.check(candlesLastQuarter["changeOpenToAverage"], "above", filters.get("minProfitLastQuarter", None)):
            return False
        return True

    
    def is_liquid_market(self, market, verbose=False):
        '''
        Devuelve true si el mercado tiene suficiente liquidez para
        ejecutar las operaciones de compra y venta.
        '''
        # Detecta los picos exagerados que se producen.
        # del crecimiento del mercado en 24 horas. Se hace comparando el % de
        #crecimiento de cada vela 1h con el % de crecimiento total 24h. Si la
        #vela concentra mas de x% del crecimiento total, se asume que el mercado
        #crecio por un mechazo.

        input()
        return
        
        #calcular estadisticas
        #amplitud media de todas las velas
        #desviaciones con respecto a la media de las aplitudes.
        #volumen medio de todas las velas, etc
        #
        #Imprimir estadisticas

        
        
        #print(market['symbol'], market['ticker']['percentage'], '%')
        print(json.dumps(market['ticker'], indent=2))
        print('minToMax:', round(minToMax, 2), '%')
        print('spread:', round(spread, 2), '%')
        print('inToOut:', round(market['ticker']['percentage'], 2), '%')
        if minToMax > 0:
            print('spread in minToMax:', round(spread / minToMax * 100, 2), '%')
        if market['ticker']['percentage'] > 0:
            print('spread in inToOut:', round(spread / market['ticker']['percentage'] * 100, 2), '%')
        #self.to_graph(market['symbol'])
        print('---------------------------------------')
        input()
        
        return True        


    def get_market_limit(self, limit:AmountLimit, symbolData:Market) -> float:
        '''
        Devuelve el valor del limite minimo o maximo que se puede invertir en el mercado especificado.\n
        param limit: Especifica el limite que se desea obtener.
        param symbolData: Datos del mercado obtenidos mediante la libreria CCXT.
        return: Valor del limite minimo o maximo que se puede invertir en el mercado especificado.
        '''
        try: 
            return float(symbolData['limits']['amount'][limit])
        except: 
            return float(0) if limit == "min" else float(1000000000)


    def check_market_limits(self, symbolData:Market, amountAsBase:float, lastPrice:float) -> bool:
        '''
        Verifica si un valor esta dentro de los limites permitidos para el mercado especificado.\n
        param symbolData: Datos del mercado obtenidos mediante la libreria CCXT.
        param amountAsBase: Valor expresado e currecy ase, que se debe verificar si esta dentro de los limites.
        return: True si el valor "amountAsBase" esta dentro de los limites permitidos. False si esta fuera de los limites.
        '''
        symbolId = symbolData['symbol']
        base = self.exchangeInterface.base_of_symbol(symbolId)
        quote = self.exchangeInterface.quote_of_symbol(symbolId)
        decimals = 2 if quote.upper() == "USDT" else 12
        amountMin = self.get_market_limit("min", symbolData)
        amountMax = self.get_market_limit("max", symbolData)
        amountMinAsQuote = float(amountMin * lastPrice)
        amountMaxAsQuote = float(amountMax * lastPrice)
        if amountAsBase < amountMin:
            msg1 = f'   El monto {amountAsBase} {base} es inferior al minimo permitido en el mercado {symbolId}'
            msg2 = f'   Atencion: El monto minimo permitido en {symbolId} es de {amountMin} {base}  ({round(amountMinAsQuote, decimals)} {quote} )'
            if self.toLog: 
                self.log.error(msg1)
                self.log.warning(msg2)
            if self.toConsole: 
                print(msg1)
                print(msg2)
            return False
        elif amountAsBase > amountMax:
            msg1 = f'{INDENT}El monto {amountAsBase} {base} es superior al maximo permitido en el mercado {symbolId}'
            msg2 = f'{INDENT}Atencion: El monto maximo permitido en {symbolId} es de {amountMax} {base}  ({round(amountMaxAsQuote, decimals)} {quote} )'
            if self.toLog: 
                self.log.error(msg1)
                self.log.warning(msg2)
            if self.toConsole: 
                print(msg1)
                print(msg2)
            return False
        else:
            return True
    
    
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
            
            
    def execute_market(self, side:Side, symbol:MarketId, amount:float, simulated:bool=True) -> Optional[Order]:
        '''
        Ejecuta una orden a precio de mercado.
        param side: Tipo de operacion "buy" o "sell".
        param symbol: Identificador del mercado en el que se debe hacer la operacion.
        param amount: Cantidad de currency base que se va a operar.
        param simulated: En True indica que la operacion solo se debe simular.
        return: Devuelve un Dict que contiene los datos del resultado de la orden. 
                Si la operacion es simulada, devuelve un Dict con datos ficticios.
                Devuelve None si ocurre un error.
        '''
        if simulated: 
            order = self.create_simulated_order(side, symbol, amount) 
        else:       
            if side == "buy":
                order = self.exchangeInterface.execute_market_buy(symbol, amount)
            else:
                order = self.exchangeInterface.execute_market_sell(symbol, amount)
        if order is not None:
            orderId = order["id"]
            if self.toLog: 
                self.log.info(f'Orden de mercado creada: {str(order)}')
            if self.toConsole: 
                print(f'\nOrden de mercado creada: {orderId}')
                print(f'{side.upper()} {self.decimal_string(amount)} en el mercado {symbol} al precio actual:')
            while order is not None: 
                if self.toLog: 
                    self.log.info(f'estado: {str(order)}')
                if self.toConsole: 
                    print('{}estado: {}   llenado: {}   remanente: {}   precio promedio: {}   fee:{}'.format(
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
            msg1 = f'Error creando orden de mercado {side}.'
            if self.toLog: self.log.error(msg1)
            if self.toConsole: print(msg1)
            return None


        

# Codigo de ejemplo y test.
if __name__ == "__main__":
    core = TrendTakerCore('hitbtc', '', '')
    core.load_markets()
    validMarketsIdList = core.get_list_of_valid_markets()
    print(validMarketsIdList)