
from basics import *
import logging
from typing import Dict, Optional
from file_manager import *
from ledger import Ledger

InvestmentsData = Dict
CloseInvestmentResult = Dict
InvestmentStatus = Dict

class Balance(Basics):
    
    def __init__(self, botId:str, directoryLedger:str):
        self.botId = botId
        self.prepare_directory(directoryLedger)
        self.log = logging.getLogger(botId)
        self.ledger = Ledger(self.botId, directoryLedger) 
        self.fileName = f'./{self.botId}_current_investment.json'
        self.totalFeeAsQuote:float = 0
        self.data:InvestmentsData = {
            "initialQuoteBalance": 0,
            "lastQuoteBalance": 0,
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
            if type(dataFromFile) != Dict:
                self.log.error(self.cmd('Error: La estructura del fichero de datos de inversiones actuales no es correcta.'))
                return False
            if len(dataFromFile) == 0:
                self.log.error(self.cmd('El fichero de datos de inversiones actuales no contiene datos.'))
                return True
            else:
                self.log.error(self.cmd(f'Cantidad de inversiones actuales: {len(dataFromFile)}'))
            for key in dataFromFile.keys():
                investment = dataFromFile[key]
                if self._is_valid_current_investment_structure(investment): 
                    symbolId = investment["symbol"]
                    base = self.base_of_symbol(investment["symbol"])
                    quote = self.quote_of_symbol(investment["symbol"])                                
                    msg1 = f'Inversion actual en {investment["symbol"]}'
                    msg2 = f'cantidad comprada: {investment["amountAsBase"]} {base}'
                    msg3 = f'precio de compra: {investment["initialPrice"]} {quote}'
                    self.log.info(f'{msg1} {msg2} {msg3}')
                    self.cmd(f'\n{msg1}\n   {msg2}\n   {msg3}\n')

                    self.data["investments"][symbolId] = investment
                    #self.initialExecutionDateTimeAsSeconds = data["initialDateTimeAsSeconds"] # debe quedarse con el mas antiguo.
                    self.log.info(self.cmd(f'Se han cargado los datos de la iversion actual en {symbolId}.'))
                else:
                    self.log.error(self.cmd(f'Error en los datos de la inversion en el mercado {symbolId}'))
        return False



    def open(
            self,
            symbolId:MarketId, 
            amountAsBase:float, 
            lastPrice:float,
            order,
            balanceQuote:float,
            timestampSeconds,
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
            "orderId": order["id"],
            "initialPrice": order["average"],
            "amountAsBase": order["amount"],
            "initialTimestampSeconds": timestampSeconds,
            "fee": order["fee"]["cost"],
            "profitPercent": profitPercent, 
            "maxLossPercent": maxLossPercent, 
            "trailingStop": trailingStop,
            "takeProfitPrice": takeProfitPrice,
            "stopLossPrice": stopLossPrice,
            "maxHours": maxHours
        }
        FileManager.data_to_file_json(self.data, self.fileName, self.log)
        self.totalFeeAsQuote += float(order["fee"]["cost"])
        self.ledger.write(order, balanceQuote)
        return True

        
        
    def close(self, symbolId:MarketId, order, balanceQuote:float, timestampSeconds) -> CloseInvestmentResult:
        del self.data["investments"][symbolId]
        FileManager.data_to_file_json(self.data, self.fileName, self.log)
        self.totalFeeAsQuote += float(order["fee"]["cost"])
        self.ledger.write(order, balanceQuote)
        return {
            "initialQuoteBalance": self.data["initialQuoteBalance"],
            "lastQuoteBalance": self.data["lastQuoteBalance"],
            "feeAsQuote": self.totalFeeAsQuote,
            "hours": "duracio de la imversiom",
            "profitAsPercent": jhgrjkag,
            "profitAsQuote": jhgrjkag,
        }
    


    def status(self) -> InvestmentStatus:
        return {
            "initialQuoteBalance": self.data["initialQuoteBalance"],
            "lastQuoteBalance": self.data["lastQuoteBalance"],
            "totalFeeAsQuote": self.totalFeeAsQuote,
            "totalHours": "duracio de la imversiom",
            "totalProfitAsPercent": jhgrjkag,
            "totalProfitAsQuote": jhgrjkag,
        }
        #return {
        #    "initialQuoteBalance": self.data["initialQuoteBalance"],
        #    "lastQuoteBalance": self.data["lastQuoteBalance"],
        #    "totalFeeAsQuote": self.totalFeeAsQuote,
        #    "totalHours": duracio desde el imicio hasta ahora,
        #    "totalProfitAsPercent": jhgrjkag,
        #    "totalProfitAsQuote": jhgrjkag,
        #}
    


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
    
    
       
    