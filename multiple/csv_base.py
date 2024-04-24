import os
from file_manager import *
from basics import *


class CsvBase(Basics):
    
    def __init__(self, fileName:str, headers:List=[], log:Optional[Logger]=None):
        '''
        Crea un objeto para manejar ficheros csv.
        param fileName: Ruta y nombre del fichero con extension csv.
        '''
        self.log = log
        self.headers = headers
        self.fileName = fileName
        if not os.path.isfile(self.fileName):
            self._create_csv_file()




    def _create_csv_file(self) -> bool:
        '''
        Crea un nuevo fichero csv.
        return: Devuelve True si logra crear el ficehro csv. De lo contrario devuelve False.
        '''
        if FileManager.data_to_file_text(self._csv_line(self.headers), self.fileName, self.log):
            return True
        else:
            return False
        
        


    def write(self, data) -> bool:
        '''
        Escribe una linea con los datos, en el fichero csv.
        param data: Datos que se debes escribir en el fichero csv.
        return: Devuelve True si logra escribir el dato en el fichero csv. De lo contrario devuelve False.
        '''
        if os.path.isfile(self.fileName):
            return FileManager.data_to_file_text(self._csv_line_from(data), self.fileName, self.log)
        else:
            if self.log is not None:
                self.log.error(self.cmd(f'No existe el fichero: "{self.fileName}"'))
            return self._create_csv_file()
    

    
    
    def _csv_line(self, valuesList:List[str], separator:str=",", endLine:str="") -> str:
        '''
        Crea una linea CSV de los valores de la lista, con el separador y final de linea especificados.
        param valuesList: Lista de los valores para crear la linea CSV.
        param separator: Caracter separador de los valores.
        param endLine: Caracter que marca el final de la linea.
        return: Devuelve una cadena en formato CSV con los valores de la lista.        
        '''
        line = separator.join(valuesList)
        return line + endLine + '\n'



        
    def _csv_line_from(self, data):
        '''
        Crea una linea CSV a partir de los datos
        Este metodo debe ser sobrescrito por la clase que lo hereda.
        '''
        return ""
            

        