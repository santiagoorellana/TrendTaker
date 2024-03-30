
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


