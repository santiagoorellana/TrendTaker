
import logging
from logging.handlers import TimedRotatingFileHandler
import regex # type: ignore



class Basics():
    
    @staticmethod 
    def cmd(message:str, prefix:str="", suffix:str=""):
        '''
        Imprime en consola un mensaje de texto.
        param message: Mensaje de texto que se debe mostrar en la consola CMD.
        param prefix: Cadena de texto que solo se agrega delante del texto que se imprime en pantalla.
        param suffix: Cadena de texto que solo se agrega detras del texto que se imprime en pantalla.
        return: Devuelve el mismo mensaje.
        '''
        print(f"{prefix}{message}{suffix}")
        return message


    @staticmethod 
    def create_logger(name:str, fileName:str, filesCount:int, debugMode:bool) -> logging.Logger:
        '''
        Prepara la configuracion del logging para guardar mensajes en fichero
        de manera que se crea un fichero por cada dia de la semana.
        La linea que se agrega al fichero logging, contendra el nombre del script,
        la funcion o metodo y el numero de la linea donde se reporta el mensaje.\n
        param fileName: jhgjh
        param filesCount: jhgjhg
        param debugMode: jhgjh
        return: kgjh
        '''
        LOG_FORMAT = '%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)04d - %(message)s'
        handler = TimedRotatingFileHandler(fileName, when="midnight", backupCount=filesCount) 
        handler.setLevel(logging.DEBUG if debugMode else logging.INFO)
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        handler.suffix = "%Y%m%d"       # Este es el sufijo del nombre de fichero.
        handler.extMatch = regex.compile(r"^\d{8}$")   
        log = logging.getLogger(name)
        logging.root.setLevel(logging.NOTSET)
        log.addHandler(handler)
        return log


