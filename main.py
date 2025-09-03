#Iniciar UI
import ctypes
import sys
import os
from forms.form_login import App

def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass

def main():
    set_dpi_awareness()
    os.environ['TK_SILENCE_DEPRECATION'] = '1'
    
    try:
        app = App()
        app.ventana.mainloop()
    except Exception as e:
        print(f"Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()