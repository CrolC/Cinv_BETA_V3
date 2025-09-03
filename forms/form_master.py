import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps, ImageTk
import sqlite3
import sys
import threading
import time
import serial
import serial.tools.list_ports
import tkinter.filedialog as filedialog
import os 
from tkinter import messagebox
from forms.form_nuevoproceso import FormNuevoProceso
from forms.form_paneldecontrol import FormPaneldeControl
from forms.form_historial import FormHistorial
from forms.form_monitoreo import FormMonitoreo
from forms.form_diagnostico import FormDiagnostico

COLOR_BARRA_SUPERIOR = "#1a1e23"
COLOR_MENU_LATERAL = "#1f3334"
COLOR_CUERPO_PRINCIPAL = "#f4f8f7"
COLOR_MENU_CURSOR_ENCIMA = "#18a9b1"

##Probably delete the diagnostic and control panel forms (Under consideration)
class MasterPanel(ctk.CTk):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self._imagenes = []
        self.paneles_activos = {}
        self.lock = threading.Lock()
        self.panel_actual = None
        self.bloqueo_activo = False
        self.panel_con_bloqueo = None
        self.paneles_serial = {}  # Diccionario para almacenar paneles que reciben mensajes seriales
        
        # Conexión serial
        self.serial_connection = None
        self.serial_lock = threading.Lock()
        self.serial_thread = None
        self.serial_running = False
        self.serial_buffer = ""
        self.serial_timeout = 2
        self.max_command_length = 16000000000
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.config_window()

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(BASE_DIR, "imagenes", "logocinves_predeterm.png")
        self.logo = self.leer_imagen(logo_path, (400, 400))


        # Cargar imagen de perfil si existe
        self.perfil_path = self.obtener_ruta_perfil()
        if self.perfil_path:
            self.perfil = self.leer_imagen_circular(self.perfil_path, (100, 100))
        else:
            # Imagen por defecto
            perfil_path = os.path.join(BASE_DIR, "imagenes", "Perfil.png")
            self.perfil = self.leer_imagen_circular(perfil_path, (100, 100))
        
        self.paneles()
        self.controles_barra_superior()
        self.controles_menu_lateral()
        self.controles_cuerpo()
        
        self.after(100, self.iniciar_conexion_serial_async)

    def obtener_ruta_perfil(self):
        try:
            conn = sqlite3.connect("usuarios.db")
            cursor = conn.cursor()
            cursor.execute("SELECT imagen_perfil FROM usuarios WHERE id=?", (self.user_id,))
            resultado = cursor.fetchone()
            conn.close()
            return resultado[0] if resultado and resultado[0] else None
        except:
            return None

    def leer_imagen(self, path, size):
        try:
            pil_image = Image.open(path)
            pil_image = pil_image.resize(size, Image.LANCZOS)
            image = ctk.CTkImage(pil_image, size=size)
            if not hasattr(self, '_imagenes'):
                self._imagenes = []
            self._imagenes.append(image)
            return image
        except Exception as e:
            print(f"Error al cargar la imagen {path}: {e}")
            placeholder = ctk.CTkImage(Image.new('RGB', size, (200, 200, 200)), size=size)
            if not hasattr(self, '_imagenes'):
                self._imagenes = []
            self._imagenes.append(placeholder)
            return placeholder

    def leer_imagen_circular(self, path, size):
        """Carga una imagen y la recorta en forma circular con bordes suaves"""
        try:
            from PIL import Image, ImageDraw, ImageOps, ImageFilter

            # Tamaño para el supersampling (4x más grande para antialiasing)
            supersample_size = (size[0] * 4, size[1] * 4)
            
            # Abrir imagen y redimensionar con antialiasing
            pil_image = Image.open(path).convert("RGBA")
            pil_image = pil_image.resize(supersample_size, Image.LANCZOS)

            # Crear máscara circular en alta resolución
            mask = Image.new('L', supersample_size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, *supersample_size), fill=255)  # Círculo en alta resolución

            # Reducir la máscara para suavizar bordes
            mask = mask.resize(size, Image.LANCZOS)

            # Ligero desenfoque al borde (1 píxel)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=0.7))

            # Aplicar máscara a la imagen (ya redimensionada al tamaño final)
            pil_image = pil_image.resize(size, Image.LANCZOS)
            output = Image.new("RGBA", size)
            output.paste(pil_image, (0, 0), mask)

            # Convertir a CTkImage
            image = ctk.CTkImage(output, size=size)
            
            # Guardar referencia para evitar garbage collection
            if not hasattr(self, '_imagenes'):
                self._imagenes = []
            self._imagenes.append(image)
            
            return image
        except Exception as e:
            print(f"Error al cargar imagen circular: {e}")
            # Placeholder circular con bordes suaves
            placeholder = Image.new('RGBA', size, (200, 200, 200, 0))
            draw = ImageDraw.Draw(placeholder)
            draw.ellipse((0, 0, *size), fill=(200, 200, 200, 255))
            return ctk.CTkImage(placeholder, size=size)

    def config_window(self):
        self.title('Cinvestav')
        try:
            self.iconbitmap("d:/Python_Proyectos/INTER_C3/imagenes/logo.ico")
        except Exception as e:
            print(f"Error al cargar el ícono: {e}")
        self.centrar_ventana(1024, 600)

    def centrar_ventana(self, ancho, alto):
        pantall_ancho = self.winfo_screenwidth()
        pantall_largo = self.winfo_screenheight()
        x = int((pantall_ancho / 2) - (ancho / 2))
        y = int((pantall_largo / 2) - (alto / 2))
        self.geometry(f"{ancho}x{alto}+{x}+{y}")

    def paneles(self):        
        self.barra_superior = ctk.CTkFrame(self, fg_color=COLOR_BARRA_SUPERIOR, height=50)
        self.barra_superior.pack(side=ctk.TOP, fill='both')
        
        self.menu_lateral = ctk.CTkFrame(self, fg_color=COLOR_MENU_LATERAL, width=150)
        self.menu_lateral.pack(side=ctk.LEFT, fill='both', expand=False)
        
        self.cuerpo_principal = ctk.CTkFrame(self, fg_color=COLOR_CUERPO_PRINCIPAL)
        self.cuerpo_principal.pack(side=ctk.RIGHT, fill='both', expand=True)
        self.cuerpo_principal.grid_rowconfigure(0, weight=1)
        self.cuerpo_principal.grid_columnconfigure(0, weight=1)

    def controles_barra_superior(self):
        font_awesome = ctk.CTkFont(family="FontAwesome", size=12)
        
        self.labelTitulo = ctk.CTkLabel(self.barra_superior, text="Sistema MBE", 
                                      text_color="white", font=ctk.CTkFont(family="Roboto", size=15))
        self.labelTitulo.pack(side=ctk.LEFT, padx=10, pady=10)
        
        self.buttonMenuLateral = ctk.CTkButton(self.barra_superior, text="\uf022", font=font_awesome, 
                                             command=self.toggle_panel, fg_color=COLOR_BARRA_SUPERIOR, 
                                             text_color="white")
        self.buttonMenuLateral.pack(side=ctk.LEFT, padx=5)
        
        self.labelInfo = ctk.CTkLabel(self.barra_superior, 
                                    text="Crecimiento por Epitaxia de Haces Moleculares", 
                                    text_color="white", font=ctk.CTkFont(family="Roboto", size=10))
        self.labelInfo.pack(side=ctk.RIGHT, padx=10, pady=10)


    def controles_menu_lateral(self):
        ancho_menu = 20
        alto_menu = 2
        font_awesome = ctk.CTkFont(family="FontAwesome", size=15)
        
        try:
            if hasattr(self, 'perfil') and self.perfil:
                
                self.labelPerfil = ctk.CTkButton(
                    self.menu_lateral, 
                    image=self.perfil, 
                    text="", 
                    fg_color=COLOR_MENU_LATERAL,
                    hover_color=COLOR_MENU_CURSOR_ENCIMA,
                    command=self.cambiar_foto_perfil  
                )
            else:
                self.labelPerfil = ctk.CTkButton(
                    self.menu_lateral, 
                    text="Click para\ncambiar foto", 
                    fg_color=COLOR_MENU_LATERAL,
                    hover_color=COLOR_MENU_CURSOR_ENCIMA,
                    command=self.cambiar_foto_perfil
                )
            self.labelPerfil.pack(side=ctk.TOP, pady=10)

        except Exception as e:
            print(f"Error al crear label de perfil: {e}")
            self.labelPerfil = ctk.CTkLabel(self.menu_lateral, text="Perfil", 
                                          fg_color=COLOR_MENU_LATERAL)
            self.labelPerfil.pack(side=ctk.TOP, pady=10)
        
        self.menu_buttons = {}
        buttons_info = [
            ("nuevoproceso", "Nuevo proceso", "\uf144", self.abrir_nuevoproceso),  
            ("historial", "Historial", "\uf07c", self.abrir_historial), 
            ("diagnostico", "Diagnóstico", "\uf044", self.abrir_diagnostico), 
            ("paneldecontrol", "Panel de Control", "\uf080", self.abrir_paneldecontrol), 
            ("monitoreo", "Monitoreo del Proceso", "\uf017", self.abrir_monitoreo) 
        ]
        
        for key, text, icon, command in buttons_info:
            button = ctk.CTkButton(
                self.menu_lateral, 
                text=f"  {icon}    {text}", 
                font=font_awesome, 
                anchor="w", 
                fg_color=COLOR_MENU_LATERAL, 
                text_color="white", 
                hover_color=COLOR_MENU_CURSOR_ENCIMA, 
                command=lambda k=key: self.actualizar_boton_activo(k)
            )
            button.pack(side=ctk.TOP, fill="x", padx=5, pady=5)
            self.menu_buttons[key] = button


    def cambiar_foto_perfil(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar imagen de perfil",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg"), ("Todos los archivos", "*.*")]
        )
        
        if filepath:
            try:
                # Guardar en la base de datos
                conn = sqlite3.connect("usuarios.db")
                cursor = conn.cursor()
                cursor.execute("UPDATE usuarios SET imagen_perfil=? WHERE id=?", 
                            (filepath, self.user_id))
                conn.commit()
                conn.close()
                
                # Actualizar la imagen en la interfaz
                nuevo_perfil = self.leer_imagen(filepath, (100, 100))
                self.perfil = nuevo_perfil
                self.labelPerfil.configure(image=self.perfil)
                
                messagebox.showinfo("Éxito", "Foto de perfil actualizada correctamente")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar la foto: {str(e)}")

    def actualizar_boton_activo(self, boton_key):
        for key, button in self.menu_buttons.items():
            button.configure(fg_color=COLOR_MENU_LATERAL)
        
        if boton_key in self.menu_buttons:
            self.menu_buttons[boton_key].configure(fg_color=COLOR_MENU_CURSOR_ENCIMA)
        
        if boton_key == "nuevoproceso":
            self.abrir_nuevoproceso()
        elif boton_key == "historial":
            self.abrir_historial()
        elif boton_key == "diagnostico":
            self.abrir_diagnostico()
        elif boton_key == "paneldecontrol":
            self.abrir_paneldecontrol()
        elif boton_key == "monitoreo":
            self.abrir_monitoreo()

    def controles_cuerpo(self):
        if not hasattr(self, 'panel_inicial'):
            try:
                if hasattr(self, 'logo') and self.logo:
                    self.panel_inicial = ctk.CTkLabel(self.cuerpo_principal, image=self.logo, text="", 
                                                    fg_color=COLOR_CUERPO_PRINCIPAL)
                else:
                    self.panel_inicial = ctk.CTkLabel(self.cuerpo_principal, 
                                                    text="Bienvenido al Sistema MBE", 
                                                    font=ctk.CTkFont(size=20), 
                                                    fg_color=COLOR_CUERPO_PRINCIPAL)
                
                self.panel_inicial.pack(fill="both", expand=True)
                self.panel_actual = self.panel_inicial
            except Exception as e:
                print(f"Error al crear el cuerpo principal: {e}")

    def mostrar_panel(self, nombre):
        if self.panel_actual and self.panel_actual.winfo_exists():
            self.panel_actual.pack_forget()
        
        if nombre in self.paneles_activos and self.paneles_activos[nombre].winfo_exists():
            panel = self.paneles_activos[nombre]
        else:
            if nombre == "nuevoproceso":
                panel = FormNuevoProceso(self.cuerpo_principal, self.user_id)
            elif nombre == "paneldecontrol":
                panel = FormPaneldeControl(self.cuerpo_principal, self.user_id)
            elif nombre == "historial":
                panel = FormHistorial(self.cuerpo_principal, self.user_id)
            elif nombre == "diagnostico":
                panel = FormDiagnostico(self.cuerpo_principal, self.user_id)
            elif nombre == "monitoreo":
                panel = FormMonitoreo(self.cuerpo_principal, self.user_id)
            else:
                return
                
            self.paneles_activos[nombre] = panel
        
        panel.pack(fill="both", expand=True)
        self.panel_actual = panel

    def toggle_panel(self):
        if self.menu_lateral.winfo_ismapped():
            self.menu_lateral.pack_forget()
        else:
            self.menu_lateral.pack(side=ctk.LEFT, fill='both', expand=False)  

    def abrir_nuevoproceso(self):
        self.mostrar_panel("nuevoproceso")
        
    def abrir_paneldecontrol(self):
        self.mostrar_panel("paneldecontrol")
        
    def abrir_historial(self):
        self.mostrar_panel("historial")
        
    def abrir_diagnostico(self):
        self.mostrar_panel("diagnostico")
        
    def abrir_monitoreo(self):
        self.mostrar_panel("monitoreo")

    def verificar_ejecucion(self, nombre_panel):
        with self.lock:
            if self.bloqueo_activo and self.panel_con_bloqueo != nombre_panel:
                messagebox.showwarning(
                    "Hardware ocupado",
                    f"No se pueden enviar comandos. El panel {self.panel_con_bloqueo} está controlando las válvulas."
                )
                return False
            return True

    def activar_bloqueo_hardware(self, nombre_panel):
        with self.lock:
            self.bloqueo_activo = True
            self.panel_con_bloqueo = nombre_panel

    def liberar_bloqueo_hardware(self):
        with self.lock:
            self.bloqueo_activo = False
            self.panel_con_bloqueo = None

    def registrar_panel_serial(self, nombre, panel):
        """Registra un panel para recibir mensajes seriales"""
        with self.lock:
            self.paneles_serial[nombre] = panel
    
    def desregistrar_panel_serial(self, nombre):
        """Elimina un panel de la lista de receptores de mensajes seriales"""
        with self.lock:
            if nombre in self.paneles_serial:
                del self.paneles_serial[nombre]

    def iniciar_conexion_serial_async(self):
        threading.Thread(
            target=self.iniciar_conexion_serial,
            daemon=True,
            name="SerialConnectionThread"
        ).start()

    def iniciar_conexion_serial(self):
        try:
            puertos = serial.tools.list_ports.comports()
            if not puertos:
                self.after(0, lambda: messagebox.showwarning(
                    "Advertencia", 
                    "No se detectaron puertos seriales. La aplicación continuará en modo sin conexión."
                ))
                return False

            for puerto in puertos:
                try:
                    with self.serial_lock:
                        if self.serial_connection and self.serial_connection.is_open:
                            self.serial_connection.close()
                        
                        self.serial_connection = serial.Serial(
                            port=puerto.device,
                            baudrate=9600,#115200
                            timeout=self.serial_timeout,
                            write_timeout=self.serial_timeout
                        )
                        time.sleep(2)
                        
                        self.serial_connection.reset_input_buffer()
                        self.serial_connection.reset_output_buffer()
                        
                        self.serial_connection.write(b"ESTADO?\n")
                        time.sleep(0.5)
                        
                        if self.serial_connection.in_waiting:
                            respuesta = self.serial_connection.read(
                                self.serial_connection.in_waiting
                            ).decode('utf-8', errors='ignore')
                            
                            if any(f"M{i}" in respuesta for i in range(1, 10)):
                                self.serial_running = True
                                self.serial_thread = threading.Thread(
                                    target=self.leer_datos_serial,
                                    daemon=True,
                                    name="SerialReadThread"
                                )
                                self.serial_thread.start()
                                print(f"Conexión establecida con {puerto.device}")
                                self.after(0, lambda: self.actualizar_estado_conexion(True))
                                return True
                        
                        self.serial_connection.close()
                        self.serial_connection = None
                        
                except Exception as e:
                    print(f"Intento de conexión fallido en {puerto.device}: {e}")
                    continue
            
            self.after(0, lambda: messagebox.showwarning(
                "Advertencia", 
                "No se encontró un dispositivo de control conectado. La aplicación continuará en modo sin conexión."
            ))
            return False
            
        except Exception as e:
            print(f"Error en la conexión serial: {e}")
            self.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Error al conectar con el puerto serial: {str(e)}"
            ))
            return False

    def actualizar_estado_conexion(self, conectado):
        color = "green" if conectado else "red"
        if hasattr(self, 'labelInfo'):
            self.labelInfo.configure(text_color=color)

    def leer_datos_serial(self):
        while self.serial_running:
            try:
                with self.serial_lock:
                    if not (self.serial_connection and self.serial_connection.is_open):
                        time.sleep(1)
                        continue
                    
                    bytes_to_read = self.serial_connection.in_waiting
                    if bytes_to_read > 0:
                        data = self.serial_connection.read(bytes_to_read).decode('utf-8', errors='ignore')
                        self.serial_buffer += data
                        
                        while '\n' in self.serial_buffer:
                            linea, self.serial_buffer = self.serial_buffer.split('\n', 1)
                            self.procesar_mensaje_serial(linea.strip())
            except serial.SerialException as e:
                print(f"Error de comunicación serial: {e}")
                self.reconectar_serial()
                time.sleep(1)
            except Exception as e:
                print(f"Error general en lectura serial: {e}")
                time.sleep(1)

    def procesar_mensaje_serial(self, mensaje):
        print(f"Mensaje recibido: {mensaje}")
        
        with self.lock:
            panels = list(self.paneles_serial.items())
        
        for nombre, panel in panels:
            if hasattr(panel, 'procesar_mensaje'):
                try:
                    self.after(0, lambda p=panel, m=mensaje: p.procesar_mensaje(m))
                except Exception as e:
                    print(f"Error al notificar a {nombre}: {e}")

    def reconectar_serial(self):
        with self.serial_lock:
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            self.serial_running = False
            if self.serial_thread and self.serial_thread.is_alive():
                self.serial_thread.join(timeout=1)
            
            if self.iniciar_conexion_serial():
                print("Reconexión serial exitosa")
            else:
                print("No se pudo reconectar el puerto serial")

    def enviar_comando_serial(self, comando):
        try:
            if not comando.endswith('\n'):
                comando += '\n'
                
            if len(comando) > self.max_command_length:
                print(f"Comando demasiado largo ({len(comando)} bytes)")
                return False
                
            with self.serial_lock:
                if not (self.serial_connection and self.serial_connection.is_open):
                    print("Error: No hay conexión serial disponible")
                    return False
                
                self.serial_connection.write(comando.encode('utf-8'))
                self.serial_connection.flush()
                print(f"Comando enviado: {comando.strip()}")
                return True
                
        except serial.SerialException as e:
            print(f"Error de comunicación serial: {e}")
            self.reconectar_serial()
            return False
        except Exception as e:
            print(f"Error inesperado al enviar comando: {e}")
            return False

    def on_close(self):
        try:
            self.serial_running = False
            if hasattr(self, 'serial_thread') and self.serial_thread and self.serial_thread.is_alive():
                self.serial_thread.join(timeout=1)
            
            with self.serial_lock:
                if hasattr(self, 'serial_connection') and self.serial_connection and self.serial_connection.is_open:
                    self.serial_connection.close()
                    print("Conexión serial cerrada")
            
            for nombre, panel in self.paneles_activos.items():
                if panel and hasattr(panel, 'proceso_en_ejecucion') and panel.proceso_en_ejecucion:
                    if hasattr(panel, 'reiniciar_rutina'):
                        panel.reiniciar_rutina()
                    elif hasattr(panel, 'paro_emergencia'):
                        panel.paro_emergencia()
            
            for nombre, panel in list(self.paneles_activos.items()):
                if panel and panel.winfo_exists():
                    try:
                        panel.pack_forget()
                        panel.destroy()
                    except Exception as e:
                        print(f"Error al destruir panel {nombre}: {e}")
            
            if hasattr(self, '_imagenes'):
                for img in self._imagenes:
                    try:
                        if hasattr(img, '_PhotoImage__photo'):
                            img._PhotoImage__photo = None
                    except:
                        pass
                self._imagenes.clear()
            
            self.quit()
            self.destroy()
            
        except Exception as e:
            print(f"Error durante el cierre: {e}")
            import os
            os._exit(0)

    def __del__(self):
        try:
            self.serial_running = False
            if hasattr(self, 'serial_thread') and self.serial_thread and self.serial_thread.is_alive():
                self.serial_thread.join(timeout=1)
            
            if hasattr(self, 'serial_connection') and self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            if hasattr(self, 'paneles_serial'):
                self.paneles_serial.clear()
        except Exception as e:
            print(f"Error en limpieza de MasterPanel: {e}")

if __name__ == "__main__":
    app = MasterPanel()  
    app.mainloop()