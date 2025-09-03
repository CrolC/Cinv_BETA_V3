import customtkinter as ctk
import threading
import time
from tkinter import messagebox
import re
#notes:Maybe I'm going to delete this panel or modify some parts to change the source of information (since is no longer the microncontroller who give the vlues)

class FormDiagnostico(ctk.CTkFrame):
    def __init__(self, panel_principal, user_id):
        super().__init__(panel_principal)
        self.user_id = user_id
        self.master_panel = panel_principal.master  # Acceso al MasterPanel
        self.configure(fg_color="#f4f8f7")
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Mapeo de números de válvula a elementos
        self.valvula_map = {
            1: 'Al',
            2: 'As',
            3: 'Ga',
            4: 'In',
            5: 'N',
            6: 'Mn',
            7: 'Be',
            8: 'Mg',
            9: 'Si'
        }
        
        # Variables de estado
        self.estado_micro = "rojo"  # rojo/amarillo/verde
        self.modo_proceso = "Inactivo"
        self.estado_proceso = "Inactivo"
        self.valvulas_estado = {elemento: {'estado': 'C', 'tiempo': 0} for elemento in self.valvula_map.values()}
        self.detener_hilo = threading.Event()
        
        # Configurar interfaz
        self._crear_interfaz()
        
        # Registrar este panel para recibir mensajes seriales
        self.master_panel.registrar_panel_serial("diagnostico", self)

    def _crear_interfaz(self):
        """Crea la interfaz con los tres frames principales"""
        # Frame principal con grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # FRAME 1 - Estado de las válvulas
        self.frame_valvulas = ctk.CTkFrame(self)
        self.frame_valvulas.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self._crear_frame_valvulas()
        
        # Frame contenedor para frames 2 y 3
        self.frame_derecha = ctk.CTkFrame(self)
        self.frame_derecha.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.frame_derecha.grid_columnconfigure(0, weight=1)
        self.frame_derecha.grid_rowconfigure(0, weight=1)
        self.frame_derecha.grid_rowconfigure(1, weight=1)
        
        # FRAME 2 - Estado del microcontrolador
        self.frame_micro = ctk.CTkFrame(self.frame_derecha)
        self.frame_micro.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self._crear_frame_micro()
        
        # FRAME 3 - Estado del proceso
        self.frame_proceso = ctk.CTkFrame(self.frame_derecha)
        self.frame_proceso.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        self._crear_frame_proceso()

    def _crear_frame_valvulas(self):
        """Crea el frame con el estado de las válvulas"""
        # Título del frame
        ctk.CTkLabel(
            self.frame_valvulas, 
            text="Estado de las válvulas", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(5, 10), anchor="center")
        
        # Frame para encabezados
        header_frame = ctk.CTkFrame(self.frame_valvulas, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 5))
        
        # Encabezados
        ctk.CTkLabel(header_frame, text="Válvula", width=80, anchor="w").pack(side="left", padx=(10, 5))
        ctk.CTkLabel(header_frame, text="⏳ Tiempo", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="🔓 Abierto", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="🔒 Cerrado", width=80).pack(side="left", padx=5)
        
        # Línea divisoria
        ctk.CTkFrame(self.frame_valvulas, height=1, fg_color="#cccccc").pack(fill="x", pady=2)
        
        # Contenedor para las válvulas
        self.valvulas_container = ctk.CTkScrollableFrame(self.frame_valvulas)
        self.valvulas_container.pack(fill="both", expand=True)
        
        # Columnas del contenedor
        self.valvulas_container.grid_columnconfigure(0, weight=1)
        self.valvulas_container.grid_columnconfigure(1, weight=1)
        self.valvulas_container.grid_columnconfigure(2, weight=1)
        self.valvulas_container.grid_columnconfigure(3, weight=1)
        
        # Elementos para cada válvula
        self.valvula_widgets = {}
        for elemento in ['Al', 'As', 'Ga', 'In', 'N', 'Mn', 'Be', 'Mg', 'Si']:
            frame = ctk.CTkFrame(self.valvulas_container)
            frame.pack(fill="x", pady=2)
            
            # Nombre válvula
            ctk.CTkLabel(frame, text=elemento, width=80, anchor="w").pack(side="left", padx=(10, 5))
            
            # Tiempo
            tiempo_label = ctk.CTkLabel(frame, text="0000", width=80)
            tiempo_label.pack(side="left", padx=5)
            
            # LED Abierto (verde) (30px x 30px)
            led_abierto = ctk.CTkLabel(
                frame, 
                text="", 
                width=30, 
                height=30, 
                corner_radius=15,
                fg_color="gray"
            )
            led_abierto.pack(side="left", padx=(20, 10))
            
            # LED Cerrado (gris) (30px x 30px)
            led_cerrado = ctk.CTkLabel(
                frame, 
                text="", 
                width=30, 
                height=30, 
                corner_radius=15,
                fg_color="gray"
            )
            led_cerrado.pack(side="left", padx=(40, 10))
            
            self.valvula_widgets[elemento] = {
                'tiempo': tiempo_label,
                'led_abierto': led_abierto,
                'led_cerrado': led_cerrado
            }
        
        # Botón de actualización manual
        ctk.CTkButton(
            self.frame_valvulas, 
            text="Actualizar Estados", 
            command=self.actualizar_estados_valvulas,
            width=150,
            height=35,
            fg_color="#06918A",
            hover_color="#057a75"
        ).pack(side="bottom", pady=(10, 5))

    def _crear_frame_micro(self):
        """Crea el frame con el estado del microcontrolador"""
        ctk.CTkLabel(self.frame_micro, text="Estado del Microcontrolador", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Semaforo
        self.semaforo_micro = ctk.CTkFrame(self.frame_micro)
        self.semaforo_micro.pack(pady=10)
        
        self.led_rojo_micro = ctk.CTkLabel(self.semaforo_micro, text="", width=30, height=30, corner_radius=15, fg_color="red")
        self.led_rojo_micro.pack(pady=2)
        
        self.led_amarillo_micro = ctk.CTkLabel(self.semaforo_micro, text="", width=30, height=30, corner_radius=15, fg_color="gray")
        self.led_amarillo_micro.pack(pady=2)
        
        self.led_verde_micro = ctk.CTkLabel(self.semaforo_micro, text="", width=30, height=30, corner_radius=15, fg_color="gray")
        self.led_verde_micro.pack(pady=2)
        
        # Descripción estados
        desc_frame = ctk.CTkFrame(self.frame_micro, fg_color="transparent")
        desc_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(desc_frame, text="🔴 No hay conexión").pack(anchor="w")
        ctk.CTkLabel(desc_frame, text="🟡 Instrucciones enviadas").pack(anchor="w")
        ctk.CTkLabel(desc_frame, text="🟢 Confirmación recibida").pack(anchor="w")
        
        # Botón de prueba de conexión
        ctk.CTkButton(
            self.frame_micro, 
            text="Probar Conexión", 
            command=self.probar_conexion
        ).pack(pady=10)

    def _crear_frame_proceso(self):
        """Crea el frame con el estado del proceso"""
        ctk.CTkLabel(self.frame_proceso, text="Estado del Proceso", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Modo de trabajo
        self.modo_label = ctk.CTkLabel(self.frame_proceso, text="Modo: Inactivo")
        self.modo_label.pack(pady=5)
        
        # Semaforo estado
        self.semaforo_proceso = ctk.CTkFrame(self.frame_proceso)
        self.semaforo_proceso.pack(pady=10)
        
        self.led_rojo_proceso = ctk.CTkLabel(self.semaforo_proceso, text="", width=30, height=30, corner_radius=15, fg_color="red")
        self.led_rojo_proceso.pack(pady=2)
        
        self.led_amarillo_proceso = ctk.CTkLabel(self.semaforo_proceso, text="", width=30, height=30, corner_radius=15, fg_color="gray")
        self.led_amarillo_proceso.pack(pady=2)
        
        self.led_verde_proceso = ctk.CTkLabel(self.semaforo_proceso, text="", width=30, height=30, corner_radius=15, fg_color="gray")
        self.led_verde_proceso.pack(pady=2)
        
        # Descripción estados
        desc_frame = ctk.CTkFrame(self.frame_proceso, fg_color="transparent")
        desc_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(desc_frame, text="🔴 Inactivo").pack(anchor="w")
        ctk.CTkLabel(desc_frame, text="🟡 En espera").pack(anchor="w")
        ctk.CTkLabel(desc_frame, text="🟢 En ejecución").pack(anchor="w")
        
        # Botón de actualización
        ctk.CTkButton(
            self.frame_proceso, 
            text="Actualizar Estado", 
            command=self.actualizar_estado_proceso
        ).pack(pady=10)

    def procesar_mensaje(self, mensaje):
        """Procesa un mensaje recibido de la ESP32"""
        print(f"Mensaje recibido: {mensaje}")  # Debug
        
        # Actualizar estado micro a verde (hay comunicación)
        self.estado_micro = "verde"
        self.after(0, self.actualizar_estado_micro)
        
        # Procesar estado de todas las válvulas en un solo mensaje
        patron = r'M(\d+)([AC])'
        coincidencias = re.findall(patron, mensaje)
        
        if coincidencias:
            # Primero marcamos todas las válvulas como cerradas (por si falta alguna en el mensaje)
            for elemento in self.valvula_map.values():
                self.valvulas_estado[elemento]['estado'] = 'C'
                self.valvulas_estado[elemento]['tiempo'] = 0
            
            # Luego actualizamos las que vienen en el mensaje
            for num_valvula, estado in coincidencias:
                try:
                    num_valvula = int(num_valvula)
                    if 1 <= num_valvula <= 9:
                        elemento = self.valvula_map[num_valvula]
                        self.valvulas_estado[elemento]['estado'] = estado
                        
                        # Si está abierta, incrementar tiempo (si ya estaba abierta)
                        if estado == 'A' and self.valvulas_estado[elemento]['estado'] == 'A':
                            self.valvulas_estado[elemento]['tiempo'] += 1
                        else:
                            self.valvulas_estado[elemento]['tiempo'] = 0
                except (ValueError, KeyError):
                    continue
            
            # Actualizar interfaz
            self.after(0, self.actualizar_estados_valvulas)
        
        # Determinar estado del proceso
        if any(estado == 'A' for estado in [v['estado'] for v in self.valvulas_estado.values()]):
            self.estado_proceso = "En ejecución"
        else:
            self.estado_proceso = "Inactivo"
        
        # Determinar modo de proceso basado en el mensaje completo
        if "&" in mensaje:  # Mensaje con múltiples fases
            self.modo_proceso = "Automático"
        elif len(coincidencias) > 0:  # Mensaje con válvulas individuales
            self.modo_proceso = "Semiautomático"
        
        self.after(0, self.actualizar_estado_proceso)

    def probar_conexion(self):
        """Intenta establecer conexión con la ESP32"""
        if self.master_panel.enviar_comando_serial("ESTADO?"):
            self.estado_micro = "amarillo"
            self.after(0, self.actualizar_estado_micro)
            messagebox.showinfo("Conexión", "Solicitud de estado enviada al microcontrolador")
        else:
            self.estado_micro = "rojo"
            self.after(0, self.actualizar_estado_micro)
            messagebox.showerror("Error", "No se pudo enviar la solicitud de estado")

    def actualizar_estados_valvulas(self):
        """Actualiza la visualización del estado de las válvulas"""
        for elemento, widgets in self.valvula_widgets.items():
            estado = self.valvulas_estado[elemento]['estado']
            tiempo = self.valvulas_estado[elemento]['tiempo']
            
            widgets['tiempo'].configure(text=f"{tiempo:04d}")
            
            if estado == 'A':
                widgets['led_abierto'].configure(fg_color="green")
                widgets['led_cerrado'].configure(fg_color="gray")
            else:
                widgets['led_abierto'].configure(fg_color="gray")
                widgets['led_cerrado'].configure(fg_color="red")  

    def actualizar_estado_micro(self):
        """Actualiza el semáforo del microcontrolador"""
        self.led_rojo_micro.configure(fg_color="gray")
        self.led_amarillo_micro.configure(fg_color="gray")
        self.led_verde_micro.configure(fg_color="gray")
        
        if self.estado_micro == "rojo":
            self.led_rojo_micro.configure(fg_color="red")
        elif self.estado_micro == "amarillo":
            self.led_amarillo_micro.configure(fg_color="yellow")
        elif self.estado_micro == "verde":
            self.led_verde_micro.configure(fg_color="green")

    def actualizar_estado_proceso(self):
        """Actualiza el estado del proceso"""
        self.modo_label.configure(text=f"Modo: {self.modo_proceso}")
        
        self.led_rojo_proceso.configure(fg_color="gray")
        self.led_amarillo_proceso.configure(fg_color="gray")
        self.led_verde_proceso.configure(fg_color="gray")
        
        if self.estado_proceso == "Inactivo":
            self.led_rojo_proceso.configure(fg_color="red")
        elif self.estado_proceso == "En espera":
            self.led_amarillo_proceso.configure(fg_color="yellow")
        elif self.estado_proceso == "En ejecución":
            self.led_verde_proceso.configure(fg_color="green")


    def __del__(self):
        """Limpia recursos al destruir el objeto"""
        try:
            self.detener_hilo.set()
            # Desregistrar este panel para dejar de recibir mensajes seriales
            if hasattr(self, 'master_panel') and hasattr(self.master_panel, 'desregistrar_panel_serial'):
                self.master_panel.desregistrar_panel_serial("diagnostico")
        except Exception as e:
            print(f"Error en limpieza de Diagnóstico: {e}")