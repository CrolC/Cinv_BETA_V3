import customtkinter as ctk
import sqlite3
import sys
import traceback
import threading
import time
from tkinter import messagebox
import datetime
import uuid
import os

#PENDIENTES: 
##Agregar rutina de tiempo indefinido 
##Aumentar a 5 cifras en seg y a 1000 fases
##quitar conexxion serial, bloqueo de hardware y verificacion de ejecucion, guardar en TXT las cadenas que se mandaban por serial

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
        
        self.agregar_fase("Fase 1")

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
        self.pack(padx=10, pady=10, fill="both", expand=True)

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
        """Validación de entrada numérica - aumentado a 5 cifras (99999)"""
        if text == "":
            return True
        if text.isdigit():
            try:
                val = int(text)
                return val <= 99999  # Aumentado a 5 cifras
            except:
                return False
        return False

    def validar_tiempo(self, entry, unidad_menu):
        """Validación de tiempo de apertura/cierre"""
        try:
            valor = float(entry.get()) if entry.get() else 0
            unidad = unidad_menu.get()
            segundos = self.convertir_a_segundos(valor, unidad)

            if segundos > 99999:  # Aumentado a 5 cifras
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
            apertura = ctk.CTkEntry(apertura_frame, width=60, validate="key", 
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
            cierre = ctk.CTkEntry(cierre_frame, width=60, validate="key", 
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

    def eliminar_fase(self, nombre_fase):
        """Elimina una fase si no es la última"""
        if len(self.tabview._name_list) > 1:
            self.tabview.delete(nombre_fase)
            del self.fases_datos[nombre_fase]
            self.agregar_notificacion(f"Fase {nombre_fase} eliminada")
        else:
            messagebox.showwarning("Advertencia", "No puedes eliminar la última fase")
            self.agregar_notificacion("Intento de eliminar la última fase (no permitido)")

    def guardar_cadena_txt(self, cadena_final):
        """Guarda SOLO la cadena de comandos en un archivo TXT"""
        try:
            # Crear directorio si no existe
            directorio = "comandos_guardados"
            if not os.path.exists(directorio):
                os.makedirs(directorio)
            
            # Generar nombre de archivo con timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"comandos_proceso_{timestamp}.txt"
            ruta_archivo = os.path.join(directorio, nombre_archivo)
            
            # Guardar SOLO la cadena en el archivo
            with open(ruta_archivo, 'w', encoding='utf-8') as archivo:
                archivo.write(cadena_final)
            
            self.agregar_notificacion(f"Comandos guardados en: {ruta_archivo}")
            return True
            
        except Exception as e:
            self.agregar_notificacion(f"Error al guardar archivo TXT: {str(e)}")
            return False

    def generar_cadena_comandos(self, repeticiones):
        """Genera la cadena de comandos para guardar en TXT"""
        try:
            cadenas_fases = []
            
            # Construir comando para cada fase
            for fase_idx, (nombre_fase, valvulas) in enumerate(self.fases_datos.items(), start=1):
                cadenas = []
                for valvula_idx, valvula in enumerate(valvulas, start=1):
                    if valvula['switch'].get():
                        tiempo = self.convertir_a_segundos(
                            valvula['apertura'].get(), 
                            valvula['apertura_unidad'].get()
                        )
                        ciclos = valvula['ciclos'].get() if valvula['ciclos'].get() else 0
                        
                        # Validar tiempos (ahora hasta 99999 segundos)
                        if tiempo > 99999:
                            messagebox.showerror(
                                "Error", 
                                f"Tiempo para {valvula['elemento']} excede el máximo (99999 segundos)"
                            )
                            return None
                            
                        # Construir cadena de comando
                        motor = f"M{valvula_idx}"
                        ciclos_val = str(ciclos).zfill(5) if ciclos else "00000"  # 5 cifras
                        cierre_val = self.convertir_a_segundos(
                            valvula['cierre'].get(), 
                            valvula['cierre_unidad'].get()
                        )
                        
                        apertura_str = str(min(tiempo, 99999)).zfill(5)  # 5 cifras
                        cierre_str = str(min(cierre_val, 99999)).zfill(5)  # 5 cifras

                        # Determinar tipo de tarea
                        if int(ciclos_val) > 0:
                            tarea = "B"  # Modo cíclico
                        elif tiempo > 0:
                            tarea = "C"  # Apertura/cierre temporizado
                        elif valvula['switch'].get() and tiempo == 0:
                            tarea = "A"  # Apertura simple
                        else:
                            tarea = "E"  # Error

                        cadena = f"{motor}{tarea}N{ciclos_val}{apertura_str}{cierre_str}"
                        
                        # Validar longitud del comando
                        if len(cadena) > 25:  # Límite por válvula aumentado
                            messagebox.showerror(
                                "Error", 
                                f"Comando para {valvula['elemento']} es demasiado largo"
                            )
                            return None
                            
                        cadenas.append(cadena)
                
                if cadenas:
                    fase_cadena = "".join(cadenas)
                    if len(fase_cadena) > 200:  # Límite por fase aumentado
                        messagebox.showerror(
                            "Error", 
                            f"Comando para fase {nombre_fase} es demasiado largo"
                        )
                        return None
                    cadenas_fases.append(fase_cadena)

            # Unir todas las fases con repeticiones
            cadena_final = ""
            for _ in range(repeticiones):
                if cadenas_fases:
                    cadena_final += "&".join(cadenas_fases)
                    cadena_final += "&"  # Separador entre repeticiones
            
            # Eliminar último separador
            cadena_final = cadena_final.rstrip("&")
            
            if len(cadena_final) > 20000:  # Límite total aumentado
                messagebox.showerror("Error", "Comando completo es demasiado largo")
                return None
                
            return cadena_final
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar comando: {str(e)}")
            return None

    def iniciar_proceso(self):
        """Inicia el proceso de ejecución de rutina"""
        try:
            if not self.proceso_en_ejecucion:
                # Generar ID de proceso consistente (fecha + hora)
                self.proceso_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Obtener número de repeticiones
                try:
                    repeticiones = int(self.repeticiones_spinbox.get())
                    if repeticiones < 1 or repeticiones > 1000:  # Aumentado a 1000 fases
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
                
                # Generar y guardar cadena de comandos en TXT
                cadena_final = self.generar_cadena_comandos(repeticiones)
                if cadena_final is None:
                    return
                
                if not self.guardar_cadena_txt(cadena_final):
                    messagebox.showerror("Error", "No se pudo guardar los comandos en archivo TXT")
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
            messagebox.showerror("Error", f"Error al iniciar proceso: {str(e)}")
            self.agregar_notificacion(f"Error al iniciar proceso: {str(e)}")

    def ejecutar_proceso(self):
        """Ejecuta el proceso fase por fase y registra todo en la base de datos"""
        try:
            self.agregar_notificacion("Iniciando ejecución de rutina...")
            
            # Obtener número de repeticiones
            try:
                repeticiones = int(self.repeticiones_spinbox.get())
                if repeticiones < 1 or repeticiones > 1000:
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
                                            'valvula': f"Válvula {config['elemento']} - Ciclo {ciclos_completos}",
                                            'tiempo': config['tiempo_ciclo'],
                                            'ciclos': ciclos_completos,
                                            'estado': 'C',
                                            'fase': fase_global_idx + 1,
                                            'tipo_proceso': 'cíclico'
                                        }
                                        self.guardar_proceso_db(datos_ciclo)
                                    
                                    if config['ciclos_completados'] < config['ciclos_totales']:
                                        fase_completada = False
                                else:
                                    tiempo_restante = max(0, config['tiempo_ciclo'] - tiempo_transcurrido_fase)
                                    valvula['progreso'].configure(text=f"T: {int(tiempo_restante)}s")
                                    
                                    if tiempo_transcurrido_fase < config['tiempo_ciclo']:
                                        fase_completada = False
                                    else:
                                        self.agregar_notificacion(f"Válvula {config['elemento']}: Tiempo completado")
                                        datos_tiempo = {
                                            'proceso_id': self.proceso_id,
                                            'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'fecha_fin': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            'valvula': f"Válvula {config['elemento']} - Tiempo completado",
                                            'tiempo': config['tiempo_ciclo'],
                                            'ciclos': 0,
                                            'estado': 'F',
                                            'fase': fase_global_idx + 1,
                                            'tipo_proceso': 'puntual'
                                        }
                                        self.guardar_proceso_db(datos_tiempo)
                        
                        if not fase_completada:
                            time.sleep(1)
                    
                    if self.proceso_en_ejecucion:
                        self.agregar_notificacion(f"{nombre_fase} completada (Repetición {repeticion+1})")
                        datos_fin_fase = {
                            'proceso_id': self.proceso_id,
                            'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'fecha_fin': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'valvula': f"Fin fase {fase_idx+1} (Rep {repeticion+1})",
                            'tiempo': int(time.time() - self.tiempo_inicio_fase),
                            'ciclos': 0,
                            'estado': 'F',
                            'fase': fase_global_idx + 1,
                            'tipo_proceso': 'complejo'
                        }
                        self.guardar_proceso_db(datos_fin_fase)
            
            if self.proceso_en_ejecucion:
                self.agregar_notificacion("Proceso completado exitosamente")
                datos_fin = {
                    'proceso_id': self.proceso_id,
                    'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'fecha_fin': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'valvula': "Fin de proceso complejo",
                    'tiempo': 0,
                    'ciclos': 0,
                    'estado': 'F',
                    'fase': 0,
                    'tipo_proceso': 'complejo'
                }
                self.guardar_proceso_db(datos_fin)
                
                messagebox.showinfo("Éxito", "Proceso completado exitosamente")
        except Exception as e:
            error_msg = f"Error en ejecución: {str(e)}"
            self.agregar_notificacion(error_msg)
            messagebox.showerror("Error", error_msg)
        finally:
            self.proceso_en_ejecucion = False
            self.proceso_pausado = False
            self.ejecutar_btn.configure(state="normal")
            self.pausar_btn.configure(state="disabled", text="Pausar Rutina")
            self.agregar_notificacion("Proceso finalizado")

    def pausar_proceso(self):
        """Pausa o reanuda el proceso"""
        if self.proceso_en_ejecucion:
            if not self.proceso_pausado:
                self.proceso_pausado = True
                self.pausar_btn.configure(text="Reanudar Rutina")
                self.agregar_notificacion("Proceso pausado")
            else:
                self.proceso_pausado = False
                self.pausar_btn.configure(text="Pausar Rutina")
                self.agregar_notificacion("Proceso reanudado")

    def reiniciar_rutina(self):
        """Reinicia la rutina actual"""
        if messagebox.askyesno("Confirmar", "¿Está seguro de reiniciar la rutina?"):
            self.proceso_en_ejecucion = False
            self.proceso_pausado = False
            self.fase_actual = 0
            self.tiempo_pausa = 0
            self.ejecutar_btn.configure(state="normal")
            self.pausar_btn.configure(state="disabled", text="Pausar Rutina")
            self.agregar_notificacion("Rutina reiniciada")
            
            # Reiniciar progresos
            for nombre_fase, valvulas in self.fases_datos.items():
                for valvula in valvulas:
                    valvula['progreso'].configure(text="0/0")

    def paro_emergencia(self):
        """Paro de emergencia del proceso"""
        if messagebox.askyesno("PARO DE EMERGENCIA", "¿Está seguro de activar el paro de emergencia?"):
            self.proceso_en_ejecucion = False
            self.proceso_pausado = False
            self.fase_actual = 0
            self.tiempo_pausa = 0
            self.ejecutar_btn.configure(state="normal")
            self.pausar_btn.configure(state="disabled", text="Pausar Rutina")
            
            # Registrar paro de emergencia en la base de datos
            if hasattr(self, 'proceso_id'):
                datos_paro = {
                    'proceso_id': self.proceso_id,
                    'fecha_inicio': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'fecha_fin': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'hora_instruccion': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'valvula': "PARO DE EMERGENCIA",
                    'tiempo': 0,
                    'ciclos': 0,
                    'estado': 'E',
                    'fase': self.fase_actual,
                    'tipo_proceso': 'emergencia'
                }
                self.guardar_proceso_db(datos_paro)
            
            self.agregar_notificacion("PARO DE EMERGENCIA ACTIVADO")
            messagebox.showwarning("PARO DE EMERGENCIA", "Proceso detenido por emergencia")

    def guardar_proceso_db(self, datos):
        """Guarda los datos del proceso en la base de datos procesos.db"""
        try:
            conn = sqlite3.connect('procesos.db')
            cursor = conn.cursor()
            
            # Verificar si la tabla existe, si no crearla
            cursor.execute('''CREATE TABLE IF NOT EXISTS procesos (
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
                fase INTEGER,
                tipo_proceso TEXT
            )''')
            
            cursor.execute('''
                INSERT INTO procesos (user_id, proceso_id, fecha_inicio, fecha_fin, hora_instruccion, 
                                    valvula_activada, tiempo_valvula, ciclos, estado_valvula, fase, tipo_proceso)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.user_id,
                datos['proceso_id'],
                datos['fecha_inicio'],
                datos.get('fecha_fin', ''),
                datos['hora_instruccion'],
                datos['valvula'],
                datos['tiempo'],
                datos['ciclos'],
                datos['estado'],
                datos['fase'],
                datos['tipo_proceso']
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error al guardar en BD: {e}")
            return False

    def __del__(self):
        """Cleanup resources"""
        try:
            self.stop_event.set()
            
            # Stop execution thread
            if hasattr(self, 'hilo_proceso') and self.hilo_proceso and self.hilo_proceso.is_alive():
                self.hilo_proceso.join(timeout=1)
        except Exception as e:
            print(f"Error en limpieza de NuevoProceso: {e}")