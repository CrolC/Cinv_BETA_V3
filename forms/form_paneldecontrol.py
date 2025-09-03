import customtkinter as ctk
import datetime
from tkinter import messagebox
import threading
import time
import sqlite3
from datetime import datetime, date
import uuid
##maybe delete this panel (under consideration)
class FormPaneldeControl(ctk.CTkScrollableFrame):
    def __init__(self, panel_principal, user_id):  
        super().__init__(panel_principal)
        self.user_id = user_id
        self.master_panel = panel_principal.master
        
        # Improved process ID generation
        self.proceso_id = self.generar_proceso_id_diario()
        self.ultima_fecha_reinicio = date.today()
        
        # Valve control variables
        self.valvulas = ["Al", "As", "Ga", "In", "N", "Mn", "Be", "Mg", "Si"]
        self.estados_valvulas = [False] * 9
        self.tiempos_inicio = [None] * 9
        self.contadores_ciclos = [0] * 9
        self.hilos_ejecucion = [None] * 9
        self.direcciones_valvulas = ["D"] * 9
        self.stop_event = threading.Event()
        
        # Build interface
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        
        # Frame para Proceso Cíclico
        self.frame_ciclico = ctk.CTkFrame(self, fg_color="#f0f0f0")
        self.frame_ciclico.grid(row=0, column=0, padx=(10,5), pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.frame_ciclico, 
                    text="PROCESO CÍCLICO",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5,10))
        
        frame_headers = ctk.CTkFrame(self.frame_ciclico)
        frame_headers.pack(fill="x", padx=5, pady=2)
        
        ctk.CTkLabel(frame_headers, text="Válvula", width=60, anchor="w").pack(side="left")
        ctk.CTkLabel(frame_headers, text="Activar", width=60).pack(side="left", padx=5)
        ctk.CTkLabel(frame_headers, text="Apertura", width=120).pack(side="left", padx=5)
        ctk.CTkLabel(frame_headers, text="Cierre", width=120).pack(side="left", padx=5)
        ctk.CTkLabel(frame_headers, text="Ciclos", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(frame_headers, text="Actual", width=80).pack(side="left", padx=5)
        
        # Validación de entrada
        self.validar_cmd = self.register(self.validar_entrada)
        
        self.controles_ciclicos = []
        for i in range(9):
            frame_control = ctk.CTkFrame(self.frame_ciclico)
            frame_control.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(frame_control, text=self.valvulas[i], width=60, anchor="w").pack(side="left")
            
            switch = ctk.CTkSwitch(frame_control, text="", command=lambda idx=i: self.toggle_controles_ciclicos(idx))
            switch.pack(side="left", padx=5)
            
            # Apertura
            apertura_frame = ctk.CTkFrame(frame_control, fg_color="transparent")
            apertura_frame.pack(side="left", padx=5)
            apertura = ctk.CTkEntry(apertura_frame, width=50, validate="key", validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            apertura.pack(side="left")
            apertura_unidad = ctk.CTkOptionMenu(apertura_frame, values=["s", "min", "h"], width=50, state="disabled")
            apertura_unidad.set("s")
            apertura_unidad.pack(side="left", padx=5)
            apertura.bind("<KeyRelease>", lambda e, ent=apertura, unidad=apertura_unidad: self.validar_tiempo(ent, unidad))
            apertura_unidad.configure(command=lambda v, ent=apertura, unidad=apertura_unidad: self.validar_tiempo(ent, unidad))
            
            # Cierre
            cierre_frame = ctk.CTkFrame(frame_control, fg_color="transparent")
            cierre_frame.pack(side="left", padx=5)
            cierre = ctk.CTkEntry(cierre_frame, width=50, validate="key", validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            cierre.pack(side="left")
            cierre_unidad = ctk.CTkOptionMenu(cierre_frame, values=["s", "min", "h"], width=50, state="disabled")
            cierre_unidad.set("s")
            cierre_unidad.pack(side="left", padx=5)
            cierre.bind("<KeyRelease>", lambda e, ent=cierre, unidad=cierre_unidad: self.validar_tiempo(ent, unidad))
            cierre_unidad.configure(command=lambda v, ent=cierre, unidad=cierre_unidad: self.validar_tiempo(ent, unidad))
            
            # Ciclos deseados
            ciclos_deseados = ctk.CTkEntry(frame_control, width=60, validate="key", validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            ciclos_deseados.pack(side="left", padx=5)
            
            # Ciclos actuales
            ciclos_actual = ctk.CTkLabel(frame_control, text="0", width=60)
            ciclos_actual.pack(side="left", padx=5)
            
            self.controles_ciclicos.append((switch, apertura, apertura_unidad, cierre, cierre_unidad, ciclos_deseados, ciclos_actual))

        # Frame de botones para proceso cíclico
        frame_botones_ciclico = ctk.CTkFrame(self.frame_ciclico, fg_color="transparent")
        frame_botones_ciclico.pack(fill="x", padx=5, pady=(5,10))
        
        btn_ejecutar_ciclico = ctk.CTkButton(frame_botones_ciclico, text="EJECUTAR", 
                                    fg_color="#06918A", command=self.iniciar_proceso_ciclico)
        btn_ejecutar_ciclico.pack(side="right", padx=5)
        
        # Frame para Proceso Puntual
        self.frame_puntual = ctk.CTkFrame(self, fg_color="#f0f0f0")
        self.frame_puntual.grid(row=0, column=1, padx=(5,10), pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.frame_puntual, 
                    text="PROCESO PUNTUAL",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(5,10))
                
        # Encabezados
        frame_headers = ctk.CTkFrame(self.frame_puntual)
        frame_headers.pack(fill="x", padx=5, pady=2)

        # Posición de texto encabezado
        col_widths = {
            'valvula': 70,
            'activar': 70,
            'estado': 100,
            'tiempo': 120,
            't_abierto': 90,
            'acciones': 100
        }

        ctk.CTkLabel(frame_headers, text="Válvula", width=col_widths['valvula'], anchor="w").grid(row=0, column=0, padx=(0,5))
        ctk.CTkLabel(frame_headers, text="Activar", width=col_widths['activar'], anchor="center").grid(row=0, column=1, padx=5)
        ctk.CTkLabel(frame_headers, text="Estado", width=col_widths['estado'], anchor="center").grid(row=0, column=2, padx=5)
        ctk.CTkLabel(frame_headers, text="Tiempo", width=col_widths['tiempo'], anchor="center").grid(row=0, column=3, padx=5)
        ctk.CTkLabel(frame_headers, text="T. Abierto", width=col_widths['t_abierto'], anchor="center").grid(row=0, column=4, padx=5)
        ctk.CTkLabel(frame_headers, text="Acciones", width=col_widths['acciones'], anchor="center").grid(row=0, column=5, padx=5)

        # Controles
        self.controles_puntuales = []
        for i in range(9):
            frame_control = ctk.CTkFrame(self.frame_puntual)
            frame_control.pack(fill="x", padx=5, pady=2)
            
            # Válvula
            ctk.CTkLabel(frame_control, text=self.valvulas[i], width=col_widths['valvula'], anchor="w").grid(row=0, column=0, padx=(0,5))
            
            # Switch Activar
            switch_frame = ctk.CTkFrame(frame_control, width=col_widths['activar'], fg_color="transparent")
            switch_frame.grid(row=0, column=1, padx=5)
            switch = ctk.CTkSwitch(switch_frame, text="", command=lambda idx=i: self.toggle_controles_puntuales(idx))
            switch.pack(pady=3)
            
            # Estado
            estado = ctk.CTkLabel(frame_control, text="CERRADO", width=col_widths['estado'], anchor="center",
                                fg_color="#222222", text_color="white", corner_radius=5)
            estado.grid(row=0, column=2, padx=5)
            
            # Tiempo
            tiempo_frame = ctk.CTkFrame(frame_control, width=col_widths['tiempo'], fg_color="transparent")
            tiempo_frame.grid(row=0, column=3, padx=5)
            
            tiempo = ctk.CTkEntry(tiempo_frame, width=50, validate="key", validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            tiempo.pack(side="left", padx=(0,5))
            tiempo_unidad = ctk.CTkOptionMenu(tiempo_frame, values=["s", "min", "h"], width=50, state="disabled")
            tiempo_unidad.set("s")
            tiempo_unidad.pack(side="left")
            
            # Tiempo Abierto
            tiempo_transcurrido = ctk.CTkLabel(frame_control, text="00:00", width=col_widths['t_abierto'], anchor="center")
            tiempo_transcurrido.grid(row=0, column=4, padx=5)
            
            # Acciones
            btn_frame = ctk.CTkFrame(frame_control, width=col_widths['acciones'], fg_color="transparent")
            btn_frame.grid(row=0, column=5, padx=5)
            btn_invertir = ctk.CTkButton(btn_frame, text="Cerrar", width=80, state="disabled",
                                        command=lambda idx=i: self.invertir_sentido(idx))
            btn_invertir.pack()
            
            self.controles_puntuales.append((switch, estado, tiempo, tiempo_unidad, tiempo_transcurrido, btn_invertir))

        # Frame de botones para proceso puntual
        frame_botones_puntual = ctk.CTkFrame(self.frame_puntual, fg_color="transparent")
        frame_botones_puntual.pack(fill="x", padx=5, pady=(5,10))
        
        btn_ejecutar_puntual = ctk.CTkButton(frame_botones_puntual, text="EJECUTAR", 
                                    fg_color="#06918A", command=self.iniciar_proceso_puntual)
        btn_ejecutar_puntual.pack(side="right", padx=5)
        
        # Frame para Notificaciones
        self.frame_notificaciones = ctk.CTkFrame(self)
        self.frame_notificaciones.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,10), sticky="nsew")
        self.grid_rowconfigure(1, weight=1) 
        
        ctk.CTkLabel(self.frame_notificaciones, 
                    text="NOTIFICACIONES",
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5,0))
        
        self.notificaciones_text = ctk.CTkTextbox(self.frame_notificaciones, height=100, state="disabled")
        self.notificaciones_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Botón para limpiar notificaciones
        btn_limpiar = ctk.CTkButton(self.frame_notificaciones, text="Limpiar", width=80,
                                   command=self.limpiar_notificaciones)
        btn_limpiar.pack(side="right", padx=5, pady=(0,5))

        # Botón de paro de emergencia
        btn_paro = ctk.CTkButton(self.frame_notificaciones, 
                                    text="STOP EMERGENCIA", 
                                    fg_color="red", 
                                    hover_color="darkred",
                                    command=self.paro_emergencia)
        btn_paro.pack(side="right", padx=5, pady=(0,5))
        self.pack(padx=10, pady=10, fill="both", expand=True)

    def generar_proceso_id_diario(self):
        """Genera un ID de proceso único para el día actual"""
        hoy = date.today().strftime("%Y%m%d")
        return f"{hoy}_{uuid.uuid4().hex[:6]}"

    def verificar_cambio_dia(self):
        """Verifica si ha cambiado el día y actualiza el proceso_id si es necesario"""
        hoy = date.today()
        if hoy != self.ultima_fecha_reinicio:
            self.proceso_id = self.generar_proceso_id_diario()
            self.ultima_fecha_reinicio = hoy
            self.agregar_notificacion(f"Nuevo ID de proceso generado para el día: {self.proceso_id}")

    def paro_emergencia(self):
        """Detiene todos los procesos y limpia los campos"""
        # Activar evento de paro
        self.stop_event.set()
        
        # Detener procesos cíclicos
        for i in range(9):
            if self.hilos_ejecucion[i] and self.hilos_ejecucion[i].is_alive():
                self.hilos_ejecucion[i].do_run = False
                try:
                    self.hilos_ejecucion[i].join(timeout=0.5)
                except:
                    pass
                self.hilos_ejecucion[i] = None
            
            # Reiniciar contadores y limpiar campos (proceso cíclico)
            switch, apertura, apertura_unidad, cierre, cierre_unidad, ciclos_deseados, ciclos_actual = self.controles_ciclicos[i]
            switch.deselect()
            apertura.delete(0, "end")
            apertura_unidad.set("s")
            cierre.delete(0, "end")
            cierre_unidad.set("s")
            ciclos_deseados.delete(0, "end")
            ciclos_actual.configure(text="0")
            self.contadores_ciclos[i] = 0
            self.toggle_controles_ciclicos(i)
        
        # Detener procesos puntuales y limpiar campos
        for i in range(9):
            if self.estados_valvulas[i]:
                self.estados_valvulas[i] = False
                switch, estado, tiempo, tiempo_unidad, tiempo_transcurrido, btn_invertir = self.controles_puntuales[i]
                switch.deselect()
                estado.configure(text="CERRADO", fg_color="red")
                tiempo.delete(0, "end")
                tiempo_unidad.set("s")
                tiempo_transcurrido.configure(text="00:00")
                btn_invertir.configure(text="Cerrar", state="disabled")
                self.direcciones_valvulas[i] = "D"  # Resetear dirección
                self.toggle_controles_puntuales(i)
        
        # Enviar señal de emergencia a ESP32
        if self.master_panel.enviar_comando_serial("PPPPPPPPPPPPPPPP"):
            self.agregar_notificacion("¡PARO DE EMERGENCIA ACTIVADO!")
        
        # Registrar paro de emergencia en la base de datos
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        datos_emergencia = {
            'proceso_id': self.proceso_id,
            'fecha_inicio': fecha_actual,
            'fecha_fin': fecha_actual,
            'hora_instruccion': fecha_actual,
            'valvula': "PARO DE EMERGENCIA",
            'tiempo': 0,
            'ciclos': 0,
            'estado': 'E',  # E = Emergencia
            'fase': 0,
            'tipo_proceso': 'emergencia'
        }
        self.guardar_proceso_db(datos_emergencia)
        
        # Mostrar confirmación
        messagebox.showwarning("PARO DE EMERGENCIA", "Todos los procesos han sido detenidos.")
        
        # Liberar bloqueo de hardware
        self.master_panel.liberar_bloqueo_hardware()
        
        # Resetear el evento de paro para futuras ejecuciones
        self.stop_event.clear()


    def toggle_controles_ciclicos(self, idx):
        """Habilita/deshabilita controles según estado del switch"""
        switch_ciclico, apertura, apertura_unidad, cierre, cierre_unidad, ciclos_deseados, _ = self.controles_ciclicos[idx]
        switch_puntual, _, _, _, _, _ = self.controles_puntuales[idx]
        
        if switch_ciclico.get():
            # Verificar si la válvula está en proceso puntual
            if self.estados_valvulas[idx]:
                switch_ciclico.deselect()
                messagebox.showwarning("Advertencia", 
                                    f"La válvula {self.valvulas[idx]} está en proceso puntual. Cierre el proceso puntual primero.")
                return
            
            # Deshabilitar switch puntual
            switch_puntual.configure(state="disabled")
            
            # Habilitar controles cíclicos (fondo blanco)
            apertura.configure(state="normal", fg_color="#ffffff")
            apertura_unidad.configure(state="normal")
            cierre.configure(state="normal", fg_color="#ffffff")
            cierre_unidad.configure(state="normal")
            ciclos_deseados.configure(state="normal", fg_color="#ffffff")
        else:
            # Habilitar switch puntual si no está en ejecución
            if not self.estados_valvulas[idx]:
                switch_puntual.configure(state="normal")
            
            # Deshabilitar controles cíclicos (fondo gris)
            apertura.configure(state="disabled", fg_color="#e0e0e0")
            apertura_unidad.configure(state="disabled")
            cierre.configure(state="disabled", fg_color="#e0e0e0")
            cierre_unidad.configure(state="disabled")
            ciclos_deseados.configure(state="disabled", fg_color="#e0e0e0")

    def toggle_controles_puntuales(self, idx):
        """Habilita/deshabilita controles según estado del switch"""
        switch_puntual, estado, tiempo, tiempo_unidad, tiempo_transcurrido, btn_invertir = self.controles_puntuales[idx]
        switch_ciclico, _, _, _, _, _, _ = self.controles_ciclicos[idx]
        
        if switch_puntual.get():
            # Verificar si la válvula está en proceso cíclico
            if switch_ciclico.get():
                switch_puntual.deselect()
                messagebox.showwarning("Advertencia", 
                                    f"La válvula {self.valvulas[idx]} está en proceso cíclico. Detenga el proceso cíclico primero.")
                return
            
            # Deshabilitar switch cíclico
            switch_ciclico.configure(state="disabled")
            
            # Habilitar controles puntuales (fondo blanco)
            tiempo.configure(state="normal", fg_color="#ffffff")
            tiempo_unidad.configure(state="normal")
            btn_invertir.configure(state="normal")
        else:
            # Habilitar switch cíclico si no está en ejecución
            if not switch_ciclico.get():
                switch_ciclico.configure(state="normal")
            
            # Deshabilitar controles puntuales (fondo gris)
            tiempo.configure(state="disabled", fg_color="#e0e0e0")
            tiempo_unidad.configure(state="disabled")
            btn_invertir.configure(state="disabled")

    def limpiar_notificaciones(self):
        """Limpia el área de notificaciones"""
        self.notificaciones_text.configure(state="normal")
        self.notificaciones_text.delete("1.0", "end")
        self.notificaciones_text.configure(state="disabled")

    def agregar_notificacion(self, mensaje):
        """Agrega un mensaje al área de notificaciones"""
        self.notificaciones_text.configure(state="normal")
        hora_actual = datetime.now().strftime("%H:%M:%S")
        self.notificaciones_text.insert("end", f"[{hora_actual}] {mensaje}\n")
        self.notificaciones_text.configure(state="disabled")
        self.notificaciones_text.see("end")

    def validar_entrada(self, text):
        if text == "":
            return True
        if text.isdigit():
            try:
                val = int(text)
                if val <= 9999:
                    return True
                else:
                    return False
            except:
                return False
        else:
            return False

    def validar_tiempo(self, entry, unidad_menu):
        try:
            valor = float(entry.get()) if entry.get() else 0
            unidad = unidad_menu.get()
            segundos = self.convertir_a_segundos(valor, unidad)

            if segundos > 9999:
                entry.configure(border_color="red")
                return False
            else:
                entry.configure(border_color="gray")
                return True
        except:
            entry.configure(border_color="red")
            return False

    def convertir_a_segundos(self, valor, unidad):
        try:
            valor = float(valor)
            if unidad == "min":
                return int(valor * 60)
            elif unidad == "h":
                return int(valor * 3600)
            else:
                return int(valor)
        except:
            return 0

    def format_tiempo(self, segundos):
        mins, secs = divmod(segundos, 60)
        return f"{mins:02d}:{secs:02d}"

    def guardar_proceso_db(self, datos_proceso):
        """Guarda los datos del proceso en la base de datos"""
        conn = None
        try:
            conn = sqlite3.connect("procesos.db")
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='procesos'")
            if not cursor.fetchone():
                # Crear tabla nueva con todas las columnas
                cursor.execute('''CREATE TABLE procesos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            proceso_id TEXT,
                            fecha_inicio TEXT,
                            fecha_fin TEXT,
                            hora_instruccion TEXT,
                            valvula_activada TEXT,
                            tiempo_valvula INTEGER,
                            ciclos INTEGER,
                            estado_valvula TEXT,
                            fase INTEGER DEFAULT 1,
                            tipo_proceso TEXT)''')
                print("Tabla 'procesos' creada con la nueva estructura")
            
            # Insertar datos
            cursor.execute('''INSERT INTO procesos 
                        (user_id, proceso_id, fecha_inicio, fecha_fin, hora_instruccion, 
                            valvula_activada, tiempo_valvula, ciclos, estado_valvula, fase, tipo_proceso)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (self.user_id,
                        datos_proceso.get('proceso_id', ''),
                        datos_proceso['fecha_inicio'],
                        datos_proceso.get('fecha_fin', ''),
                        datos_proceso['hora_instruccion'],
                        datos_proceso['valvula'],
                        datos_proceso['tiempo'],
                        datos_proceso.get('ciclos', 0),
                        datos_proceso['estado'],
                        datos_proceso.get('fase', 1),
                        datos_proceso.get('tipo_proceso', 'puntual')))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error de SQLite al guardar en DB: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado al guardar en DB: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def actualizar_proceso_db(self, idx, fecha_fin, ciclos_completados=None):
        """Actualiza un proceso existente en la base de datos"""
        conn = None
        try:
            conn = sqlite3.connect("procesos.db")
            cursor = conn.cursor()
            
            valvula = f"Válvula {self.valvulas[idx]}" 
            
            cursor.execute('''SELECT id FROM procesos 
                           WHERE valvula_activada = ? AND fecha_fin = '' 
                           ORDER BY id DESC LIMIT 1''',
                        (valvula,))
            resultado = cursor.fetchone()
            
            if resultado:
                id_proceso = resultado[0]
                
                if ciclos_completados is not None:
                    cursor.execute('''UPDATE procesos 
                                   SET fecha_fin = ?, ciclos = ?
                                   WHERE id = ?''',
                                (fecha_fin, ciclos_completados, id_proceso))
                else:
                    cursor.execute('''UPDATE procesos 
                                   SET fecha_fin = ?
                                   WHERE id = ?''',
                                (fecha_fin, id_proceso))
                
                conn.commit()
                return True
            return False
        except sqlite3.Error as e:
            print(f"Error de SQLite al actualizar proceso en DB: {e}")
            return False
        except Exception as e:
            print(f"Error inesperado al actualizar proceso en DB: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def deshabilitar_controles_puntuales(self, idx):
        switch, _, tiempo, tiempo_unidad, _, btn_invertir = self.controles_puntuales[idx]
        switch.configure(state="disabled")
        tiempo.configure(state="disabled")
        tiempo_unidad.configure(state="disabled")
        btn_invertir.configure(state="disabled")

    def habilitar_controles_puntuales(self, idx):
        switch, _, tiempo, tiempo_unidad, _, btn_invertir = self.controles_puntuales[idx]
        switch.configure(state="normal")
        if switch.get():
            tiempo.configure(state="normal")
            tiempo_unidad.configure(state="normal")
            btn_invertir.configure(state="normal")
        else:
            tiempo.configure(state="disabled")
            tiempo_unidad.configure(state="disabled")
            btn_invertir.configure(state="disabled")

    def deshabilitar_controles_ciclicos(self, idx):
        switch, apertura, apertura_unidad, cierre, cierre_unidad, ciclos_deseados, _ = self.controles_ciclicos[idx]
        switch.configure(state="disabled")
        apertura.configure(state="disabled")
        apertura_unidad.configure(state="disabled")
        cierre.configure(state="disabled")
        cierre_unidad.configure(state="disabled")
        ciclos_deseados.configure(state="disabled")

    def habilitar_controles_ciclicos(self, idx):
        switch, apertura, apertura_unidad, cierre, cierre_unidad, ciclos_deseados, _ = self.controles_ciclicos[idx]
        switch.configure(state="normal")
        if switch.get():
            apertura.configure(state="normal")
            apertura_unidad.configure(state="normal")
            cierre.configure(state="normal")
            cierre_unidad.configure(state="normal")
            ciclos_deseados.configure(state="normal")
        else:
            apertura.configure(state="disabled")
            apertura_unidad.configure(state="disabled")
            cierre.configure(state="disabled")
            cierre_unidad.configure(state="disabled")
            ciclos_deseados.configure(state="disabled")

    def iniciar_proceso_ciclico(self, proceso_id=None):
        """Inicia proceso cíclico usando el proceso_id diario"""
        try:
            if not self.master_panel.verificar_ejecucion("paneldecontrol"):
                return
                
            self.master_panel.activar_bloqueo_hardware("paneldecontrol")
            
            self.verificar_cambio_dia()  # Verificar si ha cambiado el día
            
            # Usar el proceso_id diario a menos que se especifique uno diferente
            proceso_id = self.proceso_id if proceso_id is None else proceso_id
                
            cadenas = []
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for i, (switch, apertura, apertura_unidad, cierre, cierre_unidad, ciclos_deseados, ciclos_actual) in enumerate(self.controles_ciclicos, start=1):
                if switch.get():
                    # Verificar si la válvula está en proceso puntual
                    if self.estados_valvulas[i-1]:
                        self.master_panel.liberar_bloqueo_hardware()
                        messagebox.showwarning("Advertencia", 
                                            f"La válvula {self.valvulas[i-1]} está en proceso puntual. Cierre el proceso puntual primero.")
                        return
                    
                    # Validar tiempos
                    apertura_val = self.convertir_a_segundos(apertura.get(), apertura_unidad.get())
                    cierre_val = self.convertir_a_segundos(cierre.get(), cierre_unidad.get())
                    
                    if apertura_val > 9999 or cierre_val > 9999:
                        self.master_panel.liberar_bloqueo_hardware()
                        messagebox.showerror("Error", f"Los tiempos para {self.valvulas[i-1]} no pueden exceder 9999 segundos (o equivalentes)")
                        return
                    
                    # Stop hilo previo
                    if self.hilos_ejecucion[i-1] and self.hilos_ejecucion[i-1].is_alive():
                        self.hilos_ejecucion[i-1].do_run = False
                    
                    # Deshabilitar controles puntuales
                    self.deshabilitar_controles_puntuales(i-1)
                    
                    # Cadena para ESP32
                    motor = f"M{i}"
                    ciclos_val = ciclos_deseados.get().zfill(4) if ciclos_deseados.get() else "0000"
                    
                    apertura_str = str(min(apertura_val, 9999)).zfill(4)
                    cierre_str = str(min(cierre_val, 9999)).zfill(4)

                    if int(ciclos_val) > 0:
                        tarea = "B"
                    else:
                        tarea = "E"

                    cadena = f"{motor}{tarea}N{ciclos_val}{apertura_str}{cierre_str}"
                    cadenas.append(cadena)
                    
                    # Guardar en DB
                    datos = {
                        'proceso_id': proceso_id,
                        'fecha_inicio': fecha_actual,
                        'fecha_fin': '',
                        'hora_instruccion': fecha_actual,
                        'valvula': f"Válvula {self.valvulas[i-1]}",
                        'tiempo': apertura_val,
                        'ciclos': ciclos_val,
                        'estado': 'A',
                        'fase': 1,
                        'tipo_proceso': 'cíclico'
                    }
                    self.guardar_proceso_db(datos)
                    
                    # Start hilo de ejecución
                    self.contadores_ciclos[i-1] = 0
                    ciclos_actual.configure(text="0")
                    
                    hilo = threading.Thread(target=self.ejecutar_ciclos, args=(i-1, apertura_val, cierre_val, int(ciclos_val) if ciclos_val.isdigit() else 0))
                    hilo.do_run = True
                    hilo.start()
                    self.hilos_ejecucion[i-1] = hilo
            
            if cadenas:
                cadena_final = "".join(cadenas)
                print(f"Cadena a enviar: {cadena_final}")
                
                # Enviar por serial usando el MasterPanel
                if self.master_panel.enviar_comando_serial(cadena_final):
                    print("Cadena enviada a ESP32...")
                    self.agregar_notificacion(f"Proceso cíclico iniciado")
                else:
                    messagebox.showerror("Error", "No se pudo enviar el comando a la ESP32")
            else:
                messagebox.showwarning("Advertencia", "No hay válvulas activadas para ejecutar")
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el proceso: {str(e)}")

    def ejecutar_ciclos(self, idx, tiempo_apertura, tiempo_cierre, ciclos_deseados):
        """Execute valve cycles with thread safety"""
        switch, _, _, _, _, _, ciclos_actual = self.controles_ciclicos[idx]
        
        ciclos = 0
        try:
            while not self.stop_event.is_set() and (ciclos_deseados == 0 or ciclos < ciclos_deseados):
                # Verificar paro de emergencia antes de cada fase
                if self.stop_event.is_set():
                    break
                    
                # Abrir fase
                inicio = time.time()
                while (time.time() - inicio < tiempo_apertura and 
                    not self.stop_event.is_set()):
                    time.sleep(0.1)
                
                if self.stop_event.is_set():
                    break
                    
                # Cerrar fase
                inicio = time.time()
                while (time.time() - inicio < tiempo_cierre and 
                    not self.stop_event.is_set()):
                    time.sleep(0.1)
                
                if self.stop_event.is_set():
                    break
                    
                ciclos += 1
                self.after(0, lambda: ciclos_actual.configure(text=str(ciclos)))
            
            # Finalizacion
            self.after(0, self.habilitar_controles_puntuales, idx)
            
            if not self.stop_event.is_set() and ciclos_deseados > 0 and ciclos >= ciclos_deseados:
                self.after(0, lambda: self.agregar_notificacion(
                    f"Válvula {self.valvulas[idx]} ha completado {ciclos_deseados} ciclos"
                ))
                
            # Actualizar proceso en DB
            if not self.stop_event.is_set():
                fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.after(0, self.actualizar_proceso_db, idx, fecha_fin, ciclos)
            else:
                # En caso de paro de emergencia, registrar como interrumpido
                fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.after(0, self.actualizar_proceso_db, idx, fecha_fin, ciclos)
                self.after(0, lambda: self.agregar_notificacion(
                    f"Válvula {self.valvulas[idx]} detenida por emergencia en ciclo {ciclos}"
                ))
                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(
                "Error", 
                f"Error en válvula {self.valvulas[idx]}: {str(e)}"
            ))

    def iniciar_proceso_puntual(self):
        """Inicia proceso puntual para todas las válvulas activadas"""
        try:
            self.verificar_cambio_dia()  # Verificar si ha cambiado el día
            proceso_id = self.proceso_id  # Siempre usar el proceso_id diario
            
            for i in range(9):
                switch, _, _, _, _, _ = self.controles_puntuales[i]
                if switch.get():
                    self.ejecutar_valvula_puntual(i, proceso_id)
            
            self.agregar_notificacion(f"Proceso puntual simultáneo iniciado")
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar el proceso puntual: {str(e)}")


    def iniciar_proceso_puntual(self):
        """Inicia proceso puntual para todas las válvulas activadas"""
        try:
            if not self.master_panel.verificar_ejecucion("paneldecontrol"):
                return
                
            self.master_panel.activar_bloqueo_hardware("paneldecontrol")
            self.verificar_cambio_dia()
            proceso_id = self.proceso_id
            
            cadenas = []
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for i, (switch, estado, tiempo, tiempo_unidad, tiempo_transcurrido, btn_invertir) in enumerate(self.controles_puntuales, start=1):
                if switch.get():
                    # Verificar si la válvula está en proceso cíclico
                    switch_ciclico, _, _, _, _, _, _ = self.controles_ciclicos[i-1]
                    if switch_ciclico.get():
                        self.master_panel.liberar_bloqueo_hardware()
                        messagebox.showwarning("Advertencia", 
                                            f"La válvula {self.valvulas[i-1]} está en proceso cíclico. Detenga el proceso cíclico primero.")
                        return
                    
                    # Validar tiempo
                    segundos = self.convertir_a_segundos(tiempo.get(), tiempo_unidad.get())
                    if segundos > 9999:
                        self.master_panel.liberar_bloqueo_hardware()
                        messagebox.showerror("Error", f"El tiempo para {self.valvulas[i-1]} no puede exceder 9999 segundos")
                        return
                    
                    # Deshabilitar controles cíclicos
                    self.deshabilitar_controles_ciclicos(i-1)
                    
                    # Construir cadena para microcontrolador
                    motor = f"M{i}"
                    direccion = self.direcciones_valvulas[i-1]
                    
                    if segundos == 0:
                        tarea = "A"  # Apertura simple sin tiempo
                    else:
                        tarea = "C"  # Apertura con tiempo
                    
                    ciclos_val = "0000"
                    apertura_str = str(min(segundos, 9999)).zfill(4)
                    cierre_str = "0000"
                    
                    cadena = f"{motor}{tarea}{direccion}{ciclos_val}{apertura_str}{cierre_str}"
                    cadenas.append(cadena)
                    
                    # Guardar en DB
                    datos = {
                        'proceso_id': proceso_id,
                        'fecha_inicio': fecha_actual,
                        'fecha_fin': '',
                        'hora_instruccion': fecha_actual,
                        'valvula': f"Válvula {self.valvulas[i-1]}",
                        'tiempo': segundos,
                        'ciclos': 0,
                        'estado': 'A',
                        'fase': 1,
                        'tipo_proceso': 'puntual'
                    }
                    if not self.guardar_proceso_db(datos):
                        self.master_panel.liberar_bloqueo_hardware()
                        messagebox.showerror("Error", "No se pudo guardar el proceso en la base de datos")
                        return
                    
                    # Actualizar estado visual
                    self.estados_valvulas[i-1] = True
                    self.tiempos_inicio[i-1] = time.time()
                    estado.configure(text="ABIERTO", fg_color="green")
                    
                    # Iniciar temporizador solo si hay tiempo definido
                    if tarea == "C":
                        self.actualizar_tiempo_transcurrido(i-1, segundos)
                    else:
                        tiempo_transcurrido.configure(text="--:--")
            
            if cadenas:
                cadena_final = "".join(cadenas)
                print(f"Cadena a enviar: {cadena_final}")
                
                # Enviar por serial usando el MasterPanel
                if self.master_panel.enviar_comando_serial(cadena_final):
                    self.agregar_notificacion("Proceso puntual iniciado")
                else:
                    messagebox.showerror("Error", "No se pudo enviar el comando al microcontrolador")
            else:
                messagebox.showwarning("Advertencia", "No hay válvulas activadas para ejecutar")
                self.master_panel.liberar_bloqueo_hardware()
                
        except Exception as e:
            self.master_panel.liberar_bloqueo_hardware()
            messagebox.showerror("Error", f"No se pudo iniciar el proceso: {str(e)}")


    def actualizar_tiempo_transcurrido(self, idx, duracion_total):
        switch, estado, _, _, tiempo_transcurrido, _ = self.controles_puntuales[idx]
        
        if not self.estados_valvulas[idx]:
            return
            
        tiempo_transcurrido_seg = int(time.time() - self.tiempos_inicio[idx])
        tiempo_restante = max(0, duracion_total - tiempo_transcurrido_seg)
        
        tiempo_transcurrido.configure(text=self.format_tiempo(tiempo_transcurrido_seg))
        
        if tiempo_restante > 0:
            self.after(1000, lambda: self.actualizar_tiempo_transcurrido(idx, duracion_total))
        else:
            self.estados_valvulas[idx] = False
            estado.configure(text="CERRADO", fg_color="red")
            tiempo_transcurrido.configure(text="00:00")
            
            # Habilitar controles cíclicos
            self.habilitar_controles_ciclicos(idx)
            
            # Notificación de finalización
            self.agregar_notificacion(f"Válvula {self.valvulas[idx]} ha completado su tiempo de apertura")
            
            # Actualizar fecha de finalización en DB
            fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.actualizar_proceso_db(idx, fecha_fin)

    def invertir_sentido(self, idx):
        _, estado, _, _, _, btn_invertir = self.controles_puntuales[idx]
        
        # Alternar la dirección
        direccion_actual = self.direcciones_valvulas[idx]
        nueva_direccion = "I" if direccion_actual == "D" else "D"
        self.direcciones_valvulas[idx] = nueva_direccion
        
        # Cambiar texto del botón
        nuevo_texto = "Abrir" if nueva_direccion == "D" else "Cerrar"
        btn_invertir.configure(text=nuevo_texto)
        
        # Notificación
        self.agregar_notificacion(
            f"Sentido de la válvula {self.valvulas[idx]} cambiado a {'Izquierda' if nueva_direccion == 'I' else 'Derecha'}"
        )
        
        # Si la válvula está abierta, cerrarla primero
        if self.estados_valvulas[idx]:
            self.estados_valvulas[idx] = False
            estado.configure(text="CERRADO", fg_color="red")
            
            # Guardar cierre en DB
            fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.actualizar_proceso_db(idx, fecha_fin)
        
        # Ejecutar con nueva dirección si el switch está activado
        switch_puntual, _, _, _, _, _ = self.controles_puntuales[idx]
        if switch_puntual.get():
            self.ejecutar_valvula_puntual(idx)

    def __del__(self):
        """Libera recursos al destruir el panel"""
        try:
            self.stop_event.set()
            
            # Stop all threads
            for i in range(9):
                if (hasattr(self, 'hilos_ejecucion') and 
                    self.hilos_ejecucion[i] and 
                    self.hilos_ejecucion[i].is_alive()):
                    self.hilos_ejecucion[i].join(timeout=1)
            
            # Release hardware lock
            if hasattr(self, 'master_panel'):
                self.master_panel.liberar_bloqueo_hardware()
        except Exception as e:
            print(f"Error en limpieza de PaneldeControl: {e}")