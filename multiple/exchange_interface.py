
import time
import ccxt # type: ignore
from basics import *
import logging


CANDLE_TIMESTAMP = 0
CANDLE_OPEN = 1
CANDLE_HIGT = 2
CANDLE_LOW = 3
CANDLE_CLOSE = 4
CANDLE_VOLUME = 5

INSISTENCE_COUNT_MAX = 25
INSISTENCE_PAUSE_SECONDS = 1

class ExchangeInterface(Basics):

    def __init__(self, exchangeId:str, apiKey:str, secret:str, logName:str):
        self.exchange: Any = None
        self.select_exchange(exchangeId, apiKey, secret)   #hitbtc, kraken
        self.exchangeId: str = exchangeId
        self.insistenceCountMax: int = INSISTENCE_COUNT_MAX
        self.insistencePauseSeconds: int = INSISTENCE_PAUSE_SECONDS
        self.log = logging.getLogger(logName)

        
    def select_exchange(self, exchangeId:str, apiKey:str, secret:str) -> bool:
        '''
        Selecciona un exchage para hacerle peticiones por API mediante CCXT.
        param exchangeId: Identificador del exchange que se desea seleccionar.
        return: Instancia del objeto exchange. Si ocurre error, devuelve None.
        '''
        try:
            self.exchange = (getattr(ccxt, exchangeId))({"apiKey": apiKey, "secret": secret}) 
            self.exchangeId = exchangeId
            return True
        except Exception as e:
            self.log.exception(self.cmd(f"Error: No se pudo seleccionar el exchange: {exchangeId}"))
            return False


    def _check_exchange_method(self, method:str) -> bool:
        '''
        Verifica que el exchange contega el metodo especificado.
        param method: Es el nombre del metodo que se debe comprobar.
        return: True si el exchange contiene el metodo. False si falta el metodo.
        '''
        if not self.exchange.has[method]:
            self.log.error(self.cmd(f'Error: El exchange {self.exchangeId} no tiene el metodo "{method}".'))
            return False
        else:
            return True
                    
                    
    def check_exchange_methods(self, checkPrivate:bool) -> bool:
        '''
        Verifica que el exchange contega todos los metodos necesarios para operar.
        param checkPrivate: Poner a True para que se verifiquen los metodos privados.
        return: True si el exchange contiene todos los metodos necesarios. False si falta algun metodo.
        '''
        try:
            missing = 0
            missing += int(not self._check_exchange_method("fetchTicker"))
            missing += int(not self._check_exchange_method("fetchTickers"))
            missing += int(not self._check_exchange_method("fetchOHLCV"))            
            if checkPrivate:
                missing += int(not self._check_exchange_method("fetchBalance"))
                missing += int(not self._check_exchange_method("fetchOrder"))
                missing += int(not self._check_exchange_method("cancelOrder"))
                missing += int(not self._check_exchange_method("createMarketOrder"))
            return missing == 0
        except Exception as e:
            self.log.exception(self.cmd(f"Error: Verificando los metodos del exchange. Exception: {str(e)}"))
            return False


    def load_markets_and_currencies(self) -> bool:
        '''
        Carga los mercados y cryptomonedas del exchange y sus datos.
        Si se produce un error, lo intenta nuevamente varias veces antes de fallar.
        Return: True si se logran cargar los mercados y monedas. De lo contrario False.
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                self.exchange.load_markets()
                if len(self.exchange.markets) > 0 and len(self.exchange.currencies) > 0:
                    return True
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        self.log.exception(self.cmd(f"Error: Cargando datos de los mercados y sus cryptomonedas. Exception: {exceptionMsg}"))
        return False
        

    def get_markets(self) -> DictOfMarkets:
        '''
        Devuelve los mercados del exchange que ya fueron cargados previamente.
        Return: Lista de los mercados del exchange. Si no hay, devuelve None.
        '''
        return self.exchange.markets
        

    def get_currencies(self) -> DictOfCurrencies:
        '''
        Devuelve las currencies del exchange que ya fueron cargadas previamente.
        Return: Lista de las currencies del exchange. Si no hay, devuelve None.
        '''
        return self.exchange.currencies


    def get_balance(self) -> Optional[Balance]:
        '''
        Devuelve el balance actual de la cuenta.
        Return: Estructura con la informacion del balance. Si ocurre error, devuelve None.
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.fetch_balance()  #{'recvWindow': 10000000}
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        self.log.exception(self.cmd(f"Error: Cargando el balance de la cuenta. Exception: {exceptionMsg}"))
        return None
                

    def get_tickers(self, symbols:Optional[ListOfMarketsId]=None) -> Optional[DictOfTickers]:
        '''
        Carga la lista de tickers de todos los mercados del exchange.
        Si se produce un error, lo intenta nuevamente varias veces antes de fallar.
        return: Lista de tickers obtenidos. Si ocurre error, devuelve None.
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                if symbols == None:
                    return self.exchange.fetch_tickers()
                else:
                    return self.exchange.fetch_tickers(symbols)
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        self.log.exception(self.cmd(f"Error: Obteniendo los tickers de todos los mercados. Exception: {exceptionMsg}"))
        return None
        

    def get_ticker(self, symbol:MarketId) -> Optional[Ticker]:
        '''
        Obtiene el precio a partir del último ticker.
        Si se produce un error, lo intenta nuevamente varias veces antes de fallar.
        param symbol: Mercado del que se va a obtener el ticker.
        return: Devuelve el ticker obtenido. Si falla devuelve None.
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.fetch_ticker(symbol)
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        self.log.exception(self.cmd(f"Error: Obteniendo el ticker del mercado {symbol}. Exception: {exceptionMsg}"))
        return None


    def get_last_candles(self, symbol:MarketId, count:int=24, timeFrame:str='1h') -> Optional[ListOfCandles]:
        '''
        Obtiene las ultimas velas del mercado
        Si se produce un error, lo intenta nuevamente varias veces antes de fallar.
        param symbol: Mercado al que se le van a leer las velas.
        param count: Cantidad de velas hacia atras que se deben buscar.
        param timeFrame: Temporalidad de las velas que se deben buscar.
        return: Devuelve una lista con las velas obtenidas. Si falla devuelve None.
        '''
        timeFrame = self.exchange.timeframes.get(timeFrame, None)
        if timeFrame is None:
            self.log.exception(self.cmd(f"Error: El timeFrame {timeFrame} no esta soportado por el exchange."))
            return None
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.fetch_ohlcv(symbol, timeFrame, params={'sort':'DESC', 'limit':count})
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        msg1 = f"Error: Obteniendo las ultimas {count} velas {timeFrame} del mercado {symbol}. Exception: {exceptionMsg}"
        self.log.exception(self.cmd(msg1))
        return None


    def get_order_book(self, symbol:MarketId, count:int=24):
        '''
        Obtiene las ultimas velas del mercado
        Si se produce un error, lo intenta nuevamente varias veces antes de fallar.

        Parámetros
        symbol: Mercado al que se le van a leer las velas.
        count: Cantidad de velas hacia atras que se deben buscar.
        timeFrame: Temporalidad de las velas que se deben buscar.
        
        Resultado
        Devuelve una lista con las velas obtenidas. Si falla devuelve None.
        '''
        '''
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.fetch_ohlcv(
                    symbol,
                    timeFrame,
                    params={'sort':'DESC', 'limit':count}
                )
            except:
                time.sleep(self.insistencePauseSeconds)
        '''
        return None


    def round_to_precision(self, value:float, symbol:MarketId, precisionType:PrecisionType) -> float:
        '''
        Recibe un valor numerico y redondea sus decimales segun la precision del mercado.
        Esto es porque los exchanges aceptan solo una cantidad especifica de decimales 
        en los valores de monto que se compran o venden.
        param value: Valor que debe ser ajustado.
        param symbol: Identificador del mercado de donde se toma la precision.
        param precisionType: Tipo de precision "price", "amount" o "cost"
        return: Devuelve el valor redondeado a la cantidad de decimales especificada por el exchange.
        '''
        try:
            precision = self.exchange.markets[symbol]["precision"][precisionType]
            return round(value, precision)
        except:
            return value
        
        
    def execute_market_buy(self, symbol:MarketId, amountAsBase:float, params:Dict) -> Optional[Order]:
        '''
        Ejecuta una orden de compra a precio de mercado.
        param symbol: Identificador del mercado donde se debe ejecutar la compra.
        param amountAsBase: Cantidad de currecy base que se debe comprar.
        param params: Otros parametros que se le pasan a la orden de compra.
        return: Objeto con los datos y estado de la orden insertada. Si ocurre error, devuelve None.
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.create_market_buy_order(symbol, amountAsBase)
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        msg1 = f"Error: Comprando {amountAsBase} a precio de mercado en {symbol}. Exception: {exceptionMsg}"
        self.log.exception(self.cmd(msg1))
        return None
        
        
    def execute_market_sell(self, symbol:MarketId, amountAsBase:float, params:Dict) -> Optional[Order]:
        '''
        Ejecuta una orden de venta a precio de mercado.
        param symbol: Identificador del mercado donde se debe ejecutar la venta.
        param amountAsBase: Cantidad de currecy base que se debe vender.
        param params: Otros parametros que se le pasan a la orden de venta.
        return: Objeto con los datos y estado de la orden insertada. Si ocurre error, devuelve None.
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.create_market_sell_order(symbol, amountAsBase)
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        msg1 = f"Error: Vediendo {amountAsBase} a precio de mercado en {symbol}. Exception: {exceptionMsg}"
        self.log.exception(self.cmd(msg1))
        return None
        
        
    def get_order(self, orderId:str, symbol:MarketId) -> Optional[Order]:
        '''
        Obtiene una orden por su ID.
        param orderId: Identificador de la orden. Se obtiene al poner la orden.
        return: 
        Esto hay que termiarlo para que verifique el resultado de la cacelacio...
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.fetch_order(orderId, symbol=symbol)
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        msg1 = f"Error: Obteniendo la orden {orderId} en {symbol}. Exception: {exceptionMsg}"
        self.log.exception(self.cmd(msg1))
        return None
        
        
    def cancel_order(self, orderId:str, symbol:MarketId) -> Optional[Order]:
        '''
        Cancela una orden por su ID.
        param orderId: Identificador de la orden. Se obtiene al poner la orden.
        return: 
        Esto hay que termiarlo para que verifique el resultado de la cacelacio...
        '''
        exceptionMsg = ""
        for i in range(self.insistenceCountMax):
            try:
                return self.exchange.cancel_order(orderId, symbol=symbol)
            except Exception as e:
                exceptionMsg = str(e)
                time.sleep(self.insistencePauseSeconds) 
        msg1 = f"Error: Cancelando orden {orderId} en {symbol}. Exception: {exceptionMsg}"
        self.log.exception(self.cmd(msg1))
        return None
        
        
            
# Codigo de ejemplo y test.
if __name__ == "__main__":
    x = ExchangeInterface('hitbtc', "", "", 'kkk')
    import json
    print(json.dumps(x.get_tickers(["BTC/USDT"]), indent=4))
