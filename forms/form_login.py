import customtkinter as ctk
from tkinter import messagebox
import sqlite3
import sys
import os
import util.generic as utl
from forms.form_master import MasterPanel

#completo

CODIGO_SEGURIDAD = "u6404c3101"  # Código de seguridad para registrarse

def inicializar_base_datos():
    conn = sqlite3.connect("usuarios.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    imagen_perfil TEXT)''')
    
    # Actualizar procesos.db con la columna user_id
    conn_procesos = sqlite3.connect("procesos.db")
    cursor_procesos = conn_procesos.cursor()
    
    # Verificar si la tabla existe
    cursor_procesos.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='procesos'")
    table_exists = cursor_procesos.fetchone()
    
    if table_exists:
        # Verificar si la columna user_id existe
        cursor_procesos.execute("PRAGMA table_info(procesos)")
        columns = [column[1] for column in cursor_procesos.fetchall()]
        if 'user_id' not in columns:
            # Agregar la columna si no existe
            cursor_procesos.execute("ALTER TABLE procesos ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
    
    cursor_procesos.execute('''CREATE TABLE IF NOT EXISTS procesos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            fecha_inicio TEXT NOT NULL,
                            fecha_fin TEXT,
                            hora_instruccion TEXT NOT NULL,
                            valvula_activada TEXT NOT NULL,
                            tiempo_valvula INTEGER NOT NULL,
                            ciclos INTEGER NOT NULL,
                            estado_valvula TEXT NOT NULL,
                            FOREIGN KEY (user_id) REFERENCES usuarios(id))''')
    
    conn.commit()
    conn_procesos.commit()
    conn.close()
    conn_procesos.close()

class App:

    def safe_destroy(self):
        """Método seguro para destruir la ventana"""
        if hasattr(self, 'ventana') and self.ventana:
            try:
                # Cancelar todos los after pendientes
                for id in self.ventana.tk.eval('after info').split():
                    try:
                        self.ventana.after_cancel(id)
                    except:
                        pass
            
                # Destruir widgets hijos primero
                for child in self.ventana.winfo_children():
                    try:
                        child.destroy()
                    except:
                        pass
            
                # Dstruir la ventana principal
                self.ventana.quit()
                self.ventana.destroy()
            except Exception as e:
                print(f"Error durante el cierre: {e}")
                import os
                os._exit(0)  # Salida forzosa como último recurso


    def verificar(self):
        usu = self.usuario.get()
        password = self.password.get()

        conn = sqlite3.connect("usuarios.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE usuario=? AND password=?", (usu, password))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            user_id = resultado[0]  # Obtener el ID
            self.safe_destroy()
            master_panel = MasterPanel(user_id)  # Pasar el ID
            master_panel.mainloop()
        else:
            messagebox.showerror(message="Usuario o contraseña incorrectos", title="Error")


    def registrar_usuario(self):
        usu = self.usuario_registro.get()
        password = self.password_registro.get()
        codigo = self.codigo_seguridad_entry.get()

        if not all([usu, password, codigo]):
            messagebox.showwarning("Error", "Todos los campos son obligatorios")
            return

        # Verificar código de seguridad
        if codigo != CODIGO_SEGURIDAD:
            messagebox.showerror("Error", "Código de seguridad incorrecto")
            return

        conn = sqlite3.connect("usuarios.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE usuario=?", (usu,))
        if cursor.fetchone():
            messagebox.showwarning("Error", "El usuario ya existe")
        else:
            cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)", (usu, password))
            conn.commit()
            messagebox.showinfo("Éxito", "Usuario registrado exitosamente")
            self.ventana_registro.destroy()
        conn.close()


    def mostrar_ventana_registro(self):
        self.ventana_registro = ctk.CTkToplevel(self.ventana)
        self.ventana_registro.title("Registrar usuario")
        self.ventana_registro.geometry("400x250")  # Aumentamos el tamaño para el nuevo campo
        self.ventana_registro.protocol("WM_DELETE_WINDOW", self.ventana_registro.destroy)

        # Frame principal para organizar mejor los elementos
        frame_principal = ctk.CTkFrame(self.ventana_registro)
        frame_principal.pack(pady=20, padx=20, fill="both", expand=True)

        # Campo de usuario
        #ctk.CTkLabel(frame_principal, text="Usuario:").pack()
        self.usuario_registro = ctk.CTkEntry(frame_principal, width=200, placeholder_text="usuario")
        self.usuario_registro.pack(pady=5)

        # Campo de contraseña
        #ctk.CTkLabel(frame_principal, text="Contraseña:").pack()
        self.password_registro = ctk.CTkEntry(frame_principal, width=200, show="*", placeholder_text="contraseña")
        self.password_registro.pack(pady=5)

        # Campo de código de seguridad
        #ctk.CTkLabel(frame_principal, text="Código de seguridad:").pack()
        self.codigo_seguridad_entry = ctk.CTkEntry(frame_principal, width=200,show="*", placeholder_text="código de seguridad")
        self.codigo_seguridad_entry.pack(pady=5)

        # Botón de registro
        registrar_btn = ctk.CTkButton(
            frame_principal, 
            text="Registrar", 
            command=self.registrar_usuario, 
            fg_color="#06918A"
        )
        registrar_btn.pack(pady=20)

    def __init__(self):
        inicializar_base_datos()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("green")

        self.ventana = ctk.CTk()
        self.ventana.title('Inicio de sesión')
        self.ventana.geometry('800x500')
        self.ventana.resizable(width=False, height=False)
        self.ventana.protocol("WM_DELETE_WINDOW", self.safe_destroy)
        utl.centrar_ventana(self.ventana, 800, 500)

        # Frame del logo
        frame_logo = ctk.CTkFrame(self.ventana, width=400, corner_radius=0, fg_color="#06918A")  
        frame_logo.pack(side="left", expand=True, fill="both")

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  
        logo_path = os.path.join(BASE_DIR, "imagenes", "logo.png")
        logo = utl.leer_imagen(logo_path, (200, 200))

        label_logo = ctk.CTkLabel(frame_logo, image=logo, text="")
        label_logo.place(relx=0.5, rely=0.5, anchor="center")

        # Frame del formulario
        frame_form = ctk.CTkFrame(self.ventana, corner_radius=0)
        frame_form.pack(side="right", expand=True, fill="both")

        title = ctk.CTkLabel(frame_form, 
                           text="Sistema de Crecimiento\npor Epitaxia de\nHaces Moleculares", 
                           font=ctk.CTkFont(size=25, weight="bold"), 
                           justify="center")
        title.pack(pady=30, padx=20, anchor="n") 

        self.usuario = ctk.CTkEntry(frame_form, placeholder_text="Usuario", font=ctk.CTkFont(size=14))
        self.usuario.pack(pady=10, padx=20, fill="x")

        self.password = ctk.CTkEntry(frame_form, placeholder_text="Contraseña", font=ctk.CTkFont(size=14), show="*")
        self.password.pack(pady=10, padx=20, fill="x")

        inicio = ctk.CTkButton(frame_form, text="Iniciar sesión", font=ctk.CTkFont(size=15, weight="bold"),
                             command=self.verificar, fg_color="#06918A")
        inicio.pack(pady=20, padx=20, fill="x")

        registro = ctk.CTkButton(frame_form, text="Registrarse", font=ctk.CTkFont(size=15), 
                               command=self.mostrar_ventana_registro, fg_color="#06918A")
        registro.pack(pady=10, padx=20, fill="x")

        self.ventana.bind("<Return>", lambda event: self.verificar())#enter para iniciar sesión

if __name__ == "__main__":
    app = App()
    app.ventana.mainloop()