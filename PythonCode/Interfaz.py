import sys
import serial
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Importamos tu módulo de análisis anterior
import ecg_analisis 

ser = None
t_local = 0
subtimer_local = 0

class MonitorECG_Raspberry(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor ECG - Raspberry Pi")
        
        # Ajustamos el tamaño ideal para pantallas de Raspberry (ej. de 7 u 8 pulgadas)
        self.resize(800, 480) 
        self.setStyleSheet("background-color: #121212; color: white;") # Fondo oscuro médico
        
        self.construir_disposicion_vertical()

    def construir_disposicion_vertical(self):
        # Layout Principal Vertical: Todo lo que agreguemos se apila de arriba hacia abajo
        layout_principal = QtWidgets.QVBoxLayout(self)

        # ==========================================
        # PARTE DE ARRIBA: LA GRÁFICA DEL ECG
        # ==========================================
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot = self.win_grafica.addPlot()
        self.plot.setYRange(-2, 2)
        self.plot.enableAutoRange(axis='y', enable=False)
        
        # Línea de color verde brillante como monitor de hospital
        self.curve = self.plot.plot(pen=pg.mkPen(color='#00ff00', width=2)) 
        
        # Etiqueta amarilla para las Pulsaciones (BPM)
        self.hr_label = pg.TextItem(text="HR: -- bpm", color='y', size='14pt')
        self.plot.addItem(self.hr_label)
        
        # Metemos la gráfica arriba en el layout
        layout_principal.addWidget(self.win_grafica, stretch=3) 

        # Separador visual entre la señal y los controles
        linea_divisoria = QtWidgets.QFrame()
        linea_divisoria.setFrameShape(QtWidgets.QFrame.HLine)
        linea_divisoria.setStyleSheet("color: #444;")
        layout_principal.addWidget(linea_divisoria)

        # ==========================================
        # PARTE DE ABAJO: BOTONES Y CONTROLES
        # ==========================================
        layout_inferior = QtWidgets.QHBoxLayout()

        # Consola interna izquierda para ver estados (reemplaza los prints de la terminal)
        self.consola = QtWidgets.QTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setStyleSheet("background-color: #1e1e1e; color: #00ffcc; border: 1px solid #333;")
        self.consola.setPlaceholderText("Esperando conexión serial...")
        self.consola.setMaximumHeight(110)
        layout_inferior.addWidget(self.consola, stretch=2)

        # Panel derecho de botones de control táctil
        layout_botones = QtWidgets.QGridLayout()
        
        self.btn_conectar = QtWidgets.QPushButton("🔌 Conectar Arduino")
        self.btn_captura = QtWidgets.QPushButton("📸 Tomar Captura (G)")
        self.btn_pdf = QtWidgets.QPushButton("📄 Guardar PDF (R)")
        
        # Diseño estético para que sea fácil de presionar en pantalla táctil
        estilo_botones = "background-color: #2c3e50; font-size: 13px; font-weight: bold; border-radius: 5px; padding: 10px;"
        self.btn_conectar.setStyleSheet("background-color: #27ae60; font-size: 13px; font-weight: bold; border-radius: 5px; padding: 10px;")
        self.btn_captura.setStyleSheet(estilo_botones)
        self.btn_pdf.setStyleSheet(estilo_botones)

        # Acomodamos los botones en una cuadrícula
        layout_botones.addWidget(self.btn_conectar, 0, 0)
        layout_botones.addWidget(self.btn_captura, 0, 1)
        layout_botones.addWidget(self.btn_pdf, 1, 0, 1, 2) # Estirado en dos columnas
        
        layout_inferior.addLayout(layout_botones, stretch=1)
        
        # Agregamos todo el bloque de control abajo en el layout principal
        layout_principal.addLayout(layout_inferior, stretch=1)

        # Conexiones de los botones a sus funciones
        self.btn_conectar.clicked.connect(self.conectar_arduino)
        self.btn_captura.clicked.connect(self.disparar_captura)
        self.btn_pdf.clicked.connect(self.disparar_pdf)

        # Reloj interno de PyQt5 para actualizar la señal cada 10 milisegundos
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.actualizar_senal)

    # ==========================================
    # LÓGICA DE OPERACIÓN (Puente con el Arduino)
    # ==========================================
    def conectar_arduino(self):
        global ser
        try:
            # En Raspberry Pi los puertos suelen llamarse '/dev/ttyUSB0' o '/dev/ttyACM0'
            # Si lo pruebas en Windows, déjalo en 'COM5'
            puerto = '/dev/ttyACM0' if sys.platform.startswith('linux') else 'COM5'
            ser = serial.Serial(puerto, 115200, timeout=1)
            self.consola.append(f"[SISTEMA] Conectado exitosamente en {puerto}")
            self.timer.start(10)
            self.btn_conectar.setEnabled(False)
            self.btn_conectar.setStyleSheet("background-color: #7f8c8d; color: #bdc3c7;")
        except Exception as e:
            self.consola.append(f"[ERROR COM] No se detecta el Arduino: {e}")

    def actualizar_senal(self):
        global t_local, subtimer_local, ser
        if ser is None or not ser.is_open: return

        # Leer todos los datos disponibles que el Nano esté mandando
        while ser.in_waiting:
            try:
                linea = ser.readline().decode().strip()
                if linea:
                    valor = int(linea)
                    ecg_analisis.ecg_buffer.append(valor)
                    t_local += 1 / ecg_analisis.FS
            except:
                pass

        subtimer_local += 1

        # Si ya se llenó el mínimo de muestras, filtramos y pintamos en la gráfica de arriba
        if len(ecg_analisis.ecg_buffer) > ecg_analisis.FS:
            senal_normalizada = ecg_analisis.normalize(list(ecg_analisis.ecg_buffer))
            senal_limpia = ecg_analisis.filtrar_ECG(senal_normalizada) 
            
            # Refrescar los datos en el osciloscopio verde
            self.curve.setData(senal_limpia)

            # Recalcular el ritmo cardíaco (BPM) cada 3 segundos automáticamente
            if len(senal_normalizada) > ecg_analisis.hr_size and subtimer_local >= 255:
                hr = float(ecg_analisis.compute_hr(senal_normalizada))
                if hr > 0:
                    self.hr_label.setText(f"HR: {hr:.1f} bpm")
                    self.hr_label.setPos(len(senal_limpia) * 0.7, max(senal_limpia))
                subtimer_local = 0

    def disparar_captura(self):
        self.consola.append("[ACCIÓN] Capturando ventana de tiempo actual...")
        self.disparar_pdf()

    def disparar_pdf(self):
        exito = ecg_analisis.report_pdf()
        if exito:
            self.consola.append(f"[ÉXITO] PDF guardado en la carpeta del proyecto.")
        else:
            self.consola.append("[ERROR] Espera a que el buffer se llene (6 segundos de señal).")

    # Mantener los atajos de teclado por si conectan un teclado físico a la Raspberry
    def keyPressEvent(self, event):
        if event.text() == 'g': self.disparar_captura()
        elif event.text() == 'r': self.disparar_pdf()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    monitor = MonitorECG_Raspberry()
    monitor.show()
    sys.exit(app.exec_())
