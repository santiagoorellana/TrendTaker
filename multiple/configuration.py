
from trendtaker_core import *
import json
import datetime


DEFAULT_CONFIGURATION = {
    "debugMode": False,
    "forceCloseInvestmentAndExit": False,
    "currencyQuote": "USDT",
    "amountToInvestAsQuote": 10,
    "amountIsPercentOfBalance": False,
    "blackList": ["DEMONIO", "KILLER"],
    "preselected": ["BTC", "ETH"],
    "maxCurrenciesToInvest": 10,
    "createWebReport": True,
    "showWebReport": True,
    "telegramToken": "",
    "telegramChatId": "",
    "maxTickersToSelect": 50,
    "candlesDays": 7,
    "filters": {
        "note": "Todos los valores de filtro se expresan en porciento.",
        "tickers": {
            "minProfit": 0,
            "maxSpread": 1,
             "maxSpreadOverProfit": 33,
            "minProfitOverAmplitude": 33
        },
        "candles": {
            "maxColapses": 20,
            "minCompletion": 85,
            "minProfitWhole": 3.0,
            "minProfitLastHalf": 3.0,
            "minProfitLastQuarter": 3.0
        }
    }
}


class Configuration():

    def __init__(self, botId:str, log:Any=None, toLog:bool=True, toConsole:bool=False):
        self.botId = botId
        self.log = log
        self.toLog = toLog
        self.toConsole = toConsole
        self.data = DEFAULT_CONFIGURATION

    
    def create_example_file(self, fileName:str, configurationExample:Any) -> bool:
        ''' 
        Crea un fichero JSON de ejemplo de configuracion.\n
        param fileName: Nombre y ruta del fichero que se debe crear.
        param configurationExample: Objeto con el ejemplo de configuracion
        return: True si logra crear el fichero correctamente. False si ocurre error.
        '''
        try:
            with open(fileName, 'w') as file:
                file.write(json.dumps(configurationExample, indent=4))
            return True
        except Exception as e:
            msg1 = f'Error creando el fichero de configuracion de ejemplo.'
            msg2 = f'Exception: {str(e)}'
            if self.log is not None and self.toLog:
                self.log.error(f"{msg1} {msg2}")
            if self.toConsole:
                print(f"{msg1}\n{msg2}")
        return False


    def load(self) -> bool:
        '''
        Carga la configuracion desde un fichero JSON que y lo guarda en la propiedad "configuration" de la clase.
        Si el fichero de configuracion no existe, establece la configuracion por defecto y crea el fichero.
        Puede mostrar mensajes por pantalla y registrar en el log, segun los parametros del bot.\n
        return: True si logra cargar la configuracion. False si ocurre error o no la carga.
        '''
        try:
            fileNameConfiguration = f'{self.botId}_configuration.json'
            fileNameConfigurationExample = f'{self.botId}_configuration_example.json'
            self.core.data_to_file_json(DEFAULT_CONFIGURATION, fileNameConfigurationExample)
            loadedConfiguration = self.core.data_from_file_json(fileNameConfiguration, report=False)
            if loadedConfiguration is not None:
                self.configuration = loadedConfiguration
            else:
                self.core.data_to_file_json(DEFAULT_CONFIGURATION, fileNameConfiguration)
                msg1 = '\nError: No se econtro un fichero de configuracion para el bot.'
                msg2 = f'ATENCION: Se ha creado un fichero de configuracion default: "{fileNameConfiguration}"'
                msg3 = 'Debe revisar o editar el fichero de configuracion antes de volver a ejecutar el bot.'
                if self.toLog: 
                    self.log.error(msg1)
                    self.log.error(msg2)
                    self.log.error(msg3)
                if self.toConsole: 
                    print(msg1)
                    print(msg2)
                    print(msg3)
                return False
            msg1 = 'La configuracion actual es:'
            if self.toLog: 
                self.log.info(f"{msg1} {str(self.configuration)}")
            if self.toConsole: 
                TrendTakerCore.show_object(self.configuration, f"\n{msg1}") 
            return True
        except Exception as e:
            msg1 = f'Error: No se pudo establecer la configuracion del bot. Exception: {str(e)}'
            if self.toLog: self.log.exception(msg1)
            if self.toConsole: print(msg1)
            return False


