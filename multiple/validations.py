
from typing import Any, Dict, Literal, Optional, List
from exchange_interface import *
from market_metrics import MarketMetrics
import logging
from basics import *


class Validations(Basics):
    
    def __init__(self, botId:str):
        self.log = logging.getLogger(botId)

    
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
            self.log.exception(Validations.cmd(f'Error en los datos de la inversion actual. Exception: {str(e)}'))
            return False
        
    
    @staticmethod
    def get_market_limit(limit:AmountLimit, symbolData:Market) -> float:
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
        base = ExchangeInterface.base_of_symbol(symbolId)
        quote = ExchangeInterface.quote_of_symbol(symbolId)
        decimals = 2 if quote.upper() == "USDT" else 12
        amountMin = Validations.get_market_limit("min", symbolData)
        amountMax = Validations.get_market_limit("max", symbolData)
        amountMinAsQuote = float(amountMin * lastPrice)
        amountMaxAsQuote = float(amountMax * lastPrice)
        if amountAsBase < amountMin:
            msg1 = f'   El monto {amountAsBase} {base} es inferior al minimo permitido en el mercado {symbolId}'
            msg2 = f'   Atencion: El monto minimo permitido en {symbolId} es de {amountMin} {base}  ({round(amountMinAsQuote, decimals)} {quote} )'
            self.log.error(Validations.cmd(msg1))
            self.log.warning(Validations.cmd(msg2))
            return False
        elif amountAsBase > amountMax:
            msg1 = f'{INDENT}El monto {amountAsBase} {base} es superior al maximo permitido en el mercado {symbolId}'
            msg2 = f'{INDENT}Atencion: El monto maximo permitido en {symbolId} es de {amountMax} {base}  ({round(amountMaxAsQuote, decimals)} {quote} )'
            self.log.error(Validations.cmd(msg1))
            self.log.warning(Validations.cmd(msg2))
            return False
        else:
            return True
        
    
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
            self.log.exception(Validations.cmd(msg1))
            return False
        return True

    
    @staticmethod
    def check(value:Optional[float], condition:ComparisonCondition, limit:Optional[float]):
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


    @staticmethod
    def is_valid_ticker(tickerData:Ticker, configuration:Dict) -> bool:
        '''
        Verifica si el ticker pertenecen a un mercado valido que cumple las condiciones de seleccion del filtro.\n
        param tickerData: Objeto ticker obtenido del exchange, mediante la librería ccxt. 
        param configuration: Objeto con la configuracion del algoritmo.
        return: True si el ticker es un mercado valido que cumple las con el filtro. De lo contrario False.
        '''
        preselected = configuration.get("preselected", [])
        base = str(ExchangeInterface.base_of_symbol(tickerData["symbol"]))
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
            if float(MarketMetrics.ticker_spread(tickerData)) > valueLimit:
                return False

        valueLimit = float(filters.get("minProfitOverAmplitude", None))
        if valueLimit is not None:
            if float(MarketMetrics.ticker_profit_over_amplitude(tickerData)) < valueLimit:
                return False
        return True


    @staticmethod
    def is_preselected(marketData, configuration:Dict) -> bool:
        '''
        Devuelve true si el mercado esta preseleccionado.\n
        param marketData: Datos y parametros del mercado que se deben comprobar.
        param configuration: Objeto con la configuracion del algoritmo.
        return: Devuelve True si el mercado esta preseleccionado. De lo contrario, devuelve False.
        '''        
        preselected = configuration.get("preselected", [])
        base = str(marketData["baseId"])
        if base.upper() in preselected or base.lower() in preselected:
            return True
        else:
            return False


    @staticmethod
    def is_potential_market(marketData, configuration:Dict) -> bool:
        '''
        Devuelve true si el mercado tiene suficiente liquidez y potencial de crecimiento.\n
        param marketData: Datos y parametros del mercado que se deben comprobar.
        param configuration: Objeto con la configuracion del algoritmo.
        return: Devuelve True si el mercado tiene liquidez y potencial de crecimiento. De lo contrario, devuelve False.
        '''        
        preselected = configuration.get("preselected", [])
        base = str(marketData["baseId"])
        if base.upper() in preselected or base.lower() in preselected:
            return True
        filters = configuration["filters"]["candles"]
        metricsOfCandles = marketData["metrics"]["candles"]["percent"]
        # Verifica si el porciento de velas colapsadas es minimo.
        if not Validations.check(metricsOfCandles["colapses"], "below", filters.get("maxColapses", None)):
            return False
        # Verifica si el porciento de completado del rango de velas es adecuado.
        if not Validations.check(metricsOfCandles["completion"], "above", filters.get("minCompletion", None)):
            return False
        # Verifica si el profit del rango completo de velas es adecuado.
        if not Validations.check(metricsOfCandles["changeWhole"], "above", filters.get("minProfitWhole", None)):
            return False
        # Verifica si el profit de la ultima mitad del rango de velas es adecuado.
        if not Validations.check(metricsOfCandles["changeHalf1"], "above", filters.get("minProfitHalf1", None)):
            return False
        # Verifica si el profit del ultimo cuarto del rango de velas es adecuado.
        if not Validations.check(metricsOfCandles["changeHalf2"], "above", filters.get("minProfitHalf2", None)):
            return False
        return True

    
    def is_liquid_market(market):
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


