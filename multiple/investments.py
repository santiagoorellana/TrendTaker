
from basics import *
import logging
from typing import Dict, Optional
from file_manager import *
from ledger import Ledger

InvestmentsData = Dict
CloseInvestmentResult = Dict
InvestmentStatus = Dict

class Investments(Basics):
    
    def __init__(self, botId:str, directoryLedger:str, initialDateTimeUTC=None):
        self.botId = botId
        self.prepare_directory(directoryLedger)
        self.log = logging.getLogger(botId)
        self.ledger = Ledger(self.botId, directoryLedger) 
        self.fileName = f'./{self.botId}_current_investment.json'
        self.data:InvestmentsData = {
            "initialDateTimeUTC": initialDateTimeUTC,
            "initialBalanceQuote": 0.0,
            "finalBalanceQuote": 0.0,
            "totalFeeAsQuote": 0.0,
            "totalProfitAsQuote": 0.0,
            "totalExposureHours": 0.0,
            "minProfitAsPercent": None,
            "minProfitAsQuote": None,            
            "maxProfitAsPercent": None,
            "maxProfitAsQuote": None,            
            "investments": {}
        }


  
    def load_from_file(self) -> bool:
        '''
        Carga desde un fichero los datos de las inversiones actuales en curso.\n
        return: True si encuentra un fichero y logra cargar los datos. False si no se cargan datos.
        '''
        dataFromFile = FileManager.data_from_file_json(self.fileName, False, self.log)
        if dataFromFile is not None:
            msg1 = f'Se ha encontrado un fichero de datos de inversiones actuales": "{self.fileName}"'
            self.log.info(self.cmd(msg1))
            if type(dataFromFile) != dict:
                self.log.error(self.cmd('Error: La estructura del fichero de datos de inversiones actuales no es correcta.'))
                return False
            if len(dataFromFile["investments"]) == 0:
                self.log.info(self.cmd('El fichero de datos de inversiones actuales no contiene datos.'))
                return True
            else:
                self.log.info(self.cmd(f'Cantidad de inversiones actuales: {len(dataFromFile["investments"])}'))
            index = 1
            for key in dataFromFile["investments"].keys():
                investment = dataFromFile["investments"][key]
                if self._is_valid_current_investment_structure(investment): 
                    symbolId = investment["symbol"]
                    base = self.base_of_symbol(investment["symbol"])
                    quote = self.quote_of_symbol(investment["symbol"])                                
                    msg1 = f'{index}: Inversion en {investment["symbol"]}'
                    msg2 = f'cantidad comprada: {investment["buy"]["amountAsBase"]} {base}'
                    msg3 = f'precio de compra: {investment["buy"]["price"]} {quote}'
                    self.log.info(f'{msg1} {msg2} {msg3}')
                    self.cmd(f'\n{msg1}\n{INDENT}{msg2}\n{INDENT}{msg3}')
                    self.data["investments"][symbolId] = investment
                    self.log.info(self.cmd(f'{INDENT}Se han cargado los datos de la iversion en {symbolId}.'))
                else:
                    self.log.error(self.cmd(f'{index}: Error en los datos de la inversion en el mercado {symbolId}'))
                time.sleep(1)
                index += 1
            print()
            time.sleep(3)
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
        self.data["investments"][symbolId] = {
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
        if self.data["initialDateTimeUTC"] is None:
            self.data["initialDateTimeUTC"] = order["datetime"]
            self.data["initialBalanceQuote"] = balanceQuote
        self.data["finalBalanceQuote"] = balanceQuote
        self.data["totalFeeAsQuote"] += float(order["fee"]["cost"])
        FileManager.data_to_file_json(self.data, self.fileName, self.log)
        self.ledger.write(order, balanceQuote)
        return True
        
        
        
    def close(self, symbolId:MarketId, order, balanceQuote:float) -> CloseInvestmentResult:
        if self.data["initialDateTimeUTC"] is None:
            self.data["initialDateTimeUTC"] = order["datetime"]
            self.data["initialBalanceQuote"] = balanceQuote
        self.data["finalBalanceQuote"] = balanceQuote
        self.data["totalFeeAsQuote"] += float(order["fee"]["cost"])
        result = dict(self.data["investments"][symbolId]).copy()
        result["sell"] = {
            "id": order["id"],
            "price": order["average"],
            "amountAsBase": order["amount"],
            "fee": order["fee"]["cost"],
            "timestamp": order["timestamp"],
            "datetimeUTC": order["datetime"]
        }
        amountAsQuoteBuy = float(result["buy"]["amountAsBase"]) * float(result["buy"]["amountAsBase"])
        amountAsQuoteSell = float(result["sell"]["amountAsBase"]) * float(result["sell"]["amountAsBase"])
        hours = float((result["sell"]["timestamp"] - result["buy"]["timestamp"]) / 1000 / 60 / 60)
        profitAsPercent = self.delta(amountAsQuoteBuy, amountAsQuoteSell),
        profitAsQuote = amountAsQuoteSell - amountAsQuoteBuy
        
        self.data["totalProfitAsQuote"] += (amountAsQuoteSell - amountAsQuoteBuy)
        self.data["totalExposureHours"] += hours
        if self.data["minProfitAsPercent"] is None:
            self.data["minProfitAsPercent"] = profitAsPercent
            self.data["maxProfitAsPercent"] = profitAsPercent
            self.data["minProfitAsQuote"] = profitAsQuote
            self.data["maxProfitAsQuote"] = profitAsQuote
        else:
            self.data["minProfitAsPercent"] = min(self.data["minProfitAsPercent"], profitAsPercent)
            self.data["maxProfitAsPercent"] = max(self.data["maxProfitAsPercent"], profitAsPercent)
            self.data["minProfitAsQuote"] = min(self.data["minProfitAsQuote"], profitAsQuote)
            self.data["maxProfitAsQuote"] = max(self.data["maxProfitAsQuote"], profitAsQuote)
            
        result["result"] = {
            "fee": result["buy"]["fee"] + result["sell"]["fee"],
            "hours": hours,
            "profitAsPercent": profitAsPercent,
            "profitAsQuote": profitAsQuote
        }
        del self.data["investments"][symbolId]
        FileManager.data_to_file_json(self.data, self.fileName, self.log)
        self.ledger.write(order, balanceQuote)
        return result    
    


    def contains(self, marketId:MarketId) -> bool:
        return marketId in self.data["investments"]
    

    
    def get(self, marketId:MarketId) -> Optional[Dict]:
        if self.contains(marketId):
            return self.data["investments"][marketId]
        else:
            return None
    
    
    
    def markets(self) -> ListOfMarketsId:
        return list(self.data["investments"].keys())

    
    
    def empty(self) -> bool:
        if self.data["investments"] is None:
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
    
    
       
    
    
    