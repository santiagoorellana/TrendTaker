
from typing import Dict, List, Literal, Optional
from exchange_interface import *

Segment = Literal['whole', 'half1', 'half2', 'quarter1', 'quarter2', 'quarter3', 'quarter4', 'last']
Metrics = Dict
MetricsSummary = Dict

class MarketMetrics():
    
    ####################################################################################################
    # METODO PRICIPAL DE LA CLASE 
    # Se emplea para calcular parametros a partir de los valores de un ticker obtenido y de 
    # las ultimas velas del mercado, obtenidas con la libreria CCXT y los devuelve en un objeto.
    ####################################################################################################
    
    @staticmethod
    def calculate(ticker:Ticker, candles1h:ListOfCandles, preselected:ListOfCurrenciesId) -> Metrics:
        '''
        Devuelve un objeto con las metricas del mercado.\n
        Toma el ultimo ticker y las ultimas velas 1h del mercado, para hacer un resumen calculando
        valores estadisticos de los datos y derivados, que sirven para determinar si el mercado tiene
        potencial de ganancias.\n
        param ticker: Ultimo ticker del mercado, obtenido del exchange, mediante la librería ccxt.
        param candles1h: Lista de velas h1 obtenidas del exchange, mediante la librería ccxt.
        param candlesHours: Cantidad de velas que se necesitan para analizar el mercado.
        param preselected: Lista de currencies que deben pasar el filtro siempre y quedar en primera posicion.
        return: Devuelve un objeto con las metricas del mercado.
        '''    
        result: Metrics = {"completed": False}
        result["base"] = ExchangeInterface.base_of_symbol(ticker["symbol"])
        result["quote"] = ExchangeInterface.quote_of_symbol(ticker["symbol"])
        result["ticker"] = {
            "lastPrice": float(ticker["last"]),
            "percentage": float(ticker["percentage"]),
            "spread": MarketMetrics.ticker_spread(ticker),
            "deltaOverAmplitude": MarketMetrics.ticker_profit_over_amplitude(ticker)
        }
        result["candles"] = {
            "whole": MarketMetrics._candles_statistics(candles1h, "whole"),
            "lastHalf": MarketMetrics._candles_statistics(candles1h, "half2"),
            "lastQuarter": MarketMetrics._candles_statistics(candles1h, "quarter4")
        }
        result["potential"] = MarketMetrics._calculate_potential(result, preselected)
        result["completed"] = True
        return result    
    
    
    ####################################################################################################
    # METODOS DE USO GENERAL 
    ####################################################################################################
    
    @staticmethod
    def _delta(fromValue: float, toValue: float) -> float:
        '''
        Calcula la variación en porciento entre dos valores.
        Se puede utilizar para calcular el rendimiento de un activo o currecy.
        Para calcular el porciento, se toma como total el valor inicial "fromValue".
        param fromValue: Valor inicial.
        param toValue: Valor final.
        return: Variación en porciento entre los valores "fromValue" y "toValue".
                Si ocurre error no se maneja la excepcion.
        '''
        return (toValue - fromValue) / fromValue * 100
        

    @staticmethod
    def _linear_interpolation(X: int, X0: int, Y0: float, X1: int, Y1: float) -> float:
        '''
        Devuelve la interpolacion lineal de Y para un valor de X dado.
        param X: Valor del eje X para el que se debe calcular la Y mediante interpolacion lineal.
        param X0: Valor en el eje X del punto 0 donde inicia el segmento.
        param Y0: Valor en el eje Y del punto 0 donde inicia el segmento.
        param X1: Valor en el eje X del punto 1 donde termina el segmento.
        param Y1: Valor en el eje Y del punto 1 donde termina el segmento.
        return: Interpolacion lineal de Y para un valor de X dado.
        '''
        return float(((Y1 - Y0) / (X1 - X0)) * (X - X0) + Y0)


    @staticmethod
    def _create_trend_line(priceBegin: float, priceEnd: float, count: int) -> List[float]:
        '''
        Devuelve una linea de precios que van desde el precio inicial hasta el final.
        param priceBegin: Precio inicial desde donde se calcula la interpolacion.
        param priceEnd: Precio final hasta donde se calcula la interpolacion.
        param count: Cantidad de valores Y que deben componer a la linea de precios.
        return: Lista de precios que representa una linea que va desde el precio inicial hasta el final. 
                Si hay menos de 5 velas, devuelve None por unsuficiencia de datos.
                Si ocurre un error, devuelve None.
        '''
        try:
            if count < 3:
                return []
            return [MarketMetrics._linear_interpolation(index, 0, priceBegin, count-1, priceEnd) for index in range(count)]
        except Exception as e:
            return []


    @staticmethod
    def _calculate_potential(metrics:Metrics, preselected:ListOfCurrenciesId):
        if str(metrics["base"]).upper() in preselected or str(metrics["base"]).lower() in preselected:
            return float(1000000)
        weightedValues = [
            float(metrics["ticker"]["percentage"]),
            float(metrics["candles"]["lastQuarter"]["percent"]["changeOpenToAverage"]),
            float(metrics["candles"]["lastHalf"]["percent"]["changeOpenToAverage"]), 
            float(metrics["candles"]["whole"]["percent"]["changeOpenToAverage"])
        ]
        return float(sum(weightedValues) / len(weightedValues))



    ####################################################################################################
    # METODOS PARA TICKERS 
    # Calcula parametros a partir de los valores de un ticker obtenido mediante la libreria CCXT.
    ####################################################################################################
    
    @staticmethod
    def ticker_spread(tickerData: Ticker) -> float:
        '''
        Calcula el spread del ticker, en porciento
        param tickerData: Objeto ticker obtenido del exchange, mediante la librería CCXT.
        return: Spread en porciento utilizando como total el bid. 
                Si ocurre error, devuelve un delta muy grande, inaceptable.
        '''
        try:
            return MarketMetrics._delta(tickerData['bid'], tickerData['ask'])
        except:
            return 1000000
    

    @staticmethod
    def ticker_profit_over_amplitude(tickerData: Ticker) -> float:
        ''' 
        Devuelve la realacion entre el profit (percent) y la maxima amplitud (high - low) en porciento.
        Cada ticker que se recibe mediante la librería ccxt, tiene las estadisticas de las ultimas 24 
        horas, que incluye precios low, high y el porciento de variación entre el open y el close.\n
        Esta función devuelve la proporción en porciento entre el profit open-close con respecto a 
        la amplitud en porciento low-high. Se asume que mientras mayor es la proporcións, más fuerte 
        es el crecimiento de ese mercado.\n
        param tickerData: Objeto ticker obtenido del exchange, mediante la librería ccxt.
        return: Devuelve la realacion entre el delta (percent) y la maxima amplitud (high - low) en porciento. 
                Si ocurre un error, devuelve cero.
        '''
        try:
            delta = MarketMetrics._delta(tickerData['low'], tickerData['high'])
            return (tickerData['percentage'] / delta * 100)
        except Exception as e:
            return 0
    

    ####################################################################################################
    # METODOS PARA CANDLES (VELAS) 
    # Calculan parametros a partir de las ultimas velas del mercado, obtenidas con la libreria CCXT.
    ####################################################################################################
    
    @staticmethod
    def _is_candle_colapse(candle: Candle) -> bool:  #minDeltaAsPercent:float
        '''
        Permite saber si una vela esta colapsada.
        Una vela colapsada (doji, linea) tiene sus cuatro componentes open, low, high y close con valores 
        iguales o muy cercanos, lo cual significa que las operaciones de compra-venta se realizaron a un 
        unico precio. Por lo general eso ocurre en mercados con baja liquidez. 
        param candle: Objeto array con los valores de la vela, obtenido del exchange mediante la librería CCXT.
        param minDeltaAsPercent: Variacion minima que debe tener una vela para no cosiderarla colapsada.
                                 El porciento de variacion se calcula en referencia al precio de la currecy, 
                                 utilizando el valor minimo de la vela como total (valor inicial del delta). 
        return: True si la vela esta colapsada o si ocurre un error. False si la vela no esta colapsada.
        '''
        try:
            candleValues = candle[1:5]
            deltaPercent =  MarketMetrics._delta(min(candleValues), max(candleValues))
            result = deltaPercent < 0.1 if deltaPercent is not None else True
            return result
        except Exception as e:
            print(f"Error: Calculando el colapso de la vela. Exception: {str(e)}")
            return True
    

    @staticmethod
    def _candles_colapses(candles: ListOfCandles, minDeltaAsPercent:float=0.1) -> float:
        '''
        Devuelve el porciento de velas colapsadas
        Una vela colapsada (doji, linea) tiene sus cuatro componentes open, low, high y close con valores 
        iguales o muy cercanos, lo cual significa que las operaciones de compra-venta se realizaron a un 
        unico precio. Por lo general eso ocurre en mercados con baja liquidez. 
        Esta función evalúa el porciento de velas colapsadas y determina si es aceptable. 
        Se asume que mientras menos velas colapsadas existan en la lista, mayor es la liquidez de ese mercado.
        El cálculo se realiza con respecto al 100% de las velas presentes en la lista.
        param candles: Lista de velas obtenidas del exchange, mediante la librería ccxt.
        return: Devuelve el porciento de velas colapsadas. Si ocurre un error, devuelve 100.
        '''
        try:
            filtered = []
            for candle in candles:
                if MarketMetrics._is_candle_colapse(candle):
                    filtered.append(candle)
            return float(len(filtered) / len(candles) * 100)
        except Exception as e:
            print(f"Error: Calculando el porciento de colapso de las velas. Exception: {str(e)}")
            return float(100)


    @staticmethod
    def _candles_filter_time_range(candles: ListOfCandles, maxCandlesAgeAsHours: float) -> ListOfCandles:
        '''
        Filtra las velas teniendo en cuenta la cantidad de horas requerida.
        Cuando se piden las velas al exchange mediante la libreria ccxt, se debe especificar la 
        cantidad de velas. Cuando el mercado específico tiene poca liquidez o cuando ocurren errores, 
        la lista de velas devueltas puede tener huecos (gaps) en los datos, que son velas faltante. 
        En ese caso, el exchange devuelve la cantidad de velas pedidas, tomando del historial la 
        cantidad de velas necesarias para completar el pedido. Esto provoca que los datos devueltos 
        tengan la cantidad de velas pedidas, pero no el mismo rango de tiempo. Si se piden X cantidad 
        de velas tipo h1, se deberían obtener velas correspondientes a un rango total de X horas, 
        pero si faltan velas en los datos del exchange, entonces es posible que se obtenga un 
        rango mayor de X horas. 
        Esta función filtra la lista de velas, de manera tal que elimina las velas que estan 
        fuera del rango de tiempo correspondiente al pedido realizado. Ejemplo:
        Si se piden al exchange 10 velas tipo h1 y se obtienen velas con un rango total 
        de 15 horas, el filtro dejara pasar solo las velas correspondientes al rango de
        las ultimas 10 horas, porque 10 velas h1 equivale a un rango de 10 horas. 
        
        param candles: Lista de velas obtenidas del exchange, mediante la librería ccxt.
        param maxCandlesAgeAsHours: Rango de tiempo en horas para filtrar las velas.
        return: Lista filtrada con las velas que abarcan el rango de tiempo que corresponde 
                a la cantidad de velas pedidas al exchange. Si ocurre un error, devuelve vacio.
        '''
        try:
            MILLISECONDS_PER_HOURS = 60 * 60 * 1000
            maxCandlesAgeAsMilliseconds = float(MILLISECONDS_PER_HOURS * maxCandlesAgeAsHours)
            return list(filter(lambda candle: candles[-1][0] - candle[0] < maxCandlesAgeAsMilliseconds, candles))
        except:
            return []
        

    @staticmethod
    def _candles_1h_completion(candles1h:ListOfCandles, requestedCandlesCount:int) -> float:
        '''
        Devuelve el porciento de completitud del rango de velas de la lista.        
        Cuando se piden las velas al exchange, se especifica la cantidad de velas. 
        Es posible que en los datos devueltos falten algunas velas. 
        Esta función devuelve el porciento de completado de las velas devueltas. 
        Se asume que mientras más completo están los datos, mayor es la liquidez del mercado.
        param candles1h: Lista de velas 1h obtenidas del exchange, mediante la librería ccxt.
        param requestedCandlesCount: Cantidad de velas que se le pidieron al exchange.
        return: Porciento de completitud del rango de las velas. Si ocurre un error, devuelve None.
        '''
        try:
            candlesInTimeRange = len(MarketMetrics._candles_filter_time_range(candles1h, requestedCandlesCount))
            return float(candlesInTimeRange / requestedCandlesCount * 100)
        except Exception as e:
            return float(100)


    @staticmethod
    def _candles_slice(candles: ListOfCandles, segment: Segment, count:int=1) -> ListOfCandles:
        '''
        Devuelve un segmento de las velas.\n
        param candles: Lista de velas obtenidas del exchange, mediante la librería ccxt.
        param segment: Determina el segmento que se va a retornar.
        - "whole" = Calcula la variacion del total de las velas.
        - "half1" = Calcula la variacion de la primera mitad de las velas.
        - "half2" = Calcula la variacion de la segunda mitad de las velas.
        - "quarter1" = Calcula la variacion del primer cuarto de las velas.
        - "quarter2" = Calcula la variacion del segundo cuarto de las velas.
        - "quarter3" = Calcula la variacion del tercer cuarto de las velas.
        - "quarter4" = Calcula la variacion del ultimo cuarto de las velas.
        - "last" = Indica que se deben tomar las ultimas velas. \n
        param count: Indica la cantidad de velas a tomar cuando el parametro "segment" es igual a "last".
        return: Devuelve el segmento de velas indicado. Si ocurre un lista vacia.
        '''
        try:
            limitQ1 = round(float(len(candles)-1) * 0.25) 
            limitQ2 = round(float(len(candles)-1) * 0.5)
            limitQ3 = round(float(len(candles)-1) * 0.75)
            if segment == 'whole':
                return candles
            elif segment == 'half1':
                return candles[0:limitQ2+1]
            elif segment == 'half2':
                return candles[limitQ2:]
            elif segment == 'quarter1':
                return candles[0:limitQ1+1]
            elif segment == 'quarter2':
                return candles[limitQ1:limitQ2+1]
            elif segment == 'quarter3':
                return candles[limitQ2:limitQ3+1]
            elif segment == 'quarter4':
                return candles[limitQ3:]
            elif segment == 'last':
                if count < len(candles):
                    return candles[-count:]
                else:
                    return []
            else:
                return []
        except:
            return []



    @staticmethod
    def _candles_statistics(candles:ListOfCandles, segment:Segment='whole', count:int=1) -> Optional[Dict]:
        '''
        Devuelve estadisticas descriptivas del segmento de velas.
        param candles: Lista de velas obtenidas del exchange, mediante la librería ccxt.
        param segment: Determina el segmento al que se le calcula la varicacion. Ver type "Segment".
        param count: Indica la cantidad de velas a tomar cuando el parametro "segment" es igual a "last".
        return: Devuelve un objeto con las estadisticas descriptivas del segmento de velas.
                Si ocurre un error, devuelve None.
        '''
        try:
            sliced = MarketMetrics._candles_slice(candles, segment, count)
            if len(sliced) == 0:
                return None
            colapses = MarketMetrics._candles_colapses(sliced)
            completion = MarketMetrics._candles_1h_completion(sliced, len(sliced))    
            prices = [float(MarketMetrics._candle_estimated_average(candle)) for candle in sliced]
            average = float(sum(prices) / len(prices))
            absolutesDeviations = [abs(float(price) - average) for price in prices]
            deviation = sum(absolutesDeviations) / len(absolutesDeviations)            
            trendLine = MarketMetrics._create_trend_line(prices[0], average, len(prices))
            trendDeviation = MarketMetrics._candles_trend_deviation(sliced, trendLine) 
            return {
                "count": len(sliced),
                "open": sliced[0][CANDLE_OPEN],
                "low": min([candle[CANDLE_LOW] for candle in sliced]),
                "higt": max([candle[CANDLE_HIGT] for candle in sliced]),
                "close": sliced[-1][CANDLE_CLOSE],
                "average": average,
                "deviation": deviation,
                "percent": {
                    "colapses": colapses,
                    "completion": completion,
                    "deviation": MarketMetrics._delta(average, deviation),
                    "changeOpenToClose": MarketMetrics._delta(prices[0], prices[-1]),
                    "changeOpenToAverage": MarketMetrics._delta(prices[0], average),
                    "speedOpenToClose":  abs(prices[0] - prices[-1]) / len(sliced),
                    "speedOpenToAverage":  abs(prices[0] - average) / len(sliced)
                },
                "trendDeviation": trendDeviation
            }
        except Exception as e:
            print(e)
            return None


    @staticmethod
    def _candles_trend_deviation(candles: ListOfCandles, trendLine: List[float]) -> Optional[Dict]:
        '''
        Devuelve los datos de la desviacion de las velas con respecto a una linea.
        param candles: Lista de velas obtenidas del exchange, mediante la librería ccxt.
        param trendLine: Lista de precios que representa una linea que va desde el precio inicial hasta el final.
        return: Devuelve un objeto con los datos de la desviacion de las velas con respecto a "trendLine".
                Una parte del resultado contiene los valores absolutos de desviacion.
                La otra parte contiene los valores de desviacion expresados en porciento con respecto a la tendencia.
                Si hay menos de 5 velas, devuelve None por unsuficiencia de datos.
                Si ocurre un error, devuelve None.
        '''
        try:
            if len(candles) < 5:
                return None
            # Valores absolutos de desviacion
            deviations = list(float(candles[index][CANDLE_CLOSE]) - float(trendLine[index]) for index in range(len(candles)))
            upperDeviation = list(filter(lambda deviation: deviation > 0, deviations))
            lowerDeviation = list(filter(lambda deviation: deviation < 0, deviations))
            absolute = list(abs(deviation) for deviation in deviations)
            # Valores de desviacion expresados en porciento con respecto a la linea de tendencia.
            deviationsAsPercent = list(float(MarketMetrics._delta(float(trendLine[index]), candles[index][CANDLE_CLOSE])) for index in range(len(candles)))
            upperDeviationAsPercent = list(filter(lambda deviation: deviation > 0, deviationsAsPercent))
            lowerDeviationAsPercent = list(filter(lambda deviation: deviation < 0, deviationsAsPercent))
            absoluteAsPercent = list(abs(deviation) for deviation in deviationsAsPercent)
            return {
                "absolute": {
                    "max": max(absolute),
                    "average": sum(absolute) / len(absolute),
                    "upperMax": max(upperDeviation) if len(upperDeviation) > 0 else 0,
                    "upperAverage": sum(upperDeviation) / len(upperDeviation) if len(upperDeviation) > 0 else 0,
                    "lowerMin": min(lowerDeviation) if len(lowerDeviation) > 0 else 0,
                    "lowerAverage": sum(lowerDeviation) / len(lowerDeviation) if len(lowerDeviation) > 0 else 0
                },
                "percent": {
                    "max": max(absoluteAsPercent),
                    "average": sum(absoluteAsPercent) / len(absoluteAsPercent),
                    "upperMax": max(upperDeviationAsPercent) if len(upperDeviationAsPercent) > 0 else 0,
                    "upperAverage": sum(upperDeviationAsPercent) / len(upperDeviationAsPercent) if len(upperDeviationAsPercent) > 0 else 0,
                    "lowerMin": min(lowerDeviationAsPercent) if len(lowerDeviationAsPercent) > 0 else 0,
                    "lowerAverage": sum(lowerDeviationAsPercent) / len(lowerDeviationAsPercent) if len(lowerDeviationAsPercent) > 0 else 0
                }
            }
        except Exception as e:
            print(e)
            return None


    @staticmethod
    def _candle_estimated_average(candle: Candle) -> float:
        '''
        Devuelve una estimacion de la media (average) de los precios contenidos en la vela.
        Al no contar con la lista de precios de compra-venta que ocurren en el timeframe correspondiente
        a la vela, entonces se hace una estimacion sencilla y o rigurosa, en la cual se tienen en cuenta 
        los precios de apretura, minimo, maximo y cierre de la vela.
        param candle: Dato de una vela OHLCV obtenida del exchange, mediante la librería ccxt.
        return: Estimacion de la media (average) de los precios contenidos en la vela.
                Si ocurre un error, devuelve None.
        '''
        return float(sum(candle[1:-1]) / 4)

