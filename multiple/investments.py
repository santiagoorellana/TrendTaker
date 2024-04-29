
from basics import *
import logging
from typing import Dict, Optional
from file_manager import *
from file_ledger import FileLedger
from file_investments import FileInvestments

InvestmentsData = Dict
CloseInvestmentResult = Dict
InvestmentStatus = Dict

class Investments(Basics):
    
    def __init__(self, botId:str, exchangeId:str, directoryLedger:str, quote:CurrencyId):
        self.botId = botId
        self.exchangeId = exchangeId
        self.prepare_directory(directoryLedger)
        self.log = logging.getLogger(botId)
        self.fileLedger = FileLedger(self.botId, directoryLedger) 
        self.fileInvestments = FileInvestments(self.botId, directoryLedger) 
        self.fileName = f'./{self.botId}_{self.exchangeId}_{quote}_investments.json'
        self.data:InvestmentsData = {
            "initial": {
                "datetimeUTC": None,
                "timestamp": None,
                "balanceQuote": 0.0
            },
            "final": {
                "datetimeUTC": None,
                "timestamp": None,
                "balanceQuote": 0.0
            },
            "total": {
                "investmentsCount": 0,
                "feeAsQuote": 0.0,
                "profitAsQuote": 0.0,
                "hours": 0.0,
                "exposureHours": 0.0
            },
            "statistics": {
                "minProfitAsPercent": None,
                "minProfitAsQuote": None,            
                "maxProfitAsPercent": None,
                "maxProfitAsQuote": None,       
                "profitAsQuoteInBalance": None,
                "profitAsPercentInBalance": None
            },
            "currentInvestments": {} 
        }



  
    def load_from_file(self) -> bool:
        '''
        Carga desde un fichero los datos de las inversiones actuales en curso.\n
        return: True si encuentra un fichero y logra cargar los datos. False si no se cargan datos.
        '''
        dataFromFile = FileManager.data_from_file_json(self.fileName, False, self.log)
        if dataFromFile is not None:
            msg1 = f'\nSe ha encontrado un fichero de datos de inversiones actuales": "{self.fileName}"'
            self.log.info(self.cmd(msg1))
            if type(dataFromFile) != dict:
                self.log.error(self.cmd('Error: La estructura del fichero de datos de inversiones actuales no es correcta.'))
                return False
            if len(dataFromFile["currentInvestments"]) == 0:
                self.log.info(self.cmd('El fichero de datos de inversiones actuales no contiene datos.'))
                return True
            else:
                self.log.info(self.cmd(f'Cantidad de inversiones actuales: {len(dataFromFile["currentInvestments"])}'))
            index = 1
            for key in dataFromFile["currentInvestments"].keys():
                investment = dataFromFile["currentInvestments"][key]
                if self._is_valid_current_investment_structure(investment): 
                    symbolId = investment["symbol"]
                    base = self.base_of_symbol(investment["symbol"])
                    quote = self.quote_of_symbol(investment["symbol"])                                
                    msg1 = f'{index}: Inversion en {investment["symbol"]}'
                    msg2 = f'cantidad comprada: {investment["buy"]["amountAsBase"]} {base}'
                    msg3 = f'precio de compra: {investment["buy"]["price"]} {quote}'
                    #self.log.info(f'{msg1} {msg2} {msg3}')
                    #self.cmd(f'\n{msg1}\n{INDENT}{msg2}\n{INDENT}{msg3}')
                    self.data["currentInvestments"][symbolId] = investment
                    self.log.info(self.cmd(f'Se han cargado los datos de la iversion en {symbolId}.', INDENT))
                else:
                    self.log.error(self.cmd(f'{index}: Error en los datos de la inversion en el mercado {symbolId}'))
                time.sleep(1)
                index += 1
            print()
            time.sleep(3)
            return True
        return False




    def open(
            self,
            symbolId:MarketId, 
            amountAsBase:float, 
            lastPrice:float,
            order,
            balanceQuote:float,
            profitPercent:Optional[float]=None, 
            maxLossPercent:Optional[float]=None, 
            trailingStop:bool=False,
            takeProfitPrice:Optional[float]=None,
            stopLossPrice:Optional[float]=None,
            maxHours:Optional[float]=None
        ) -> bool:
        self.data["currentInvestments"][symbolId] = {
            "symbol": symbolId,
            "amountAsBase": amountAsBase,
            "lastTickerPrice": lastPrice,
            "buy": {
                "id": order["id"],
                "price": order["average"],
                "amountAsBase": order["amount"],
                "fee": order["fee"]["cost"],
                "timestamp": order["timestamp"],
                "datetimeUTC": order["datetime"]
            },
            "forExit": {
                "profitPercent": profitPercent, 
                "maxLossPercent": maxLossPercent, 
                "trailingStop": trailingStop,
                "takeProfitPrice": takeProfitPrice,
                "stopLossPrice": stopLossPrice,
                "maxHours": maxHours
            }
        }
        self._setBorders(order, balanceQuote)        
        self.data["total"]["feeAsQuote"] += float(order["fee"]["cost"])
        FileManager.data_to_file_json(self.data, self.fileName, self.log)
        self.fileLedger.write(order)
        return True
        

        
        
    def close(self, symbolId:MarketId, order, balanceQuote:float) -> CloseInvestmentResult:
        self._setBorders(order, balanceQuote)
        result = dict(self.data["currentInvestments"][symbolId]).copy()
        result["sell"] = {
            "id": order["id"],
            "price": order["average"],
            "amountAsBase": order["amount"],
            "fee": order["fee"]["cost"],
            "timestamp": order["timestamp"],
            "datetimeUTC": order["datetime"]
        }
        amountAsQuoteBuy = float(result["buy"]["amountAsBase"]) * float(result["buy"]["price"])
        amountAsQuoteSell = float(result["sell"]["amountAsBase"]) * float(result["sell"]["price"])
        exposureHours = float((result["sell"]["timestamp"] - result["buy"]["timestamp"]) / 1000 / 60 / 60)
        totalHours = float((self.data["final"]["timestamp"] - self.data["initial"]["timestamp"]) / 1000 / 60 / 60)
        profitAsPercent = self.delta(amountAsQuoteBuy, amountAsQuoteSell)
        profitAsQuote = amountAsQuoteSell - amountAsQuoteBuy
        
        self.data["total"]["investmentsCount"] += 1
        self.data["total"]["feeAsQuote"] += float(order["fee"]["cost"])
        self.data["total"]["profitAsQuote"] += (amountAsQuoteSell - amountAsQuoteBuy)
        self.data["total"]["hours"] = totalHours
        self.data["total"]["exposureHours"] += exposureHours
        
        if self.data["statistics"]["minProfitAsPercent"] is None:
            self.data["statistics"]["minProfitAsPercent"] = profitAsPercent
            self.data["statistics"]["maxProfitAsPercent"] = profitAsPercent
            self.data["statistics"]["minProfitAsQuote"] = profitAsQuote
            self.data["statistics"]["maxProfitAsQuote"] = profitAsQuote
            self.data["statistics"]["profitAsQuoteInBalance"] = 0.0
            self.data["statistics"]["profitAsPercentInBalance"] = 0.0
        else:
            self.data["statistics"]["minProfitAsPercent"] = min(self.data["statistics"]["minProfitAsPercent"], profitAsPercent)
            self.data["statistics"]["maxProfitAsPercent"] = max(self.data["statistics"]["maxProfitAsPercent"], profitAsPercent)
            self.data["statistics"]["minProfitAsQuote"] = min(self.data["statistics"]["minProfitAsQuote"], profitAsQuote)
            self.data["statistics"]["maxProfitAsQuote"] = max(self.data["statistics"]["maxProfitAsQuote"], profitAsQuote)
            self.data["statistics"]["profitAsQuoteInBalance"] = (self.data["final"]["balanceQuote"] - self.data["initial"]["balanceQuote"])
            self.data["statistics"]["profitAsPercentInBalance"] = self.delta(self.data["initial"]["balanceQuote"], self.data["final"]["balanceQuote"])
            
        result["result"] = {
            "fee": result["buy"]["fee"] + result["sell"]["fee"],
            "hours": exposureHours,
            "profitAsPercent": profitAsPercent,
            "profitAsQuote": profitAsQuote
        }
        del self.data["currentInvestments"][symbolId]
        FileManager.data_to_file_json(self.data, self.fileName, self.log)
        self.fileLedger.write(order)
        self.fileInvestments.write(result)
        return result    
    



    def _setBorders(self, order, balanceQuote):
        if self.data["initial"]["datetimeUTC"] is None:
            self.data["initial"]["datetimeUTC"] = order["datetime"]
            self.data["initial"]["timestamp"] = order["timestamp"]
            self.data["initial"]["balanceQuote"] = balanceQuote
        self.data["final"]["datetimeUTC"] = order["datetime"]
        self.data["final"]["timestamp"] = order["timestamp"]
        self.data["final"]["balanceQuote"] = balanceQuote




    def contains(self, marketId:MarketId) -> bool:
        return marketId in self.data["currentInvestments"]

    

    
    def get(self, marketId:MarketId) -> Optional[Dict]:
        if self.contains(marketId):
            return self.data["currentInvestments"][marketId]
        else:
            return None
    

    
    
    def markets(self) -> ListOfMarketsId:
        return list(self.data["currentInvestments"].keys())

    

    
    def empty(self) -> bool:
        if self.data["currentInvestments"] is None:
            return True
        return len(self.markets()) == 0

    

    
    def count(self) -> int:
        return len(list(self.markets()))

    

    
    def _is_valid_current_investment_structure(self, data:Dict) -> bool:
        '''
        Verifica que la estructura de los datos de la inversion actual sea correcta.
        Se comprueba que existan todos los parametros.\n
        param data: Datos a los que se les debe verificar y comprobar la estructura.
        return: True si los datos son correctos. De lo contrario devuelve False.
        '''
        return True
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
            self.log.exception(self.cmd(f'Error en los datos de la inversion actual. Exception: {str(e)}'))
            return False
    
    
       
    
    
    