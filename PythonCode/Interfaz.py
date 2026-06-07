import sys
import serial
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# Enlace directo al núcleo analítico
import ecg_analisis 

ser = None
t_local = 0
subtimer_local = 0

class VentanaDatosPaciente(QtWidgets.QDialog):
    """ Ventana de bienvenida táctil para configurar los metadatos """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuración de Paciente")
        self.setFixedSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e; color: white; font-family: Arial;")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        layout.addWidget(QtWidgets.QLabel("<h3>PROYECTO LATIDO - CONFIGURACIÓN</h3>"))
        
        layout.addWidget(QtWidgets.QLabel("Nombre Completo:"))
        self.txt_nombre = QtWidgets.QLineEdit("Paciente_Raspberry")
        self.txt_nombre.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555; padding: 5px;")
        layout.addWidget(self.txt_nombre)
        
        layout.addWidget(QtWidgets.QLabel("Edad:"))
        self.txt_edad = QtWidgets.QLineEdit("25")
        self.txt_edad.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555; padding: 5px;")
        layout.addWidget(self.txt_edad)
        
        layout.addWidget(QtWidgets.QLabel("Sexo Biológico:"))
        self.cb_sexo = QtWidgets.QComboBox()
        self.cb_sexo.addItems(["M", "F"])
        self.cb_sexo.setStyleSheet("background-color: #2b2b2b; color: white; padding: 5px;")
        layout.addWidget(self.cb_sexo)
        
        self.btn_listo = QtWidgets.QPushButton("Iniciar Sistema de Monitoreo")
        self.btn_listo.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        self.btn_listo.clicked.connect(self.guardar_y_entrar)
        layout.addWidget(self.btn_listo)

    def guardar_y_entrar(self):
        ecg_analisis.paciente = self.txt_nombre.text().strip()
        ecg_analisis.file_name = f"ECG_{ecg_analisis.paciente}.pdf"
        try:
            ecg_analisis.diagnostico['edad'] = int(self.txt_edad.text())
        except:
            ecg_analisis.diagnostico['edad'] = 25
        ecg_analisis.diagnostico['sexo'] = self.cb_sexo.currentText()
        self.accept()


class MonitorECG_Raspberry(QtWidgets.QWidget):
    """ Interfaz Gráfica Vertical optimizada para Pantallas de Raspberry Pi """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Monitor Isquémico Integrado - Paciente: {ecg_analisis.paciente}")
        self.resize(800, 480) # Resolución estándar pantallas oficiales Raspberry
        self.setStyleSheet("background-color: #101010; color: white; font-family: Arial;")
        
        self.inicializar_interfaz_vertical()

    def inicializar_interfaz_vertical(self):
        # Layout estructural de arriba a abajo
        layout_principal = QtWidgets.QVBoxLayout(self)

        # ==========================================
        # SECCIÓN SUPERIOR: OSCILOSCOPIO ECG (70% del alto)
        # ==========================================
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot = self.win_grafica.addPlot()
        self.plot.setYRange(-2, 2)
        self.plot.enableAutoRange(axis='y', enable=False)
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        
        # Trazo electromédico verde fosforescente de alta visibilidad
        self.curve = self.plot.plot(pen=pg.mkPen(color='#39ff14', width=2))
        
        # Indicador digital de pulso instantáneo
        self.hr_label = pg.TextItem(text="HR: -- bpm", color='#ffff00', size='15pt', bold=True)
        self.plot.addItem(self.hr_label)
        
        layout_principal.addWidget(self.win_grafica, stretch=3)

        # Divisor físico discreto
        linea = QtWidgets.QFrame()
        linea.setFrameShape(QtWidgets.QFrame.HLine)
        linea.setStyleSheet("color: #333;")
        layout_principal.addWidget(linea)

        # ==========================================
        # SECCIÓN INFERIOR: BOTONES Y LOGS (30% del alto)
        # ==========================================
        layout_controles = QtWidgets.QHBoxLayout()

        # Consola de estado del software clínico (Izquierda)
        self.consola = QtWidgets.QTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setStyleSheet("background-color: #151515; color: #00ffcc; border: 1px solid #222; font-size: 11px;")
        self.consola.append(f"[SISTEMA] Iniciado monitor para paciente: {ecg_analisis.paciente}")
        self.consola.append("[GUÍA] Presione 'Conectar' para enlazar el hardware.")
        layout_controles.addWidget(self.consola, stretch=2)

        # Matriz de Botones Gigantes para pulsación táctil (Derecha)
        layout_botones = QtWidgets.QGridLayout()
        
        self.btn_conectar = QtWidgets.QPushButton("🔌 Conectar Hardware")
        self.btn_reporte = QtWidgets.QPushButton("📄 Generar Reporte ST (R)")
        
        # Ajuste de estilos CSS táctiles
        estilo_tactivo = "background-color: #2980b9; font-size: 13px; font-weight: bold; border-radius: 6px; padding: 12px;"
        self.btn_conectar.setStyleSheet("background-color: #27ae60; font-size: 13px; font-weight: bold; border-radius: 6px; padding: 12px;")
        self.btn_reporte.setStyleSheet(estilo_tactivo)
        
        layout_botones.addWidget(self.btn_conectar, 0, 0)
        layout_botones.addWidget(self.btn_reporte, 1, 0)
        
        layout_controles.addLayout(layout_botones, stretch=1)
        layout_principal.addLayout(layout_controles, stretch=1)

        # Accionadores funcionales
        self.btn_conectar.clicked.connect(self.conectar_puerto)
        self.btn_reporte.clicked.connect(self.ejecutar_reporte_medico)

        # Temporizador de refresco sincrónico (10 ms)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.procesar_ciclo_muestreo)

    def conectar_puerto(self):
        global ser
        try:
            # Enrutamiento automático: detecta si es el puerto serial de Linux/Raspberry o de Windows
            puerto_activo = '/dev/ttyACM0' if sys.platform.startswith('linux') else 'COM5'
            ser = serial.Serial(puerto_activo, 115200, timeout=1)
            self.consola.append(f"[HARDWARE] Conexión establecida de forma rígida en {puerto_activo}")
            self.timer.start(10)
            self.btn_conectar.setEnabled(False)
            self.btn_conectar.setStyleSheet("background-color: #444; color: #888; border-radius: 6px;")
        except Exception as e:
            self.consola.append(f"[FALLO HARDWARE] No se detectó señal serial en el puerto configurado: {e}")

    def procesar_ciclo_muestreo(self):
        global t_local, subtimer_local, ser
        if ser is None or not ser.is_open: return

        # Vaciado del búfer del puerto serial hacia el buffer dinámico
        while ser.in_waiting:
            try:
                linea = ser.readline().decode().strip()
                if linea:
                    valor_adc = int(linea)
                    ecg_analisis.ecg_buffer.append(valor_adc)
                    t_local += 1 / ecg_analisis.FS
            except:
                pass

        subtimer_local += 1

        # Renderizado en tiempo real sobre la gráfica superior
        if len(ecg_analisis.ecg_buffer) > ecg_analisis.FS:
            raw_signals = ecg_analisis.normalize(list(ecg_analisis.ecg_buffer))
            cleaned_signals = ecg_analisis.filtrar_ECG(raw_signals)
            self.curve.setData(cleaned_signals)

            # Estimación algorítmica de pulso en pantalla cada 2.5 segundos
            if len(raw_signals) > ecg_analisis.hr_size and subtimer_local >= 220:
                try:
                    _, info_pks = nk.ecg_peaks(cleaned_signals, sampling_rate=ecg_analisis.FS)
                    hr = (len(info_pks["ECG_R_Peaks"]) / (len(cleaned_signals)/ecg_analisis.FS)) * 60.0
                    self.hr_label.setText(f"HR: {hr:.1f} bpm")
                    self.hr_label.setPos(len(cleaned_signals)*0.02, 1.6)
                except:
                    pass
                subtimer_local = 0

    def ejecutar_reporte_medico(self):
        self.consola.append("[PROCESANDO] Corriendo árboles lógicos y transformada DWT...")
        exito, mensaje = ecg_analisis.report_pdf()
        if exito:
            self.consola.append(f"[ÉXITO INFORME] PDF Generado en la ruta destino.")
            self.consola.append(f"[MÉTRICAS]: {mensaje}")
        else:
            self.consola.append("[PROCESO RECHAZADO] Captura incompleta. Espere a rellenar el buffer (6 segundos).")

    def keyPressEvent(self, event):
        # Soporte para teclados físicos de desarrollo
        if event.text() == 'r': self.ejecutar_reporte_medico()
        elif event.text() == 'l':
            ecg_analisis.DIVISOR_TENSION += 20
            self.consola.append(f"[DIVISOR] Ajustado a {ecg_analisis.DIVISOR_TENSION}")
        elif event.text() == 'h':
            ecg_analisis.DIVISOR_TENSION -= 20
            self.consola.append(f"[DIVISOR] Ajustado a {ecg_analisis.DIVISOR_TENSION}")


# ========================================================
# CONTROL DE ARRANQUE DE LA APLICACIÓN
# ========================================================
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    
    # 1. Solicita datos del paciente con interfaz táctil fluida al inicio
    login = VentanaDatosPaciente()
    if login.exec_() == QtWidgets.QDialog.Accepted:
        # 2. Si el operador da aceptar, despliega el monitor principal (Gráfica arriba, botones abajo)
        monitor = MonitorECG_Raspberry()
        monitor.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
