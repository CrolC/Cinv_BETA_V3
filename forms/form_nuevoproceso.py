import customtkinter as ctk
import sqlite3
import sys
import traceback
import threading
import time
from tkinter import messagebox
import datetime
import uuid

#PENDIENTES: ##Agregar rutina de tiempo indefinido ##Aumentar a 5 cifras en seg y a 1000 fases ##Agregar sonidos en eventos importantes

COLOR_CUERPO_PRINCIPAL = "#f4f8f7"

class FormNuevoProceso(ctk.CTkFrame):
    def __init__(self, panel_principal, user_id):
        super().__init__(panel_principal, fg_color=COLOR_CUERPO_PRINCIPAL)
        self.user_id = user_id
        self.master_panel = panel_principal.master
        
        # Process control variables
        self.proceso_en_ejecucion = False
        self.proceso_pausado = False
        self.fase_actual = 0
        self.tiempo_inicio_fase = 0
        self.tiempo_pausa = 0
        self.hilo_proceso = None
        self.fase_contador = 1
        self.fases_datos = {}
        self.valvulas_activas = {}
        self.notificaciones = []
        self.elementos = ["Al", "As", "Ga", "In", "N", "Mn", "Be", "Mg", "Si"]
        self.stop_event = threading.Event()
        
        # Input validation
        self.validar_cmd = self.register(self.validar_entrada)
        self.construir_interfaz()

    def construir_interfaz(self):
        """Construye todos los elementos de la interfaz"""
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color=COLOR_CUERPO_PRINCIPAL)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame superior para contenido principal
        self.top_frame = ctk.CTkFrame(self.main_frame)
        self.top_frame.pack(fill="both", expand=True)
        
        # Frame para configuración de repetición
        self.repeticion_frame = ctk.CTkFrame(self.top_frame)
        self.repeticion_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(self.repeticion_frame, text="Repetir configuración:").pack(side="left", padx=5)
        
        self.repeticiones_spinbox = ctk.CTkEntry(self.repeticion_frame, width=50, validate="key", 
                                            validatecommand=(self.validar_cmd, "%P"))
        self.repeticiones_spinbox.pack(side="left", padx=5)
        self.repeticiones_spinbox.insert(0, "1")  # Valor por defecto
        
        ctk.CTkLabel(self.repeticion_frame, text="veces").pack(side="left", padx=5)
        
        # Scrollable frame para las fases
        self.scrollable_frame = ctk.CTkFrame(self.top_frame)
        self.scrollable_frame.pack(fill="both", expand=True)

        self.tabview = ctk.CTkTabview(self.scrollable_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame para botones generales (altura fija)
        self.botones_generales_frame = ctk.CTkFrame(self.top_frame, height=50)
        self.botones_generales_frame.pack(fill="x", padx=10, pady=(5, 5))

        # Botones generales
        self.reiniciar_btn = ctk.CTkButton(
            self.botones_generales_frame, 
            text="⮌ Reiniciar Rutina", 
            fg_color="#D9534F", 
            command=self.reiniciar_rutina
        )
        self.reiniciar_btn.pack(side="right", padx=5)

        self.pausar_btn = ctk.CTkButton(
            self.botones_generales_frame, 
            text="⏸ Pausar Rutina", 
            fg_color="#F0AD4E",
            command=self.pausar_proceso,
            state="disabled"
        )
        self.pausar_btn.pack(side="right", padx=5)

        self.ejecutar_btn = ctk.CTkButton(
            self.botones_generales_frame, 
            text="▶ Ejecutar Rutina", 
            fg_color="#06918A", 
            command=self.iniciar_proceso
        )
        self.ejecutar_btn.pack(side="right", padx=5)

        # Frame para Control Manual de Válvulas
        self.frame_manual = ctk.CTkFrame(self.top_frame, height=100)
        self.frame_manual.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            self.frame_manual, 
            text="CONTROL MANUAL DE VÁLVULAS",
            font=("Arial", 14, "bold")
        ).pack(pady=(5, 0))

        # Frame para selección de fase y válvula
        self.control_frame = ctk.CTkFrame(self.frame_manual, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=5, pady=5)

        # Selección de fase
        ctk.CTkLabel(self.control_frame, text="Fase:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.fase_manual = ctk.CTkOptionMenu(self.control_frame, values=["1"])
        self.fase_manual.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Selección de válvula
        ctk.CTkLabel(self.control_frame, text="Válvula:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.valvula_manual = ctk.CTkOptionMenu(self.control_frame, values=self.elementos)
        self.valvula_manual.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Botones de control
        self.btn_abrir_manual = ctk.CTkButton(
            self.control_frame, 
            text="Abrir Válvula", 
            fg_color="#28a745",
            command=lambda: self.control_manual_valvula("abrir")
        )
        self.btn_abrir_manual.grid(row=0, column=4, padx=5, pady=5)

        self.btn_cerrar_manual = ctk.CTkButton(
            self.control_frame, 
            text="Cerrar Válvula", 
            fg_color="#dc3545",
            command=lambda: self.control_manual_valvula("cerrar")
        )
        self.btn_cerrar_manual.grid(row=0, column=5, padx=5, pady=5)

        # Frame para rango de fases
        self.rango_frame = ctk.CTkFrame(self.frame_manual, fg_color="transparent")
        self.rango_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(self.rango_frame, text="Abrir desde fase:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.fase_inicio = ctk.CTkEntry(self.rango_frame, width=50, validate="key", validatecommand=(self.validar_cmd, "%P"))
        self.fase_inicio.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(self.rango_frame, text="hasta fase:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.fase_fin = ctk.CTkEntry(self.rango_frame, width=50, validate="key", validatecommand=(self.validar_cmd, "%P"))
        self.fase_fin.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.btn_programar_rango = ctk.CTkButton(
            self.rango_frame, 
            text="Programar Rango", 
            fg_color="#007bff",
            command=self.programar_rango_fases
        )
        self.btn_programar_rango.grid(row=0, column=4, padx=5, pady=5)

        # Frame para notificaciones (altura fija)
        self.notificaciones_frame = ctk.CTkFrame(self.top_frame, height=150)
        self.notificaciones_frame.pack(fill="x", padx=10, pady=(0, 10))

        # Encabezado centrado
        header_frame = ctk.CTkFrame(self.notificaciones_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(5, 0))

        ctk.CTkLabel(
            header_frame, 
            text="NOTIFICACIONES", 
            font=("Arial", 16, "bold")
        ).pack(expand=True)

        self.notificaciones_text = ctk.CTkTextbox(self.notificaciones_frame, height=100, state="disabled")
        self.notificaciones_text.pack(fill="x", padx=5, pady=5)

        self.limpiar_btn = ctk.CTkButton(
            self.notificaciones_frame,
            text="LIMPIAR",
            fg_color="#6c757d",
            command=self.limpiar_notificaciones,
            width=100
        )
        self.limpiar_btn.pack(side="right", padx=5, pady=(0, 5))

        # Botón de paro de emergencia
        btn_paro = ctk.CTkButton(self.notificaciones_frame, 
                                text="STOP EMERGENCIA", 
                                fg_color="red", 
                                hover_color="darkred",
                                command=self.paro_emergencia)
        btn_paro.pack(side="right", padx=5, pady=(0,5))
        
        # AHORA agregamos la fase inicial después de que todos los controles estén creados
        self.agregar_fase("Fase 1")
        
        # Inicializar lista de fases
        self.actualizar_lista_fases()
        
        self.pack(padx=10, pady=10, fill="both", expand=True)

    def actualizar_lista_fases(self):
        """Actualiza la lista de fases disponibles en el control manual"""
        fases = list(self.fases_datos.keys())
        numeros_fases = [f.split()[-1] for f in fases]
        self.fase_manual.configure(values=numeros_fases)
        if numeros_fases:
            self.fase_manual.set(numeros_fases[0])

    def control_manual_valvula(self, accion):
        """Control manual de apertura/cierre de válvulas"""
        try:
            if not self.master_panel.verificar_ejecucion("nuevoproceso"):
                return
                
            fase_seleccionada = self.fase_manual.get()
            valvula_seleccionada = self.valvula_manual.get()
            
            if not fase_seleccionada or not valvula_seleccionada:
                messagebox.showwarning("Advertencia", "Seleccione una fase y una válvula")
                return
                
            # Encontrar el índice de la válvula
            idx_valvula = self.elementos.index(valvula_seleccionada)
            
            # Construir comando para ESP32
            motor = f"M{idx_valvula + 1}"
            
            if accion == "abrir":
                comando = f"{motor}A{'D'}N000000000000"  # Abrir válvula
                estado = "A"
                mensaje = f"Válvula {valvula_seleccionada} abierta manualmente en fase {fase_seleccionada}"
            else:
                comando = f"{motor}E{'D'}N000000000000"  # Cerrar válvula
                estado = "C"
                mensaje = f"Válvula {valvula_seleccionada} cerrada manualmente en fase {fase_seleccionada}"
            
            # Enviar comando
            if self.master_panel.enviar_comando_serial(comando):
                # Registrar en base de datos
                fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                datos = {
                    'proceso_id': self.proceso_id if hasattr(self, 'proceso_id') else "manual",
                    'fecha_inicio': fecha_actual,
                    'fecha_fin': fecha_actual if accion == "cerrar" else '',
                    'hora_instruccion': fecha_actual,
                    'valvula': f"Válvula {valvula_seleccionada}",
                    'tiempo': 0,
                    'ciclos': 0,
                    'estado': estado,
                    'fase': int(fase_seleccionada),
                    'tipo_proceso': 'manual'
                }
                self.guardar_proceso_db(datos)
                
                self.agregar_notificacion(mensaje)
            else:
                messagebox.showerror("Error", "No se pudo enviar el comando a la ESP32")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error en control manual: {str(e)}")

    def programar_rango_fases(self):
        """Programa la apertura de una válvula en un rango de fases"""
        try:
            fase_inicio = self.fase_inicio.get()
            fase_fin = self.fase_fin.get()
            valvula_seleccionada = self.valvula_manual.get()
            
            if not all([fase_inicio, fase_fin, valvula_seleccionada]):
                messagebox.showwarning("Advertencia", "Complete todos los campos del rango de fases")
                return
                
            fase_inicio = int(fase_inicio)
            fase_fin = int(fase_fin)
            
            if fase_inicio > fase_fin:
                messagebox.showwarning("Advertencia", "La fase inicial no puede ser mayor que la fase final")
                return
                
            # Encontrar el índice de la válvula
            idx_valvula = self.elementos.index(valvula_seleccionada)
            
            # Construir comando para ESP32 con rango de fases
            motor = f"M{idx_valvula + 1}"
            comando = f"{motor}RD{str(fase_inicio).zfill(2)}{str(fase_fin).zfill(2)}00000000"
            
            # Enviar comando
            if self.master_panel.enviar_comando_serial(comando):
                # Registrar en base de datos
                fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                datos = {
                    'proceso_id': self.proceso_id if hasattr(self, 'proceso_id') else "rango_manual",
                    'fecha_inicio': fecha_actual,
                    'fecha_fin': '',
                    'hora_instruccion': fecha_actual,
                    'valvula': f"Válvula {valvula_seleccionada} (Fases {fase_inicio}-{fase_fin})",
                    'tiempo': 0,
                    'ciclos': 0,
                    'estado': 'A',
                    'fase': fase_inicio,
                    'tipo_proceso': 'rango_manual'
                }
                self.guardar_proceso_db(datos)
                
                mensaje = f"Válvula {valvula_seleccionada} programada para abrir desde fase {fase_inicio} hasta fase {fase_fin}"
                self.agregar_notificacion(mensaje)
            else:
                messagebox.showerror("Error", "No se pudo enviar el comando a la ESP32")
                
        except ValueError:
            messagebox.showwarning("Advertencia", "Ingrese números válidos para las fases")
        except Exception as e:
            messagebox.showerror("Error", f"Error al programar rango: {str(e)}")

    def agregar_notificacion(self, mensaje):
        """Agrega una notificación al panel de notificaciones"""
        self.notificaciones.append(mensaje)
        self.notificaciones_text.configure(state="normal")
        self.notificaciones_text.insert("end", f"- {mensaje}\n")
        self.notificaciones_text.configure(state="disabled")
        self.notificaciones_text.see("end")

    def limpiar_notificaciones(self):
        """Limpia todas las notificaciones"""
        self.notificaciones = []
        self.notificaciones_text.configure(state="normal")
        self.notificaciones_text.delete("1.0", "end")
        self.notificaciones_text.configure(state="disabled")

    def toggle_campos_valvula(self, switch, campos):
        """Habilita/deshabilita campos según estado del switch"""
        estado = switch.get()
        for campo in campos:
            if campo is not None:
                if isinstance(campo, ctk.CTkEntry):  # Solo para campos de entrada de texto
                    if estado:
                        # Habilitado - fondo blanco
                        campo.configure(state="normal", fg_color="#ffffff")
                    else:
                        # Deshabilitado - fondo gris
                        campo.configure(state="disabled", fg_color="#e0e0e0")
                elif hasattr(campo, 'configure'):
                    # Otros controles CTk (switches, option menus) se mantienen igual
                    campo.configure(state="normal" if estado else "disabled")

    def validar_entrada(self, text):
        """Validación de entrada numérica"""
        if text == "":
            return True
        if text.isdigit():
            try:
                val = int(text)
                return val <= 9999
            except:
                return False
        return False

    def validar_tiempo(self, entry, unidad_menu):
        """Validación de tiempo de apertura/cierre"""
        try:
            valor = float(entry.get()) if entry.get() else 0
            unidad = unidad_menu.get()
            segundos = self.convertir_a_segundos(valor, unidad)

            if segundos > 9999:
                entry.configure(border_color="red")
            else:
                entry.configure(border_color="gray")
        except:
            entry.configure(border_color="red")

    def seleccionar_direccion(self, dir_var, btn_izq, btn_der, seleccion):
        """Control de selección de dirección"""
        dir_var.set(seleccion)
        btn_izq.configure(fg_color="#06918A" if seleccion == "I" else "#D3D3D3")
        btn_der.configure(fg_color="#06918A" if seleccion == "D" else "#D3D3D3")

    def convertir_a_segundos(self, valor, unidad):
        """Conversión de unidades de tiempo a segundos"""
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

    def agregar_fase(self, nombre_fase=None):
        """Agrega una nueva fase al tabview"""
        if nombre_fase is None:
            self.fase_contador += 1
            nombre_fase = f"Fase {self.fase_contador}"

        self.tabview.add(nombre_fase)

        frame_fase = ctk.CTkFrame(self.tabview.tab(nombre_fase))
        frame_fase.pack(fill="both", expand=True, padx=10, pady=10)

        self.fases_datos[nombre_fase] = []

        # Encabezados
        header = ctk.CTkFrame(frame_fase)
        header.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(header, text="Válvula", width=80).pack(side="left", padx=5)
        ctk.CTkLabel(header, text="Apertura", width=80).pack(side="left", padx=(20,5))
        ctk.CTkLabel(header, text="Cierre", width=80).pack(side="left", padx=(30,5))
        ctk.CTkLabel(header, text="Ciclos", width=60).pack(side="left", padx=(40,5))
        ctk.CTkLabel(header, text="Progreso", width=100).pack(side="left", padx=(15,5))

        for i, elemento in enumerate(self.elementos):
            fila = ctk.CTkFrame(frame_fase)
            fila.pack(fill="x", padx=5, pady=5)

            # Switch para activar/desactivar válvula
            switch = ctk.CTkSwitch(fila, text=elemento)
            switch.pack(side="left", padx=5)

            # Config de apertura
            apertura_frame = ctk.CTkFrame(fila)
            apertura_frame.pack(side="left", padx=5)
            apertura = ctk.CTkEntry(apertura_frame, width=50, validate="key", 
                                 validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            apertura.pack(side="left")
            apertura_unidad = ctk.CTkOptionMenu(apertura_frame, values=["s", "min", "h"], width=50, state="disabled")
            apertura_unidad.set("s")
            apertura_unidad.pack(side="left", padx=5)
            apertura.bind("<KeyRelease>", lambda e, ent=apertura, unidad=apertura_unidad: 
                        self.validar_tiempo(ent, unidad))
            apertura_unidad.configure(command=lambda v, ent=apertura, unidad=apertura_unidad: 
                                    self.validar_tiempo(ent, unidad))

            # Config de cierre
            cierre_frame = ctk.CTkFrame(fila)
            cierre_frame.pack(side="left", padx=5)
            cierre = ctk.CTkEntry(cierre_frame, width=50, validate="key", 
                                validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            cierre.pack(side="left")
            cierre_unidad = ctk.CTkOptionMenu(cierre_frame, values=["s", "min", "h"], width=50, state="disabled")
            cierre_unidad.set("s")
            cierre_unidad.pack(side="left", padx=5)
            cierre.bind("<KeyRelease>", lambda e, ent=cierre, unidad=cierre_unidad: 
                    self.validar_tiempo(ent, unidad))
            cierre_unidad.configure(command=lambda v, ent=cierre, unidad=cierre_unidad: 
                                self.validar_tiempo(ent, unidad))

            # Config de ciclos
            ciclos = ctk.CTkEntry(fila, width=60, validate="key", 
                                validatecommand=(self.validar_cmd, "%P"), state="disabled", fg_color="#e0e0e0")
            ciclos.pack(side="left", padx=5)

            # Progreso
            progreso = ctk.CTkLabel(fila, text="0/0", width=100)
            progreso.pack(side="left", padx=5)

            # Lista de campos a habilitar/deshabilitar
            campos_valvula = [
                apertura, apertura_unidad, 
                cierre, cierre_unidad, 
                ciclos
            ]
            
            # Configurar comando para toggle de campos
            switch.configure(command=lambda s=switch, c=campos_valvula: self.toggle_campos_valvula(s, c))
            
            self.fases_datos[nombre_fase].append({
                'switch': switch,
                'apertura': apertura,
                'apertura_unidad': apertura_unidad,
                'cierre': cierre,
                'cierre_unidad': cierre_unidad,
                'ciclos': ciclos,
                'progreso': progreso,
                'ciclos_completados': 0,
                'tiempo_transcurrido': 0,
                'elemento': elemento  # Guardamos el nombre del elemento
            })

        # Botones para agregar/eliminar fases
        botones_frame = ctk.CTkFrame(self.tabview.tab(nombre_fase))
        botones_frame.pack(side="bottom", pady=10)
        ctk.CTkButton(botones_frame, text="Agregar Fase", fg_color="#06918A",
                    command=self.agregar_fase).pack(side="right", padx=5)
        ctk.CTkButton(botones_frame, text="Eliminar Fase", fg_color="#D9534F",
                    command=lambda: self.eliminar_fase(nombre_fase)).pack(side="right", padx=5)

        self.tabview.set(nombre_fase)
        
        # Actualizar lista de fases en control manual
        self.actualizar_lista_fases()

    def eliminar_fase(self, nombre_fase):
        """Elimina una fase si no es la última"""
        if len(self.tabview._name_list) > 1:
            self.tabview.delete(nombre_fase)
            del self.fases_datos[nombre_fase]
            self.agregar_notificacion(f"Fase {nombre_fase} eliminada")
            
            # Actualizar lista de fases en control manual
            self.actualizar_lista_fases()
        else:
            messagebox.showwarning("Advertencia", "No puedes eliminar la última fase")
            self.agregar_notificacion("Intento de eliminar la última fase (no permitido)")

    def iniciar_proceso(self):
        """Inicia el proceso de ejecución de rutina"""
        try:
            if not self.proceso_en_ejecucion:
                # Confirmar bloqueo con el MasterPanel
                if not self.master_panel.verificar_ejecucion("nuevoproceso"):
                    return
                self.master_panel.activar_bloqueo_hardware("nuevoproceso")
                
                # Generar ID de proceso consistente (fecha + hora)
                self.proceso_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Obtener número de repeticiones
                try:
                    repeticiones = int(self.repeticiones_spinbox.get())
                    if repeticiones < 1 or repeticiones > 100:
                        raise ValueError("Número de repeticiones inválido")
                except:
                    messagebox.showwarning("Advertencia", "Número de repeticiones inválido. Usando valor por defecto (1)")
                    repeticiones = 1
                    self.repeticiones_spinbox.delete(0, "end")
                    self.repeticiones_spinbox.insert(0, "1")
                
                # Guardar información inicial en DB
                datos_iniciales = {
                    'proceso_id': self.proceso_id,
                    'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'fecha_fin': '',
                    'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'valvula': f"Inicio de proceso complejo (Repeticiones: {repeticiones})",
                    'tiempo': 0,
                    'ciclos': 0,
                    'estado': 'A',  # Abierto/Activo
                    'fase': 0,
                    'tipo_proceso': 'complejo'
                }
                if not self.guardar_proceso_db(datos_iniciales):
                    messagebox.showerror("Error", "No se pudo guardar el registro inicial en la base de datos")
                    return
                
                # Preparar datos de válvulas activas
                self.valvulas_activas = {}
                valvulas_configuradas = False
                
                # Procesar todas las fases para cada repetición
                for repeticion in range(repeticiones):
                    for fase_idx, (nombre_fase, valvulas) in enumerate(self.fases_datos.items()):
                        for valvula_idx, valvula in enumerate(valvulas):
                            if valvula['switch'].get():
                                try:
                                    tiempo = self.convertir_a_segundos(valvula['apertura'].get(), valvula['apertura_unidad'].get())
                                    ciclos = int(valvula['ciclos'].get()) if valvula['ciclos'].get() else 0
                                    
                                    if tiempo > 0:
                                        valvulas_configuradas = True
                                        # Guardar cada válvula activa en la DB
                                        datos_valvula = {
                                            'proceso_id': self.proceso_id,
                                            'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'valvula': f"Válvula {valvula['elemento']}",
                                            'tiempo': tiempo,
                                            'ciclos': ciclos,
                                            'estado': 'A',
                                            'fase': fase_idx + 1 + (repeticion * len(self.fases_datos)),
                                            'tipo_proceso': 'cíclico' if ciclos > 0 else 'puntual'
                                        }
                                        self.guardar_proceso_db(datos_valvula)
                                        
                                        key = f"R{repeticion}F{fase_idx+1}V{valvula_idx+1}"
                                        self.valvulas_activas[key] = {
                                            'fase': fase_idx + (repeticion * len(self.fases_datos)),
                                            'valvula_idx': valvula_idx,
                                            'ciclos_totales': ciclos,
                                            'tiempo_ciclo': tiempo,
                                            'ciclos_completados': 0,
                                            'tiempo_transcurrido': 0,
                                            'progreso': valvula['progreso'],
                                            'elemento': valvula['elemento']
                                        }
                                        
                                        if ciclos > 0:
                                            valvula['progreso'].configure(text=f"0/{ciclos}")
                                            self.agregar_notificacion(f"Válvula {valvula['elemento']} en {nombre_fase} (Rep {repeticion+1}): {ciclos} ciclos configurados")
                                        else:
                                            valvula['progreso'].configure(text=f"T: {tiempo}s")
                                            self.agregar_notificacion(f"Válvula {valvula['elemento']} en {nombre_fase} (Rep {repeticion+1}): Tiempo {tiempo}s configurado")
                                except Exception as e:
                                    print(f"Error al procesar válvula: {e}")
                                    pass
                
                if not valvulas_configuradas:
                    mensaje = "Debe configurar al menos una válvula con tiempo de apertura válido"
                    messagebox.showwarning("Advertencia", mensaje)
                    self.agregar_notificacion(mensaje)
                    self.master_panel.liberar_bloqueo_hardware()
                    return
                
                if not self.enviar_cadena_serial(repeticiones):
                    self.master_panel.liberar_bloqueo_hardware()
                    return
                
                self.proceso_en_ejecucion = True
                self.proceso_pausado = False
                self.fase_actual = 0
                self.pausar_btn.configure(state="normal", text="Pausar Rutina")
                self.ejecutar_btn.configure(state="disabled")
                
                self.hilo_proceso = threading.Thread(target=self.ejecutar_proceso, daemon=True)
                self.hilo_proceso.start()
                
                mensaje = f"Proceso iniciado correctamente (Repeticiones: {repeticiones})"
                messagebox.showinfo("Éxito", mensaje)
                self.agregar_notificacion(mensaje)
        except Exception as e:
            self.master_panel.liberar_bloqueo_hardware()
            messagebox.showerror("Error", f"Error al iniciar proceso: {str(e)}")
            self.agregar_notificacion(f"Error al iniciar proceso: {str(e)}")

    def ejecutar_proceso(self):
        """Ejecuta el proceso fase por fase y registra todo en la base de datos"""
        try:
            self.agregar_notificacion("Iniciando ejecución de rutina...")
            
            # Obtener número de repeticiones
            try:
                repeticiones = int(self.repeticiones_spinbox.get())
                if repeticiones < 1 or repeticiones > 100:
                    repeticiones = 1
            except:
                repeticiones = 1
            
            # Iterar por cada repetición
            for repeticion in range(repeticiones):
                if not self.proceso_en_ejecucion:
                    break
                    
                # Iterar por cada fase
                for fase_idx, (nombre_fase, valvulas) in enumerate(self.fases_datos.items()):
                    if not self.proceso_en_ejecucion:
                        break
                        
                    fase_global_idx = fase_idx + (repeticion * len(self.fases_datos))
                    self.fase_actual = fase_global_idx
                    self.tiempo_inicio_fase = time.time()
                    fase_completada = False
                    
                    self.agregar_notificacion(f"Ejecutando {nombre_fase} (Repetición {repeticion+1}/{repeticiones})...")
                    self.tabview.set(nombre_fase)  # Mostrar la fase actual
                    
                    # Registrar inicio de fase en la base de datos
                    datos_fase = {
                        'proceso_id': self.proceso_id,
                        'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'fecha_fin': '',
                        'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'valvula': f"Inicio fase {fase_idx+1} (Rep {repeticion+1})",
                        'tiempo': 0,
                        'ciclos': 0,
                        'estado': 'A',
                        'fase': fase_global_idx + 1,
                        'tipo_proceso': 'complejo'
                    }
                    self.guardar_proceso_db(datos_fase)
                    
                    # Ejecutar válvulas activas en esta fase
                    while not fase_completada and self.proceso_en_ejecucion:
                        # Manejar pausa
                        while self.proceso_pausado and self.proceso_en_ejecucion:
                            if self.tiempo_pausa == 0:
                                self.tiempo_pausa = time.time()
                                datos_pausa = {
                                    'proceso_id': self.proceso_id,
                                    'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'fecha_fin': '',
                                    'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'valvula': "Pausa",
                                    'tiempo': 0,
                                    'ciclos': 0,
                                    'estado': 'P',
                                    'fase': fase_global_idx + 1,
                                    'tipo_proceso': 'complejo'
                                }
                                self.guardar_proceso_db(datos_pausa)
                            time.sleep(0.1)
                        
                        if not self.proceso_en_ejecucion:
                            break
                            
                        if self.tiempo_pausa > 0:
                            self.tiempo_inicio_fase += time.time() - self.tiempo_pausa
                            self.tiempo_pausa = 0
                            datos_reanudar = {
                                'proceso_id': self.proceso_id,
                                'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'fecha_fin': '',
                                'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'valvula': "Reanudar",
                                'tiempo': 0,
                                'ciclos': 0,
                                'estado': 'R',
                                'fase': fase_global_idx + 1,
                                'tipo_proceso': 'complejo'
                            }
                            self.guardar_proceso_db(datos_reanudar)
                        
                        tiempo_transcurrido_fase = time.time() - self.tiempo_inicio_fase
                        fase_completada = True
                        
                        for valvula_idx, valvula in enumerate(valvulas):
                            key = f"R{repeticion}F{fase_idx+1}V{valvula_idx+1}"
                            if key in self.valvulas_activas:
                                config = self.valvulas_activas[key]
                                
                                if config['ciclos_totales'] > 0:
                                    ciclos_completos = min(
                                        int(tiempo_transcurrido_fase / config['tiempo_ciclo']),
                                        config['ciclos_totales']
                                    )
                                    
                                    if ciclos_completos > config['ciclos_completados']:
                                        config['ciclos_completados'] = ciclos_completos
                                        valvula['progreso'].configure(text=f"{ciclos_completos}/{config['ciclos_totales']}")
                                        self.agregar_notificacion(f"Válvula {config['elemento']}: Ciclo {ciclos_completos}/{config['ciclos_totales']}")
                                        
                                        datos_ciclo = {
                                            'proceso_id': self.proceso_id,
                                            'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'fecha_fin': '',
                                            'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'valvula': config['elemento'],
                                            'tiempo': config['tiempo_ciclo'],
                                            'ciclos': ciclos_completos,
                                            'estado': 'A',
                                            'fase': fase_global_idx + 1,
                                            'tipo_proceso': 'cíclico'
                                        }
                                        self.guardar_proceso_db(datos_ciclo)
                                    
                                    if config['ciclos_completados'] < config['ciclos_totales']:
                                        fase_completada = False
                                else:
                                    if tiempo_transcurrido_fase < config['tiempo_ciclo']:
                                        tiempo_restante = max(0, config['tiempo_ciclo'] - tiempo_transcurrido_fase)
                                        valvula['progreso'].configure(text=f"T: {int(tiempo_restante)}s")
                                        fase_completada = False
                                    else:
                                        valvula['progreso'].configure(text="Completado")
                                        self.agregar_notificacion(f"Válvula {config['elemento']}: Tiempo completado")
                                        
                                        datos_fin_valvula = {
                                            'proceso_id': self.proceso_id,
                                            'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'fecha_fin': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'valvula': config['elemento'],
                                            'tiempo': config['tiempo_ciclo'],
                                            'ciclos': 0,
                                            'estado': 'C',
                                            'fase': fase_global_idx + 1,
                                            'tipo_proceso': 'puntual'
                                        }
                                        self.guardar_proceso_db(datos_fin_valvula)
                        
                        time.sleep(0.1)
                    
                    if fase_completada:
                        self.agregar_notificacion(f"Fase {nombre_fase} (Repetición {repeticion+1}) completada")
                        datos_fin_fase = {
                            'proceso_id': self.proceso_id,
                            'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'fecha_fin': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'valvula': f"Fin fase {fase_idx+1} (Rep {repeticion+1})",
                            'tiempo': 0,
                            'ciclos': 0,
                            'estado': 'C',
                            'fase': fase_global_idx + 1,
                            'tipo_proceso': 'complejo'
                        }
                        self.guardar_proceso_db(datos_fin_fase)
            
            if self.proceso_en_ejecucion:
                self.agregar_notificacion("Proceso completado exitosamente")
                messagebox.showinfo("Éxito", "El proceso se ha completado correctamente")
                
                fecha_fin = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect("procesos.db")
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE procesos 
                    SET fecha_fin=?, estado_valvula='C'
                    WHERE proceso_id=? AND fecha_fin=''
                """, (fecha_fin, self.proceso_id))
                
                datos_fin_proceso = {
                    'proceso_id': self.proceso_id,
                    'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'fecha_fin': fecha_fin,
                    'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'valvula': "Fin proceso",
                    'tiempo': 0,
                    'ciclos': 0,
                    'estado': 'C',
                    'fase': 999,
                    'tipo_proceso': 'complejo'
                }
                
                cursor.execute('''INSERT INTO procesos 
                    (user_id, proceso_id, fecha_inicio, fecha_fin, hora_instruccion, 
                        valvula_activada, tiempo_valvula, ciclos, estado_valvula, fase, tipo_proceso)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (self.user_id,
                    datos_fin_proceso['proceso_id'],
                    datos_fin_proceso['fecha_inicio'],
                    datos_fin_proceso['fecha_fin'],
                    datos_fin_proceso['hora_instruccion'],
                    datos_fin_proceso['valvula'],
                    datos_fin_proceso['tiempo'],
                    datos_fin_proceso['ciclos'],
                    datos_fin_proceso['estado'],
                    datos_fin_proceso['fase'],
                    datos_fin_proceso['tipo_proceso']))
                
                conn.commit()
                conn.close()
            
            self.proceso_en_ejecucion = False
            self.pausar_btn.configure(state="disabled")
            self.ejecutar_btn.configure(state="normal")
            self.master_panel.liberar_bloqueo_hardware()
            
        except Exception as e:
            fecha_fin = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect("procesos.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE procesos 
                SET fecha_fin=?, estado_valvula='E'
                WHERE proceso_id=? AND fecha_fin=''
            """, (fecha_fin, self.proceso_id))
            
            datos_error = {
                'proceso_id': self.proceso_id,
                'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'fecha_fin': fecha_fin,
                'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'valvula': "Error",
                'tiempo': 0,
                'ciclos': 0,
                'estado': 'E',
                'fase': 999,
                'tipo_proceso': 'complejo'
            }
            
            cursor.execute('''INSERT INTO procesos 
                (user_id, proceso_id, fecha_inicio, fecha_fin, hora_instruccion, 
                    valvula_activada, tiempo_valvula, ciclos, estado_valvula, fase, tipo_proceso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (self.user_id,
                datos_error['proceso_id'],
                datos_error['fecha_inicio'],
                datos_error['fecha_fin'],
                datos_error['hora_instruccion'],
                datos_error['valvula'],
                datos_error['tiempo'],
                datos_error['ciclos'],
                datos_error['estado'],
                datos_error['fase'],
                datos_error['tipo_proceso']))
            
            conn.commit()
            conn.close()
            
            self.proceso_en_ejecucion = False
            self.pausar_btn.configure(state="disabled")
            self.ejecutar_btn.configure(state="normal")
            self.master_panel.liberar_bloqueo_hardware()
            self.agregar_notificacion(f"Error en ejecución: {str(e)}")
            messagebox.showerror("Error", f"Ocurrió un error durante la ejecución: {str(e)}")

    def enviar_cadena_serial(self, repeticiones):
        """Send command to ESP32 with validation for repeated phases"""
        try:
            if not hasattr(self.master_panel, 'serial_connection') or not self.master_panel.serial_connection:
                messagebox.showerror("Error", "No hay conexión con la ESP32")
                return False
                
            if not self.master_panel.verificar_ejecucion("nuevoproceso"):
                return False
                
            fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cadenas_fases = []
            
            # Build command for each phase
            for fase_idx, (nombre_fase, valvulas) in enumerate(self.fases_datos.items(), start=1):
                cadenas = []
                for valvula_idx, valvula in enumerate(valvulas, start=1):
                    if valvula['switch'].get():
                        tiempo = self.convertir_a_segundos(
                            valvula['apertura'].get(), 
                            valvula['apertura_unidad'].get()
                        )
                        ciclos = valvula['ciclos'].get() if valvula['ciclos'].get() else 0
                        
                        # Validate times
                        if tiempo > 9999:
                            messagebox.showerror(
                                "Error", 
                                f"Tiempo para {valvula['elemento']} excede el máximo (9999 segundos)"
                            )
                            return False
                            
                        # Build command string
                        motor = f"M{valvula_idx}"
                        ciclos_val = str(ciclos).zfill(4) if ciclos else "0000"
                        cierre_val = self.convertir_a_segundos(
                            valvula['cierre'].get(), 
                            valvula['cierre_unidad'].get()
                        )
                        
                        apertura_str = str(min(tiempo, 9999)).zfill(4)
                        cierre_str = str(min(cierre_val, 9999)).zfill(4)

                        # Determine task type
                        if int(ciclos_val) > 0:
                            tarea = "B"  # Cyclic mode
                        elif tiempo > 0:
                            tarea = "C"  # Timed open/close
                        elif valvula['switch'].get() and tiempo == 0:
                            tarea = "A"  # Simple open
                        else:
                            tarea = "E"  # Error

                        cadena = f"{motor}{tarea}N{ciclos_val}{apertura_str}{cierre_str}"
                        
                        # Validate command length
                        if len(cadena) > 20:  # Per valve limit
                            messagebox.showerror(
                                "Error", 
                                f"Comando para {valvula['elemento']} es demasiado largo"
                            )
                            return False
                            
                        cadenas.append(cadena)
                
                if cadenas:
                    fase_cadena = "".join(cadenas)
                    if len(fase_cadena) > 161:  # Per phase limit
                        messagebox.showerror(
                            "Error", 
                            f"Comando para fase {nombre_fase} es demasiado largo"
                        )
                        return False
                    cadenas_fases.append(fase_cadena)

            # Join all phases with repetitions
            cadena_final = ""
            for _ in range(repeticiones):
                cadena_final += "&".join(cadenas_fases) if cadenas_fases else ""
                cadena_final += "&"  # Add separator between repetitions
            
            # Remove last separator
            cadena_final = cadena_final.rstrip("&")
            
            if len(cadena_final) > 16000:  # Total limit
                messagebox.showerror("Error", "Comando completo es demasiado largo")
                return False
                
            if cadena_final:
                print(f"Cadena a enviar: {cadena_final}")
                if self.master_panel.enviar_comando_serial(cadena_final):
                    messagebox.showinfo("Éxito", "Comando enviado correctamente")
                    return True
                else:
                    messagebox.showerror("Error", "No se pudo enviar el comando")
                    return False
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error al enviar comando: {str(e)}")
            return False

    def pausar_proceso(self):
        """Pausa o reanuda el proceso"""
        if self.proceso_en_ejecucion:
            self.proceso_pausado = not self.proceso_pausado
            if self.proceso_pausado:
                self.tiempo_pausa = time.time()
                self.pausar_btn.configure(text="Reanudar Rutina")
                self.agregar_notificacion("Proceso pausado")
                
                # Enviar comando de pausa a ESP32
                if self.master_panel.enviar_comando_serial("XXXXXXXXXXXXXXXX"):  # Comando de pausa
                    print("Comando de pausa enviado a ESP32 = XXXXXXXXXXXXXXXX")
                    self.master_panel.liberar_bloqueo_hardware()
            else:
                self.tiempo_inicio_fase += time.time() - self.tiempo_pausa
                self.pausar_btn.configure(text="Pausar Rutina")
                self.agregar_notificacion("Proceso reanudado")
                
                # Enviar comando de reanudar a ESP32
                if self.master_panel.verificar_ejecucion("nuevoproceso"):
                    self.master_panel.activar_bloqueo_hardware("nuevoproceso")
                    if self.master_panel.enviar_comando_serial("YYYYYYYYYYYYYYYY"): # Comando de reanudar
                        print("Comando para reanudar enviado a ESP32 = YYYYYYYYYYYYYYYY")

    def paro_emergencia(self):
        """Detiene todos los procesos y envía señal de emergencia a la ESP32"""
        # Detener hilo de ejecución
        if self.proceso_en_ejecucion:
            self.proceso_en_ejecucion = False
            if self.hilo_proceso and self.hilo_proceso.is_alive():
                self.hilo_proceso.join(timeout=1)
        
        # Reiniciar campos
        self.reiniciar_rutina()
        
        # Enviar comando de emergencia
        if self.master_panel.enviar_comando_serial("PPPPPPPPPPPPPPPP"):  # 16 'P'
            self.master_panel.liberar_bloqueo_hardware()
            print("Comando de paro de emergencia enviado a ESP32 = PPPPPPPPPPPPPPPP")
        else:
            self.agregar_notificacion("No hay conexión serial para enviar señal de emergencia")

        # Actualizar UI
        self.pausar_btn.configure(state="disabled", text="Pausar Rutina")
        self.ejecutar_btn.configure(state="normal")

        # Reiniciar contadores visuales
        for fase, valvulas in self.fases_datos.items():
            for valvula in valvulas:
                valvula['progreso'].configure(text="0/0")
                valvula['ciclos_completados'] = 0

        # Notificación emergente
        messagebox.showwarning("‼ PARO DE EMERGENCIA ‼", "Todos los procesos han sido detenidos por seguridad")
        self.agregar_notificacion("🛑 ¡PARO DE EMERGENCIA ACTIVADO! Todos los procesos detenidos")

    def reiniciar_rutina(self):
        """Reinicia completamente la rutina"""
        if self.proceso_en_ejecucion:
            self.proceso_en_ejecucion = False
            if self.hilo_proceso and self.hilo_proceso.is_alive():
                self.hilo_proceso.join(timeout=1)
            
            # Enviar comando de detener a ESP32
            if self.master_panel.enviar_comando_serial("PPPPPPPPPPPPPPPP"):
                self.agregar_notificacion("Proceso detenido")
                self.master_panel.liberar_bloqueo_hardware()
        
        self.proceso_pausado = False
        self.pausar_btn.configure(text="Pausar Rutina", state="disabled")
        self.ejecutar_btn.configure(state="normal")
        
        # Reiniciar contadores y estados
        for fase, valvulas in self.fases_datos.items():
            for valvula in valvulas:
                valvula['progreso'].configure(text="0/0")
                valvula['ciclos_completados'] = 0
        
        # Eliminar fases adicionales
        for nombre_fase in list(self.fases_datos.keys())[1:]:
            self.tabview.delete(nombre_fase)
            del self.fases_datos[nombre_fase]

        self.fase_contador = 1
        self.fase_actual = 0
        self.repeticiones_spinbox.delete(0, "end")
        self.repeticiones_spinbox.insert(0, "1")

        # Reset de la primera fase
        primera_fase = list(self.fases_datos.keys())[0]
        for valvula in self.fases_datos[primera_fase]:
            valvula['switch'].deselect()
            valvula['apertura'].delete(0, "end")
            valvula['cierre'].delete(0, "end")
            valvula['ciclos'].delete(0, "end")
            valvula['progreso'].configure(text="0/0")
            valvula['ciclos_completados'] = 0
            # Deshabilitar campos
            self.toggle_campos_valvula(valvula['switch'], [
                valvula['apertura'], valvula['apertura_unidad'],
                valvula['cierre'], valvula['cierre_unidad'],
                valvula['ciclos']
            ])
        
        # Actualizar lista de fases en control manual
        self.actualizar_lista_fases()
        
        # Liberar bloqueo
        self.master_panel.liberar_bloqueo_hardware()

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
            else:
                # Verificar columnas existentes
                cursor.execute("PRAGMA table_info(procesos)")
                columnas_existentes = [col[1] for col in cursor.fetchall()]
                
                # Añadir columnas faltantes
                columnas_faltantes = {
                    'proceso_id': 'TEXT',
                    'fase': 'INTEGER DEFAULT 1',
                    'tipo_proceso': 'TEXT'
                }
                
                for columna, tipo in columnas_faltantes.items():
                    if columna not in columnas_existentes:
                        try:
                            cursor.execute(f"ALTER TABLE procesos ADD COLUMN {columna} {tipo}")
                            print(f"Columna {columna} añadida a la tabla existente")
                        except sqlite3.OperationalError as e:
                            print(f"Error al añadir columna {columna}: {e}")
            
            tipo_proceso = 'ciclico' if int(datos_proceso.get('ciclos', 0)) > 0 else 'puntual'
            
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
                        tipo_proceso))
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

    def __del__(self):
        """Cleanup resources"""
        try:
            self.stop_event.set()
            
            # Stop execution thread
            if hasattr(self, 'hilo_proceso') and self.hilo_proceso is not None and self.hilo_proceso.is_alive():
                self.hilo_proceso.join(timeout=1)
            
            # Release hardware lock
            if hasattr(self, 'master_panel'):
                self.master_panel.liberar_bloqueo_hardware()
        except Exception as e:
            print(f"Error en limpieza de NuevoProceso: {e}")