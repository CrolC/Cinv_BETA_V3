import customtkinter as ctk
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
from datetime import datetime
from matplotlib.patches import Rectangle, Patch
import numpy as np
##check the monitoring graph 
class FormMonitoreo(ctk.CTkFrame):
    def __init__(self, panel_principal, user_id):
        super().__init__(panel_principal)
        self.user_id = user_id
        self.master_panel = panel_principal.master
        self.configure(fg_color="#f4f8f7")
        
        # Variables de estado
        self.proceso_activo = None
        self.detener_monitoreo = threading.Event()
        self._hilo_monitoreo = None
        self.tiempo_inicio_proceso = None
        self.ultima_actualizacion = 0
        self.proceso_finalizado = False
        self.datos_proceso = []
        self.fases_data = {}  # Almacena datos de fases para visualización
        
        # Configurar interfaz
        self._crear_interfaz()
        
        # Registrar este panel para recibir mensajes seriales
        self.master_panel.registrar_panel_serial("monitoreo", self)
        
        # Iniciar monitoreo
        self.iniciar_monitoreo()

    def _crear_interfaz(self):
        """Crea la interfaz del panel de monitoreo"""
        # Configurar grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Frame para controles
        self.controles_frame = ctk.CTkFrame(self)
        self.controles_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Título
        ctk.CTkLabel(
            self.controles_frame,
            text="MONITOREO DE PROCESO EN TIEMPO REAL",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10)
        
        # ComboBox para selección de proceso
        self.proceso_combobox = ctk.CTkComboBox(
            self.controles_frame,
            values=self._obtener_procesos_activos(),
            command=self._cambiar_proceso_monitoreado,
            state="readonly",
            width=250
        )
        self.proceso_combobox.pack(side="left", padx=10)
        
        # Botón de actualización
        ctk.CTkButton(
            self.controles_frame,
            text="🔄 Actualizar",
            width=100,
            command=self._actualizar_lista_procesos
        ).pack(side="left", padx=5)
        
        # Frame para la gráfica
        self.grafica_frame = ctk.CTkFrame(self)
        self.grafica_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Gráfica de monitoreo
        self.fig_monitoreo = Figure(figsize=(10, 6), dpi=100)
        self.ax_monitoreo = self.fig_monitoreo.add_subplot(111)
        self.canvas_monitoreo = FigureCanvasTkAgg(self.fig_monitoreo, master=self.grafica_frame)
        self.canvas_monitoreo.get_tk_widget().pack(fill="both", expand=True)
        
        # Configurar gráfica inicial
        self._configurar_grafica_inicial()

    def _configurar_grafica_inicial(self):
        """Configura la gráfica con estado inicial"""
        self.ax_monitoreo.clear()
        self.ax_monitoreo.set_title("MONITOREO DE PROCESO", pad=10, fontsize=14, weight='bold')
        self.ax_monitoreo.set_xlabel("Tiempo (segundos)", labelpad=10)
        self.ax_monitoreo.set_ylabel("Válvulas", labelpad=10)
        self.ax_monitoreo.grid(True, linestyle='--', alpha=0.7)
        
        # Mostrar mensaje inicial
        self.ax_monitoreo.text(0.5, 0.5, 'Seleccione un proceso para comenzar', 
                             horizontalalignment='center',
                             verticalalignment='center',
                             transform=self.ax_monitoreo.transAxes,
                             fontsize=12,
                             color='gray')
        self.canvas_monitoreo.draw()

    def _obtener_procesos_activos(self):
        """Obtiene procesos activos del usuario actual"""
        try:
            conn = sqlite3.connect("procesos.db")
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT proceso_id FROM procesos 
                WHERE user_id=? 
                ORDER BY fecha_inicio DESC
                LIMIT 10
            """, (self.user_id,))
            procesos = [str(row[0]) for row in cursor.fetchall()]
            conn.close()
            return procesos if procesos else ["-- Seleccione --"]
        except Exception as e:
            print(f"Error al obtener procesos: {e}")
            return ["-- Error --"]

    def _actualizar_lista_procesos(self):
        """Actualiza la lista de procesos en el combobox"""
        procesos = self._obtener_procesos_activos()
        current = self.proceso_combobox.get()
        
        self.proceso_combobox.configure(values=procesos)
        
        if current not in procesos:
            self.proceso_combobox.set(procesos[0] if procesos else "-- Seleccione --")

    def _cambiar_proceso_monitoreado(self, choice):
        """Cambia el proceso que se está monitoreando"""
        if choice in ["-- Seleccione --", "-- Error --"]:
            self._configurar_grafica_inicial()
            return
            
        self.proceso_activo = choice
        self.detener_monitoreo.set()  # Detener cualquier monitoreo previo
        
        # Reiniciar variables
        self.datos_proceso = []
        self.fases_data = {}
        self.tiempo_inicio_proceso = None
        self.ultima_actualizacion = 0
        self.proceso_finalizado = False
        
        # Esperar a que el hilo anterior termine
        time.sleep(0.1)
        
        # Reiniciar monitoreo
        self.detener_monitoreo.clear()
        
        if not self._hilo_monitoreo or not self._hilo_monitoreo.is_alive():
            self._hilo_monitoreo = threading.Thread(
                target=self._monitorear_proceso, 
                daemon=True
            )
            self._hilo_monitoreo.start()

    def _monitorear_proceso(self):
        """Monitorea el proceso seleccionado y actualiza la animación"""
        while not self.detener_monitoreo.is_set() and self.proceso_activo:
            try:
                conn = sqlite3.connect("procesos.db")
                cursor = conn.cursor()
                
                # Obtener todos los registros del proceso ordenados por tiempo
                cursor.execute("""
                    SELECT 
                        valvula_activada, 
                        estado_valvula, 
                        tiempo_valvula,
                        hora_instruccion,
                        tipo_proceso,
                        fase,
                        ciclos,
                        fecha_fin
                    FROM procesos 
                    WHERE proceso_id=?
                    ORDER BY hora_instruccion ASC
                """, (self.proceso_activo,))
                
                registros = cursor.fetchall()
                conn.close()
                
                # Verificar si el proceso ha finalizado
                proceso_finalizado = any(reg[7] != '' for reg in registros if reg[7] is not None)
                
                if proceso_finalizado and not self.proceso_finalizado:
                    self.proceso_finalizado = True
                    self.after(0, self.agregar_notificacion, "Proceso finalizado detectado")
                
                # Almacenar todos los datos del proceso
                self.datos_proceso = registros
                
                # Procesar datos para visualización
                self._procesar_datos_visualizacion()
                
                # Actualizar gráfica
                self.after(0, self._actualizar_grafica)
                
                # Diferentes intervalos según si el proceso está activo o finalizado
                time.sleep(0.5 if not self.proceso_finalizado else 2)
                
            except Exception as e:
                print(f"Error al monitorear: {e}")
                time.sleep(2)

    def _procesar_datos_visualizacion(self):
        """Procesa los datos para la visualización con espesor"""
        if not self.datos_proceso:
            return
            
        # Obtener tiempo de inicio del proceso
        tiempo_inicio = datetime.strptime(self.datos_proceso[0][3], '%Y-%m-%d %H:%M:%S')
        self.tiempo_inicio_proceso = tiempo_inicio
        
        # Procesar fases y válvulas
        fases = {}
        for reg in self.datos_proceso:
            fase_num = reg[5]  # Número de fase
            if fase_num not in fases:
                fases[fase_num] = {
                    'valvulas': {},
                    'inicio': None,
                    'fin': None,
                    'tiempo_total': 0,
                    'elementos': set()
                }
            
            # Extraer elemento de "Válvula X"
            valvula_nombre = reg[0]
            elemento = valvula_nombre.replace("Válvula ", "").strip() if "Válvula" in valvula_nombre else valvula_nombre
            
            # Calcular tiempo de apertura total (tiempo * ciclos)
            tiempo_valvula = reg[2] if reg[2] is not None else 0
            ciclos = reg[6] if reg[6] is not None else 1
            tiempo_total = tiempo_valvula * ciclos
            
            # Actualizar información de la fase
            fases[fase_num]['elementos'].add(elemento)
            fases[fase_num]['tiempo_total'] += tiempo_total
            
            # Registrar válvula
            if elemento not in fases[fase_num]['valvulas']:
                fases[fase_num]['valvulas'][elemento] = {
                    'tiempo': tiempo_valvula,
                    'ciclos': ciclos,
                    'estado': reg[1],
                    'tiempo_total': tiempo_total,
                    'eventos': []
                }
            
            # Registrar evento
            hora_instruccion = datetime.strptime(reg[3], '%Y-%m-%d %H:%M:%S')
            tiempo_relativo = (hora_instruccion - tiempo_inicio).total_seconds()
            
            fases[fase_num]['valvulas'][elemento]['eventos'].append({
                'tiempo': tiempo_relativo,
                'estado': reg[1],
                'duracion': tiempo_valvula
            })
            
            # Actualizar tiempos de inicio/fin de fase
            if fases[fase_num]['inicio'] is None or tiempo_relativo < fases[fase_num]['inicio']:
                fases[fase_num]['inicio'] = tiempo_relativo
                
            if reg[1] == 'C' or reg[7] != '':  # Si está cerrado o proceso finalizado
                if fases[fase_num]['fin'] is None or tiempo_relativo > fases[fase_num]['fin']:
                    fases[fase_num]['fin'] = tiempo_relativo
        
        # Calcular espesor proporcional al tiempo total de la fase
        tiempo_max_fase = max(fase['tiempo_total'] for fase in fases.values()) if fases else 1
        
        # Actualizar datos para la visualización
        self.fases_data = {}
        for fase_num, fase_data in fases.items():
            # Calcular espesor proporcional al tiempo total
            espesor = max(0.5, (fase_data['tiempo_total'] / tiempo_max_fase) * 0.8)  # Factor de escala
            
            self.fases_data[fase_num] = {
                'elementos': list(fase_data['elementos']),
                'valvulas': fase_data['valvulas'],
                'tiempo_inicio': fase_data['inicio'],
                'tiempo_fin': fase_data['fin'],
                'tiempo_total': fase_data['tiempo_total'],
                'espesor': espesor,
                'color': self._obtener_color_fase(fase_num)
            }

    def _obtener_color_fase(self, fase_num):
        """Devuelve un color único para cada fase"""
        colores = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d2', '#dbdb8d', '#9edae5', '#393b79'
        ]
        return colores[(int(fase_num) - 1) % len(colores)]

    def _actualizar_grafica(self):
        """Actualiza la gráfica con los datos del proceso"""
        if not self.datos_proceso or not self.fases_data:
            return
            
        self.ax_monitoreo.clear()
        
        # Configuración básica de la gráfica
        self.ax_monitoreo.set_title(f"PROCESO: {self.proceso_activo}", pad=10, fontsize=14, weight='bold')
        self.ax_monitoreo.set_xlabel("Tiempo (segundos)", labelpad=10)
        self.ax_monitoreo.set_ylabel("Válvulas", labelpad=10)
        self.ax_monitoreo.grid(True, linestyle='--', alpha=0.7)
        
        # Obtener lista de válvulas únicas
        valvulas = []
        for fase_data in self.fases_data.values():
            valvulas.extend(fase_data['elementos'])
        valvulas = list(set(valvulas))
        valvulas.sort()
        
        if not valvulas:
            self.ax_monitoreo.text(0.5, 0.5, 'No hay datos de válvulas para mostrar', 
                                 horizontalalignment='center',
                                 verticalalignment='center',
                                 transform=self.ax_monitoreo.transAxes,
                                 fontsize=12,
                                 color='gray')
            self.canvas_monitoreo.draw()
            return
        
        # Mapeo de válvulas a posiciones Y
        y_positions = {valvula: i+1 for i, valvula in enumerate(valvulas)}
        
        # Calcular tiempo total del proceso
        tiempo_inicio = self.tiempo_inicio_proceso
        tiempo_final_reg = [reg for reg in self.datos_proceso if reg[7] != '']
        if tiempo_final_reg:
            tiempo_fin = datetime.strptime(tiempo_final_reg[-1][7], '%Y-%m-%d %H:%M:%S')
            tiempo_total = (tiempo_fin - tiempo_inicio).total_seconds()
        else:
            tiempo_actual = datetime.now()
            tiempo_total = (tiempo_actual - tiempo_inicio).total_seconds()
        
        # Establecer límites del gráfico
        self.ax_monitoreo.set_xlim(0, max(tiempo_total, 10))
        self.ax_monitoreo.set_ylim(0.5, len(valvulas) + 0.5)
        self.ax_monitoreo.set_yticks(range(1, len(valvulas)+1))
        self.ax_monitoreo.set_yticklabels(valvulas)
        
        # Dibujar cada fase con su espesor visual
        for fase_num, fase_data in sorted(self.fases_data.items(), key=lambda x: int(x[0])):
            # Dibujar fondo de fase con espesor
            for valvula in fase_data['elementos']:
                y_pos = y_positions[valvula]
                
                # Dibujar fondo de fase (transparente para mostrar espesor)
                self.ax_monitoreo.barh(
                    y_pos, 
                    fase_data['tiempo_total'],
                    left=fase_data['tiempo_inicio'],
                    height=fase_data['espesor'],
                    color=fase_data['color'],
                    alpha=0.2,
                    edgecolor=fase_data['color'],
                    linewidth=1
                )
                
                # Dibujar estados de la válvula en esta fase
                valvula_data = fase_data['valvulas'][valvula]
                estado_actual = 'C'  # Inicialmente cerrado
                tiempo_inicio_estado = fase_data['tiempo_inicio']
                
                for evento in valvula_data['eventos']:
                    # Dibujar estado anterior
                    if estado_actual == 'A':
                        color = 'green'
                        label = 'Abierto'
                    else:
                        color = 'red'
                        label = 'Cerrado'
                    
                    # Dibujar rectángulo para el estado anterior
                    if evento['tiempo'] > tiempo_inicio_estado:
                        self.ax_monitoreo.barh(
                            y_pos, 
                            evento['tiempo'] - tiempo_inicio_estado,
                            left=tiempo_inicio_estado,
                            height=fase_data['espesor'],
                            color=color,
                            alpha=0.7,
                            edgecolor='none'
                        )
                    
                    # Actualizar estado y tiempo de inicio
                    estado_actual = evento['estado']
                    tiempo_inicio_estado = evento['tiempo']
                
                # Dibujar el último estado hasta el final de la fase
                tiempo_fin_fase = fase_data['tiempo_fin'] if fase_data['tiempo_fin'] is not None else tiempo_total
                
                if estado_actual == 'A':
                    color = 'green'
                    label = 'Abierto'
                else:
                    color = 'red'
                    label = 'Cerrado'
                
                if tiempo_fin_fase > tiempo_inicio_estado:
                    self.ax_monitoreo.barh(
                        y_pos, 
                        tiempo_fin_fase - tiempo_inicio_estado,
                        left=tiempo_inicio_estado,
                        height=fase_data['espesor'],
                        color=color,
                        alpha=0.7,
                        edgecolor='none'
                    )
        
        # Dibujar línea de tiempo actual (solo si el proceso no ha finalizado)
        if not self.proceso_finalizado:
            tiempo_actual = (datetime.now() - tiempo_inicio).total_seconds()
            self.ax_monitoreo.axvline(x=tiempo_actual, color='blue', linestyle='--', alpha=0.7, linewidth=2)
            self.ax_monitoreo.text(tiempo_actual, len(valvulas)+0.2, 'Ahora', 
                                 color='blue', ha='center', va='center')
        
        # Añadir leyenda personalizada
        legend_elements = [
            Patch(facecolor='green', alpha=0.7, edgecolor='none', label='Abierto'),
            Patch(facecolor='red', alpha=0.7, edgecolor='none', label='Cerrado'),
            Patch(facecolor='blue', alpha=0.7, linestyle='--', linewidth=2, label='Tiempo actual')
        ]
        
        # Añadir colores de fases a la leyenda
        for fase_num, fase_data in sorted(self.fases_data.items(), key=lambda x: int(x[0])):
            legend_elements.append(
                Patch(facecolor=fase_data['color'], alpha=0.2, 
                     label=f'Fase {fase_num} ({fase_data["tiempo_total"]}s)')
            )
        
        self.ax_monitoreo.legend(handles=legend_elements, 
                               title="Estados y Fases", 
                               bbox_to_anchor=(1.05, 1), 
                               loc='upper left')
        
        self.fig_monitoreo.tight_layout()
        self.canvas_monitoreo.draw()

    def agregar_notificacion(self, mensaje):
        """Agrega un mensaje al área de notificaciones (si existe)"""
        if hasattr(self, 'notificaciones_text'):
            self.notificaciones_text.configure(state="normal")
            self.notificaciones_text.insert("end", f"- {mensaje}\n")
            self.notificaciones_text.configure(state="disabled")
            self.notificaciones_text.see("end")

    def iniciar_monitoreo(self):
        """Inicia el monitoreo del proceso seleccionado"""
        self._actualizar_lista_procesos()

    def __del__(self):
        """Limpia recursos al destruir el panel"""
        try:
            self.detener_monitoreo.set()
            if hasattr(self, '_hilo_monitoreo') and self._hilo_monitoreo is not None and self._hilo_monitoreo.is_alive():
                self._hilo_monitoreo.join(timeout=1)
            if hasattr(self, 'fig_monitoreo'):
                plt.close(self.fig_monitoreo)
            if hasattr(self, 'master_panel') and hasattr(self.master_panel, 'desregistrar_panel_serial'):
                self.master_panel.desregistrar_panel_serial("monitoreo")
        except Exception as e:
            print(f"Error en limpieza de Monitoreo: {e}")