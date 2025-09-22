import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps, ImageTk
import sqlite3
import sys
import threading
import tkinter.filedialog as filedialog
import os
from tkinter import messagebox
from forms.form_nuevoproceso import FormNuevoProceso
from forms.form_historial import FormHistorial
from forms.form_monitoreo import FormMonitoreo

COLOR_BARRA_SUPERIOR = "#1a1e23"
COLOR_MENU_LATERAL = "#1f3334"
COLOR_CUERPO_PRINCIPAL = "#f4f8f7"
COLOR_MENU_CURSOR_ENCIMA = "#18a9b1"


class MasterPanel(ctk.CTk):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self._imagenes = []
        self.paneles_activos = {}
        self.lock = threading.Lock()
        self.panel_actual = None

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

            supersample_size = (size[0] * 4, size[1] * 4)
            pil_image = Image.open(path).convert("RGBA")
            pil_image = pil_image.resize(supersample_size, Image.LANCZOS)

            mask = Image.new('L', supersample_size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, *supersample_size), fill=255)

            mask = mask.resize(size, Image.LANCZOS)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=0.7))

            pil_image = pil_image.resize(size, Image.LANCZOS)
            output = Image.new("RGBA", size)
            output.paste(pil_image, (0, 0), mask)

            image = ctk.CTkImage(output, size=size)

            if not hasattr(self, '_imagenes'):
                self._imagenes = []
            self._imagenes.append(image)

            return image
        except Exception as e:
            print(f"Error al cargar imagen circular: {e}")
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
            elif nombre == "historial":
                panel = FormHistorial(self.cuerpo_principal, self.user_id)
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

    def abrir_historial(self):
        self.mostrar_panel("historial")

    def abrir_monitoreo(self):
        self.mostrar_panel("monitoreo")

    def on_close(self):
        try:
            for nombre, panel in list(self.paneles_activos.items()):
                if panel and panel.winfo_exists():
                    try:
                        panel.pack_forget()
                        panel.destroy()
                    except Exception as e:
                        print(f"Error al destruir panel {nombre}: {e}")

            if hasattr(self, '_imagenes'):
                self._imagenes.clear()

            self.quit()
            self.destroy()
        except Exception as e:
            print(f"Error durante el cierre: {e}")
            import os
            os._exit(0)


if __name__ == "__main__":
    app = MasterPanel(user_id=1)
    app.mainloop()