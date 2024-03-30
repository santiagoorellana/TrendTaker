
import json
from typing import Any, Optional
from basics import *
from logging import Logger


class FileManager(Basics):

    @staticmethod
    def data_to_file_text(self, line:str, fileName:str, log:Logger=None) -> bool:
        '''
        Escribe en un fichero de texto la cadena de texto.
        param line: Cadena que contiene el texto.
        param fileName: Nombre y ruta del fichero que se debe crear.
        return: True si logra crear el fichero. False si ocurre error.
        '''
        try:
            with open(fileName, 'a') as file:
                file.write(line)
                return True
        except Exception as e:
            msg1 = f'Error creando el fichero: "{fileName}".'
            msg2 = f'Exception: {str(e)}'
            if log is not None:
                log.exception(f"{msg1} {msg2}")
            FileManager.cmd(f"{msg1}\n{msg2}")
        return False


    @staticmethod
    def data_to_file_json(data:Any, fileName:str, log:Logger=None) -> bool:
        '''
        Escribe en un fichero JSON los datos del diccionario.
        param data: Diccionario que contiene los datos.
        param fileName: Nombre y ruta del fichero que se debe crear.
        param log: Objeto que maneja los ficheros Log.
        return: True si logra crear el fichero. False si ocurre error.
        '''
        try:
            with open(fileName, 'w') as file:
                file.write(json.dumps(data, indent=4))
                return True
        except Exception as e:
            msg1 = f'Error creando el fichero: "{fileName}".'
            msg2 = f'Exception: {str(e)}'
            if log is not None:
                log.exception(f"{msg1} {msg2}")
            FileManager.cmd(f"{msg1}\n{msg2}")
        return False
        
    
    @staticmethod 
    def data_from_file_json(fileName:str, report:bool=True, log:Logger=None) -> Optional[Any]:
        '''
        Lee desde un fichero JSON los datos del diccionario.
        param fileName: Nombre y ruta del fichero que se debe leer.
        param log: Objeto que maneja los ficheros Log.
        return: Diccionario con los datos del fichero. None si ocurre error.
        '''
        try:
            with open(fileName, 'r') as file:
                return json.load(file)
        except Exception as e:
            if report:
                msg1 = f'Error leyendo el fichero: "{fileName}".'
                msg2 = f'Exception: {str(e)}'
                if log is not None:
                    log.exception(f"{msg1} {msg2}")
                FileManager.cmd(f"{msg1}\n{msg2}")
        return None



