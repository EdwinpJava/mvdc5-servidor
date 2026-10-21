# -*- coding: utf-8 -*-

import sys
import os

PASSWORD = ""

def verify_password():
    import getpass
    try:
        entered = getpass.getpass(prompt="Ingrese la contraseña para acceder a esta carpeta: ")
    except:
        entered = input("Ingrese la contraseña para acceder a esta carpeta: ")
    
    if entered.strip() != PASSWORD:
        print("\033[91mContraseña incorrecta. Cerrando...\033[0m")
        try:
            sys.exit(1)
        except:
            os._exit(1)

if __name__ == "__main__":
    verify_password()
    print("\033[92mAcceso concedido. Bienvenido al Easter Egg!\033[0m")
