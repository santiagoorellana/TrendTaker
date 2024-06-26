
from file_manager import *
from basics import *
import logging


DEBUG_MODE = {
    "ignoreBalance": True,      # En True, hace que se ignore el balance insuficiente.
    "simulateOrders": True,     # En True, hace que las ordenes de compra y venta sean simuladas.    
    "onlyBuyAndSell": None      # Ejecuta una compra y venta e el mercado especificado. Se desactiva con None.
}


DIRECTORY_LOGS = "./logs/"
DIRECTORY_LEDGER = "./ledger/"
DIRECTORY_GRAPHICS = "./graphics/"


DEFAULT_CONFIGURATION = {
    "debugMode": False,
    "forceCloseInvestmentAndExit": False,
    "currencyQuote": "USDT",
    "amountToInvestAsQuote": 20,
    "blackList": ["DEMONIO", "KILLER"],
    "preselected": ["BTC", "ETH"],
    "maxCurrenciesToInvest": 20,
    "createWebReport": True,
    "showWebReport": True,
    "maxTickersToSelect": 50,
    "candlesDays": 7,
    "modeActive": {
        "enable": False,
        "profitPercent": 3,
        "trailingStopEnable": False
    },
    "filters": {
        "note": "Todos los valores de filtro se expresan en porciento.",
        "tickers": {
            "minProfit": 0,
            "maxSpread": 1,
            "maxSpreadOverProfit": 33,
            "minProfitOverAmplitude": 33
        },
        "candles": {
            "maxColapses": 30,
            "minCompletion": 85,
            "minProfitWhole": 1.0,
            "minProfitHalf1": 0.0,
            "minProfitHalf2": 0.0
        }
    }
}


class Configuration(Basics):

    def __init__(self, botId:str, exchangeId:str):
        self.botId = botId
        self.exchangeId = exchangeId
        self.data:Dict = DEFAULT_CONFIGURATION
        self.log = logging.getLogger(botId)


    def load(self) -> bool:
        '''
        Carga la configuracion desde un fichero JSON que y lo guarda en la propiedad "configuration" de la clase.
        Si el fichero de configuracion no existe, establece la configuracion por defecto y crea el fichero.\n
        return: True si logra cargar la configuracion. False si ocurre error o no la carga.
        '''
        try:
            fileNameConfiguration = f'{self.botId}_configuration.json'
            fileNameConfigurationExample = f'{self.botId}_configuration_example.json'
            FileManager.data_to_file_json(DEFAULT_CONFIGURATION, fileNameConfigurationExample, self.log)
            loadedConfiguration = FileManager.data_from_file_json(fileNameConfiguration, False, self.log)
            if loadedConfiguration is not None:
                self.data = loadedConfiguration
            else:
                FileManager.data_to_file_json(DEFAULT_CONFIGURATION, fileNameConfiguration, self.log)
                self.log.error(self.cmd('Error: No se econtro un fichero de configuracion para el bot.', '\n'))
                self.log.error(self.cmd(f'ATENCION: Se ha creado un fichero de configuracion default: "{fileNameConfiguration}"'))
                self.log.error(self.cmd('Debe revisar o editar el fichero de configuracion antes de volver a ejecutar el bot.'))
                return False
            self.log.info(f"La configuracion actual es: {str(self.data)}")
            Basics.show_object(self.data, "\nLa configuracion actual es:") 
            return True
        except Exception as e:
            self.log.exception(self.cmd(f'Error: No se pudo establecer la configuracion del bot. Exception: {str(e)}'))
            return False


