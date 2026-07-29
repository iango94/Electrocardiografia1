import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, QtCore
from lector_ecg import LectorECG

class MonitorECGCompleto(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Electrocardiógrafo Digital - Plano Frontal y Precordial")
        self.resize(1200, 900)
        
        # Inicializar hardware
        self.lector = LectorECG()
        self.TAMANO_VENTANA = 1000
        
        # Búferes de datos
        self.nombres_derivaciones = ['dI', 'dII', 'dIII', 'aVR', 'aVL', 'aVF', 'V1', 'V5']
        self.datos = {nombre: np.zeros(self.TAMANO_VENTANA) for nombre in self.nombres_derivaciones}
        
        # Variables de estado de la interfaz
        self.pantalla_congelada = False
        self.lineas_visibles = False
        
        # Contenedor e interfaz principal
        self.widget_principal = QtWidgets.QWidget()
        self.setCentralWidget(self.widget_principal)
        layout_principal = QtWidgets.QVBoxLayout(self.widget_principal)
        
        # --- Panel de Control Superior ---
        self.panel_control = QtWidgets.QHBoxLayout()
        layout_principal.addLayout(self.panel_control)
        
        # Botón 1: Línea Isoeléctrica
        self.btn_isoectrica = QtWidgets.QPushButton("Mostrar Línea Isoeléctrica (0V)")
        self.btn_isoectrica.setCheckable(True)
        self.btn_isoectrica.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: white; border: 1px solid #475569;
                padding: 8px 15px; font-weight: bold; border-radius: 4px; min-width: 220px;
            }
            QPushButton:checked {
                background-color: #991b1b; color: #fecaca; border: 1px solid #f87171;
            }
            QPushButton:hover { background-color: #334155; }
            QPushButton:checked:hover { background-color: #7f1d1d; }
        """)
        self.btn_isoectrica.clicked.connect(self.alternar_linea_isoelectrica)
        self.panel_control.addWidget(self.btn_isoectrica)
        
        # Espacio entre botones
        self.panel_control.addSpacing(10)
        
        # Botón 2: Congelar Pantalla (Freeze)
        self.btn_freeze = QtWidgets.QPushButton("Congelar Pantalla (Freeze)")
        self.btn_freeze.setCheckable(True)
        self.btn_freeze.setStyleSheet("""
            QPushButton {
                background-color: #1e293b; color: white; border: 1px solid #475569;
                padding: 8px 15px; font-weight: bold; border-radius: 4px; min-width: 200px;
            }
            QPushButton:checked {
                background-color: #d97706; color: #fef3c7; border: 1px solid #fbbf24;
            }
            QPushButton:hover { background-color: #334155; }
            QPushButton:checked:hover { background-color: #b45309; }
        """)
        self.btn_freeze.clicked.connect(self.alternar_freeze)
        self.panel_control.addWidget(self.btn_freeze)
        
        self.panel_control.addStretch() # Empuja los botones hacia la izquierda
        
        # Contenedor para las dos columnas de gráficos
        self.layout_graficos = QtWidgets.QHBoxLayout()
        layout_principal.addLayout(self.layout_graficos)
        
        self.win_col1 = pg.GraphicsLayoutWidget()
        self.win_col2 = pg.GraphicsLayoutWidget()
        self.layout_graficos.addWidget(self.win_col1)
        self.layout_graficos.addWidget(self.win_col2)
        
        # Listas de control de gráficos
        self.plots = {}
        self.curvas = {}
        self.lineas_rojas = {}
        
        # Colores de las ondas
        colores = {
            'bipolares': '#00FF00', 'aumentadas': '#FF00FF', 'precordiales': '#00FFFF'
        }
        
        # Construir Columna 1
        self.configurar_canal(self.win_col1, 'dI', "Derivación dI", colores['bipolares'])
        self.configurar_canal(self.win_col1, 'dII', "Derivación dII", colores['bipolares'])
        self.configurar_canal(self.win_col1, 'dIII', "Derivación dIII (dII - dI)", colores['bipolares'])
        self.configurar_canal(self.win_col1, 'aVR', "Derivación aVR", colores['aumentadas'])
        
        # Construir Columna 2
        self.configurar_canal(self.win_col2, 'aVL', "Derivación aVL", colores['aumentadas'])
        self.configurar_canal(self.win_col2, 'aVF', "Derivación aVF", colores['aumentadas'])
        self.configurar_canal(self.win_col2, 'V1', "Derivación V1", colores['precordiales'])
        self.configurar_canal(self.win_col2, 'V5', "Derivación V5", colores['precordiales'])
        
        # Temporizador de actualización
        self.timer = QtCore.QTimer()
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.procesar_y_graficar)
        self.timer.start()

    def configurar_canal(self, contenedor, id_canal, titulo, color_hex):
        """Inicializa una subgráfica"""
        p = contenedor.addPlot()
        contenedor.nextRow()
        
        p.setTitle(titulo, color="w", size="9pt")
        p.setLabel('left', 'Voltaje', units='V')
        p.showGrid(x=True, y=True, alpha=0.15)
        p.setYRange(-1.5, 2.5)
        
        self.curvas[id_canal] = p.plot(pen=pg.mkPen(color_hex, width=1.5))
        self.plots[id_canal] = p
        
        # Línea horizontal discontinua en 0V (Actualizado a PyQt6 enum: QtCore.Qt.PenStyle.DashLine)
        self.lineas_rojas[id_canal] = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('r', width=1, style=QtCore.Qt.PenStyle.DashLine), movable=False)

    def alternar_linea_isoelectrica(self):
        """Muestra u oculta la línea de 0V"""
        self.lineas_visibles = self.btn_isoectrica.isChecked()
        
        if self.lineas_visibles:
            self.btn_isoectrica.setText("Ocultar Línea Isoeléctrica (0V)")
            for nombre in self.nombres_derivaciones:
                self.plots[nombre].addItem(self.lineas_rojas[nombre])
        else:
            self.btn_isoectrica.setText("Mostrar Línea Isoeléctrica (0V)")
            for nombre in self.nombres_derivaciones:
                self.plots[nombre].removeItem(self.lineas_rojas[nombre])

    def alternar_freeze(self):
        """Cambia el estado de congelamiento de la pantalla"""
        self.pantalla_congelada = self.btn_freeze.isChecked()
        if self.pantalla_congelada:
            self.btn_freeze.setText("Reanudar Monitor")
        else:
            self.btn_freeze.setText("Congelar Pantalla (Freeze)")

    def procesar_y_graficar(self):
        """Adquiere señales siempre, pero solo redibuja si no está congelado"""
        try:
            # IMPORTANTE: Se sigue leyendo el hardware para mantener vacíos los búferes del ADS1115
            v_di, v_dii, v_v1, v_v5 = self.lector.leer_canales()
            
            # Si la pantalla está congelada, salimos temprano antes de modificar los datos o gráficos
            if self.pantalla_congelada:
                return
                
            # Ecuaciones matemáticas
            v_diii = v_dii - v_di
            v_avr  = -(v_di + v_dii) / 2.0
            v_avl  = v_di - (v_dii / 2.0)
            v_avf  = v_dii - (v_di / 2.0)
            
            lecturas_instantes = {
                'dI': v_di, 'dII': v_dii, 'dIII': v_diii,
                'aVR': v_avr, 'aVL': v_avl, 'aVF': v_avf,
                'V1': v_v1, 'V5': v_v5
            }
            
            # Desplazar arreglos NumPy y renderizar curvas
            for nombre in self.nombres_derivaciones:
                self.datos[nombre] = np.roll(self.datos[nombre], -1)
                self.datos[nombre][-1] = lecturas_instantes[nombre]
                self.curvas[nombre].setData(self.datos[nombre])
                
        except Exception as e:
            print(f"Error en el procesamiento: {e}")

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOption('background', '#0b0f19')
    pg.setConfigOption('foreground', 'w')
    
    monitor = MonitorECGCompleto()
    monitor.show()
    sys.exit(app.exec())  # En PyQt6 exec_() cambia a exec()