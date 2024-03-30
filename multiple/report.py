
import os
import webbrowser
from typing import Any, Dict, Literal, Optional, List
import datetime
from exchange_interface import ListOfCandles
import plotly.graph_objects as go # type: ignore
from market_metrics import Metrics, MetricsSummary
from basics import *
import logging


Formats = Literal["png", "jpg", "jpeg", "webp", "svg", "pdf"]
Category = Literal["potentialMarket", "openInvest", "closedInvest"]

DIRECTORY_GRAPHICS = "./graphics/"

class Report(Basics):
    
    def __init__(self, core, botId:str, exchangeId:str, directory:str='./', extension:Formats='png'):
        '''
        Crea un objeto para mostrar graficos de velas.
        param format: Formato con que se guarda la imagen. Pueden ser "png", "jpg", "jpeg", "webp", "svg" o "pdf".
        param directory: Directorio donde se crean los ficheros de los graficos.
        '''
        self.log = logging.getLogger(botId)
        self.core = core
        self.botId = botId
        self.exchangeId = exchangeId
        self.directory = directory
        self.subdirectory = ""
        self.extension = extension
        self.dataMarket1:List[Dict] = []
        self.fileName = ""
        self.showLists = False
        self.centralLine = True
        self.uniqueDateTimeLabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.subdirectory = f"{self.directory}marquets_{self.uniqueDateTimeLabel}/"
        self.prepare_directory(self.subdirectory)
        
    @staticmethod
    def prepare_directory(directoryPath:str) -> bool:
        '''
        Crea el directorio especificado si este no existe.
        param directoryPath: Nombre del directorio icluyedo la ruta completa. Ej: "./graphics/"
        '''
        try:
            os.stat(directoryPath)
        except:
            try:
                os.mkdir(directoryPath)   
            except Exception as e:
                Report.cmd(f'Error: Creando el directorio: {directoryPath}')
                return False
        return True


    def create_unique_filename(self) -> str:
        '''
        Crea un nombre de fichero unico utilizando la fecha-hora actual y la extension.
        return: Cadena con un nombre de fichero unico.
        '''
        dateTimeLabel = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f'{self.botId}_{self.exchangeId}__{dateTimeLabel}.{self.extension}' 
    

    def append_market_data(self, imageFileName:str, data:Dict, category:Category) -> bool:
        '''
        Agrega a los datos de la web un fichero de imagen y datos descriptivos.
        param imageFileName: Nombre y ruta de un fichero de imagen existente.
        param data: Objeto Dict con los datos descriptivos de la imagen.
        return: True si se logro agregar el dato. De lo contrario, retorna False.
        '''
        try:
            self.dataMarket1.append({
                "imageFileName": imageFileName,
                "data": data
            })    
            return True  
        except Exception as e:
            msg1 = f'Error: Agregando datos para la web.'
            self.log.exception(f'{self.cmd(msg1)} Exception: {str(e)}Image: {imageFileName}  Data: {str(data)}')
            return False
        
        
    def count_market_data(self) -> int:
        return len(self.dataMarket1)
    
    
    def create_web(self, openInBrowser:bool=False) -> bool:
        '''
        Crea un fichero HTML con los datos e imagenes.
        param fileName: Nombre y ruta del fichero que se debe crear.
        return: True si logra crear el fichero HTML. False si ocurre error.
        '''
        try:
            self.fileName = f"{self.subdirectory}index.html"
            with open(self.fileName, 'a') as file:
                file.write("<html><head><title>Markets</title></head><body><table>\n")
                for market in self.dataMarket1:
                    file.write("<tr>\n")
                    file.write(f"<td><img src='{market['imageFileName']}' width='800px'></img></td>\n")
                    file.write("<td>")
                    summary = self.summary(market["data"])
                    for key in summary.keys():
                        param = summary[key]
                        valueStr = str(f'{round(param["value"], param["decimals"])} {param["measurementUnit"]}')
                        file.write(f"<strong>{key}</strong>: <font color='#0000ff'>{valueStr}</font><br>\n")                    
                    file.write("</td>\n")
                    file.write("</tr>\n")
                file.write("</table></body></html>\n")
                if openInBrowser:
                    self.open_web()
                return True
        except Exception as e:
            msg1 = f'Error creando el fichero: "{self.fileName}".'
            self.log.exception(f"{self.cmd(msg1)} Exception: {str(e)}")
        return False
        

    def open_web(self) -> bool:
        '''
        Abre el fichero web HTML en el navegador predeterminado.
        return: True si logra abrir el fichero HTML. False si ocurre error.
        '''
        try:
            return webbrowser.open(os.path.abspath(self.fileName))
        except Exception as e:
            msg1 = 'Error: Abriendo la web en el navegador.'
            self.log.exception(f'{self.cmd(msg1)} Exception: {str(e)}  File: {self.fileName}')
            return False
        
    
    def create_graph(self, candles: ListOfCandles, title:str, fileName:str, metrics:Optional[Dict]=None, show:bool=False):
        '''
        Crea un grafico con las velas h1 para guardarlo en un fichero o mostrarlo.
        param candles: Lista obtenida mediate CCXT que contiene las velas del mercado.
        param title: Titulo que se muestra en el grafico
        param fileName: Nombre del fichero donde se guarda el grafico. Si es cadena vacia, no guarda en fichero.
        param metrics: Objeto que contiene los datos estadisticos del mercado, que se utilizan para mostrar las desviacines.
        param show: True para que se muestre el grafico en el navegador. False para que no se muestre el grafico.
        return: False si ocurre un error. True si se ejecuta correctamente.
        '''
        if fileName == "" and show == False:
            return True
        try:
            x = [self.core.exchangeInterface.exchange.iso8601(x[0]) for x in candles]
            open = [x[1] for x in candles]
            high = [x[2] for x in candles]
            low = [x[3] for x in candles]
            close = [x[4] for x in candles]
            candlestick = go.Candlestick(x=x, open=open, high=high, low=low, close=close)
            fig = go.Figure(data=[candlestick])
            fig.update_layout(xaxis_rangeslider_visible=False)
            fig.update_layout(title_text=title, title_x=0.5)
            if metrics is not None:
                trendDeviation = metrics["candles"]["whole"]["trendDeviation"]["absolute"]
                average =metrics["candles"]["whole"]["average"]
                upperMax = float(trendDeviation.get("upperMax", 0))
                lowerMin = float(trendDeviation.get("lowerMin", 0))
                upperAverage = float(trendDeviation.get("upperAverage", 0))
                lowerAverage = float(trendDeviation.get("lowerAverage", 0))
                lineStyleExtreme = dict(color='gray', width=1)
                lineStyleAverage = dict(color='blue', width=1)
                if upperMax != 0:
                    fig.add_shape(
                        type='line', x0=x[0], y0=close[0] + upperMax, x1=x[-1], y1=average + upperMax, 
                        line=lineStyleExtreme, xref='x', yref='y'
                    )
                if lowerMin != 0:
                    fig.add_shape(
                        type='line', x0=x[0], y0=close[0] + lowerMin, x1=x[-1], y1=average + lowerMin,
                        line=lineStyleExtreme, xref='x', yref='y'
                    )
                if upperAverage != 0:
                    fig.add_shape(
                        type='line', x0=x[0], y0=close[0] + upperAverage, x1=x[-1], y1=average + upperAverage,
                        line=lineStyleAverage, xref='x', yref='y'
                    )
                if lowerAverage != 0:
                    fig.add_shape(
                        type='line', x0=x[0], y0=close[0] + lowerAverage, x1=x[-1], y1=average + lowerAverage,
                        line=lineStyleAverage, xref='x', yref='y'
                    )
            if self.centralLine:
                lineStyleTrend = dict(color='orange', width=1)
                fig.add_shape(
                    type='line', x0=x[0], y0=close[0], x1=x[-1], y1=average, 
                    line=lineStyleTrend, xref='x', yref='y'
                )
            if fileName != "": 
                fig.write_image(self.subdirectory + fileName, format=self.extension, scale=5, width=1200)  #, width=1200, height=1000
            if show:
                fig.show()
            return True
        except:
            self.log.exception(self.cmd(f'Error: No se pudo crear el grafico: {title}'))
            return False


    def summary(self, metrics:Metrics) -> MetricsSummary:
        '''
        Devuelve un objeto con un resumen de las metricas del mercado.\n
        param metrics:  Objeto con las metricas del mercado..
        return: Devuelve un con el resumen de las metricas del mercado.
        '''    
        result: MetricsSummary = {
            "candles colapses": {
                "value": metrics["candles"]["whole"]["percent"]["colapses"], 
                "decimals": 2,
                "measurementUnit": "%"
            },
            "candles completion": {
                "value": metrics["candles"]["whole"]["percent"]["completion"], 
                "decimals": 2,
                "measurementUnit": "%"
            },
            "ticker 24h profit": {
                "value": metrics["ticker"]["percentage"], 
                "decimals": 2,
                "measurementUnit": "%"
            },
            f"candles {round(metrics['candles']['lastQuarter']['count'])}h (last quarter) profit as %": {
                "value": metrics["candles"]["lastQuarter"]["percent"]["changeOpenToAverage"], 
                "decimals": 2,
                "measurementUnit": "%"
            },
            f"candles {round(metrics['candles']['lastHalf']['count'])}h (last half) profit as %": {
                "value": metrics["candles"]["lastHalf"]["percent"]["changeOpenToAverage"], 
                "decimals": 2,
                "measurementUnit": "%"
            },
            f"candles {round(metrics['candles']['whole']['count'])}h (whole) profit as %": {
                "value": metrics["candles"]["whole"]["percent"]["changeOpenToAverage"], 
                "decimals": 2,
                "measurementUnit": "%"
            },
            "open": {
                "value": metrics["candles"]["whole"]["open"], 
                "decimals": 10,
                "measurementUnit": metrics["quote"]
            },
            "low": {
                "value": metrics["candles"]["whole"]["low"], 
                "decimals": 10,
                "measurementUnit": metrics["quote"]
            },
            "higt": {
                "value": metrics["candles"]["whole"]["higt"], 
                "decimals": 10,
                "measurementUnit": metrics["quote"]
            },
            "close": {
                "value": metrics["candles"]["whole"]["close"], 
                "decimals": 10,
                "measurementUnit": metrics["quote"]
            }
        }
        return result    
    
    
    
    
    
