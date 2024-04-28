
from basics import *
import logging
from typing import Dict, Optional
from file_manager import *

InvestmentsData = Dict
CloseInvestmentResult = Dict
InvestmentStatus = Dict



class Balances(Basics):
    
    def __init__(self, botId:str):
        self.botId = botId
        self.log = logging.getLogger(botId)
        self.initial:Balance = {}
        self.current:Optional[Balance] = None        
        
        
        
    def actualize(self, balance) -> bool:
        '''
        Recibe el balance actual de la cuenta y lo guarda en la propiedad "currentBalance" del la clase.
        return: True si logra actualizar el balance. False si ocurre error o no lo actualiza.
        '''
        self.current = balance
        if self.current is None:
            self.log.error(self.cmd('Error: No se pudo actualizar el balance actual de la cuenta.'))
            return False
        else:
            if self.initial == {}:
                self.initial = self.current
            return True



                
    def get(self, currency:CurrencyId) -> float:
        '''
        Devuelve el balance actual de la currency especificada.
        param currency: Identificador de la currency de la que se desea conocer el balance.
        return: Balance actual de la currency.
        '''
        if self.current is not None:
            if "free" in self.current:
                if currency in self.current["free"]:
                    return float(self.current["free"][currency])
        return float(0)            
        



    def show(self, currency:Optional[CurrencyId]=None):
        if self.current is not None:
            msg1 = 'El balance libre actual de la cuenta es:'
            self.log.info(f"{msg1} {str(self.current)}")
            self.show_object(self.current['free'], f"\n{msg1}") 
            if currency is not None:
                self.log.info(self.cmd(f'El balance libre actual de {currency} es: {round(self.get(currency), 10)}', "\n"))
            return True
        else:
            return False
        
        

#sufficient_quote_to_buy
                
