import sys
import numpy as np
import serial
import neurokit2 as nk
from collections import deque
from scipy.signal import butter, sosfiltfilt
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

# ========================================================
# CONFIGURACIÓN Y VARIABLES GLOBALES (Mantenidas de tu base)
# ========================================================
PORT = 'COM5'
BAUD = 115200
FS = 360
RESOLUCION = [0, 1023]
GANANCIA = 1000 

BUFFER_SECONDS = 6
HR_WINDOW = 3
buffer_size = FS * BUFFER_SECONDS
hr_size = FS * HR_WINDOW

# Variables de control y almacenamiento
RUTA = "C:\\Users\\Jacobo\\Documents\\proyectosActuales\\ECG\\ElectrosTomados\\"
paciente = "PresentacionClase"
file_name = "ECG_" + paciente + ".pdf"

SHOW_Q = True    
SHOW_R = True    
SHOW_S = True    
SHOW_R_ON = True
SHOW_R_OF = True

diagnostico = {'edad': 20, 'sexo': 'M'}
respuestas_cuestionario = {} # Para almacenar las respuestas de la interfaz

DIVISOR_TENSION = 1023
NK_METHOD = 'neurokit'

nk_ECG_dataframe = None
nk_ECG_info = None
nk_ECG_error = None

ser = None # Se inicializará al dar click en conectar
t = 0
subtimer = 0

ecg_buffer = deque(maxlen=buffer_size)
time_buffer = deque(maxlen=buffer_size)

# Filtros
CORTE_BAJO = 0.5
CORTE_ALTO = 150
FR_RED = 60
ORDEN_FILTRO = 4

# ========================================================
# OPERACIONES MATEMÁTICAS Y PROCESAMIENTO (Tu lógica intacta)
# ========================================================
def obtener_tiempo():
    zona = pytz.timezone("America/Bogota")
    ahora = datetime.now(zona)
    return ahora.strftime("%Y-%m-%d %H:%M:%S")

def incrementar_divisor():
    global DIVISOR_TENSION
    DIVISOR_TENSION += 20

def reducir_divisor():
    global DIVISOR_TENSION
    DIVISOR_TENSION -= 20

def normalize(signal):
    signal = np.array(signal)
    return ((signal / DIVISOR_TENSION) * 3.3) - 1.65 

def filtrar_ECG(senal, modo = 3):
    if modo == 3:
        sos_pasabanda = butter(N=ORDEN_FILTRO, Wn=[CORTE_BAJO, CORTE_ALTO], fs=FS, btype='band', output='sos')
        prefiltrado = sosfiltfilt(sos_pasabanda, senal)
        sos_notch = butter(N=ORDEN_FILTRO, Wn=[(FR_RED-5), (FR_RED+5)], fs=FS, btype='bandstop', output='sos')
        return sosfiltfilt(sos_notch, prefiltrado)
    return nk.ecg_clean(senal, sampling_rate=FS)

def compute_hr(signal):
    try:
        ecg_signals, info = nk.ecg_process(signal, sampling_rate=FS)
        average_hr = ecg_signals["ECG_Rate"]
        return average_hr[1]
    except:
        return -1

def compute_avr_hr(signal):
    try:
        ecg_signals, info = nk.ecg_process(signal, sampling_rate=FS)
        average_hr = ecg_signals["ECG_Rate"]
        return np.mean(average_hr)
    except:
        return -1

def calculate_qrs(ecg_signal):
    try:
        ecg, info = nk.ecg_process(ecg_signal, sampling_rate=FS)
        _, waves = nk.ecg_delineate(ecg, info["ECG_R_Peaks"], sampling_rate=FS, show=False, method="dwt")
        qrs_onsets = waves['ECG_R_Onsets']
        qrs_offsets = waves['ECG_R_Offsets']
        
        qrs_durations = (np.array(qrs_offsets) - np.array(qrs_onsets)) / FS
        avr = np.nanmean(qrs_durations) * 1000
        qrs_max = np.nanmax(qrs_durations) * 1000
        qrs_min = np.nanmin(qrs_durations) * 1000

        qrs_peaks = [info['ECG_Q_Peaks'], info['ECG_R_Peaks'], info['ECG_S_Peaks']]
        qrs_times = [round(qrs_min, 2), round(avr, 2), round(qrs_max, 2)]
        qrs_ons_offs = [waves['ECG_R_Onsets'], waves['ECG_R_Offsets']]
        analisis = "QRS normal" if avr < 120 else "QRS ancho"
        return qrs_times, qrs_peaks, qrs_ons_offs, analisis
    except Exception as e:
        return [0,0,0], [[],[],[]], [[],[]], "Error análisis"

def export_pdf():
    global file_name, paciente, RUTA
    archivo = RUTA + file_name
    if len(ecg_buffer) < buffer_size: return
    
    signal = normalize(list(ecg_buffer))
    cleaned = filtrar_ECG(signal)
    time = np.linspace(0, BUFFER_SECONDS, len(signal))
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, BUFFER_SECONDS)
    ax.set_ylim(-3, 3)
    
    for x in np.arange(0, BUFFER_SECONDS, 0.04): ax.axvline(x, color='#ffcccc', linewidth=0.5)
    for x in np.arange(0, BUFFER_SECONDS, 0.2): ax.axvline(x, color='#ff6666', linewidth=1)
    for y in np.arange(-2, 2, 0.1): ax.axhline(y, color='#ffcccc', linewidth=0.5)
    for y in np.arange(-2, 2, 0.5): ax.axhline(y, color='#ff6666', linewidth=1)
    
    ax.plot(time, cleaned, color='black', linewidth=1.2)
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)
    plt.title(f"ECG {paciente} {obtener_tiempo()}", fontsize=12)
    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"PDF guardado como: {file_name}")

def report_pdf():
    global file_name, paciente, RUTA
    archivo = RUTA + "Reporte" + file_name
    if len(ecg_buffer) < buffer_size: return

    signal = normalize(list(ecg_buffer))
    cleaned = filtrar_ECG(signal)
    qrs_times, qrs_peaks, qrs_ons_offs, qrs_analisis = calculate_qrs(signal)
    pulso = compute_avr_hr(signal)
    time = np.linspace(0, BUFFER_SECONDS, len(signal))

    fig, ax = plt.subplots(figsize=(12, 3))
    sex = 'Masculino' if diagnostico['sexo'] == 'M' else 'Femenino'
    ax.text(0.5, 1.2, f"Nombre: {paciente}\nEdad: {diagnostico['edad']}\nSexo: {sex}")
    ax.text(2.0, 1.2, f"Pulso: {pulso:.1f} bpm\nInt. QRS promedio: {qrs_times[1]}ms")
    ax.text(3.5, 1.5, qrs_analisis)

    for x in np.arange(0, BUFFER_SECONDS, 0.04): ax.axvline(x, color='#ffcccc', linewidth=0.5)
    for x in np.arange(0, BUFFER_SECONDS, 0.2): ax.axvline(x, color='#ff6666', linewidth=1)
    for y in np.arange(-2, 2, 0.1): ax.axhline(y, color='#ffcccc', linewidth=0.5)
    for y in np.arange(-2, 2, 0.5): ax.axhline(y, color='#ff6666', linewidth=1)

    ax.plot(time, cleaned, color='black', linewidth=1.2)

    if SHOW_Q and len(qrs_peaks[0]) > 0:
        ax.scatter([k/FS for k in qrs_peaks[0]], [cleaned[int(k)]-0.04 for k in qrs_peaks[0]], color='red', s=5, zorder=5)
    if SHOW_R and len(qrs_peaks[1]) > 0:
        ax.scatter([k/FS for k in qrs_peaks[1]], [cleaned[int(k)]+0.04 for k in qrs_peaks[1]], color='yellow', s=5, zorder=5)
    if SHOW_S and len(qrs_peaks[2]) > 0:
        ax.scatter([k/FS for k in qrs_peaks[2]], [cleaned[int(k)]-0.04 for k in qrs_peaks[2]], color='blue', s=5, zorder=5)

    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)
    plt.title(f"ECG {paciente} {obtener_tiempo()}", fontsize=12)
    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"PDF guardado como: Reporte{file_name}")

def neurokit_analisis():
    if len(ecg_buffer) < buffer_size: return
    ekg = normalize(list(ecg_buffer))
    archivo = RUTA + "NK_ANALISIS_" + paciente + ".pdf"
    signals, info = nk.ecg_process(np.array(ekg), sampling_rate=FS)
    nk.ecg_plot(signals, info)
    fig = plt.gcf()
    fig.set_size_inches(10, 12, forward=True)
    fig.savefig(archivo)
    plt.close()

def full_analisis():
    try:
        neurokit_analisis()
        report_pdf()
        return True
    except:
        return False


# ========================================================
# CLASES DE INTERFAZ GRÁFICA (PyQt5)
# ========================================================

class PortadaECG(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PORTADA DEL PROYECTO")
        self.setFixedSize(450, 380)
        layout = QtWidgets.QVBoxLayout(self)

        lbl_titulo = QtWidgets.QLabel("<h2>SISTEMA DE ELECTROCARDIOGRAFÍA</h2>")
        lbl_titulo.setStyleSheet("color: #1f618d;")
        layout.addWidget(lbl_titulo)

        # Reemplazo de los inputs de consola obsoletos
        layout.addWidget(QtWidgets.QLabel("<b>Nombre del Paciente:</b>"))
        self.txt_nombre = QtWidgets.QLineEdit("PresentacionClase")
        layout.addWidget(self.txt_nombre)

        layout.addWidget(QtWidgets.QLabel("<b>Edad (Años):</b>"))
        self.txt_edad = QtWidgets.QLineEdit("22")
        layout.addWidget(self.txt_edad)

        layout.addWidget(QtWidgets.QLabel("<b>Sexo Biológico:</b>"))
        self.cb_sexo = QtWidgets.QComboBox()
        self.cb_sexo.addItems(["M", "F"])
        layout.addWidget(self.cb_sexo)

        btn_entrar = QtWidgets.QPushButton("Iniciar Monitor e Interfaz")
        btn_entrar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 35px;")
        btn_entrar.clicked.connect(self.procesar_datos_iniciales)
        layout.addWidget(btn_entrar)

    def procesar_datos_iniciales(self):
        global paciente, file_name, diagnostico
        paciente = self.txt_nombre.text().strip()
        file_name = "ECG_" + paciente + ".pdf"
        diagnostico['edad'] = int(self.txt_edad.text())
        diagnostico['sexo'] = self.cb_sexo.currentText()
        self.accept()


class CuestionarioECG(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cuestionario de Control Médico")
        self.setFixedSize(550, 420)
        self.respuestas = {}
        self.preguntas = [
            "1. ¿Siente algún dolor o presión inusual en el pecho en este momento?",
            "2. ¿Ha percibido palpitaciones rápidas o arrítmicas recientemente?",
            "3. ¿Tiene antecedentes familiares directos de patologías cardíacas?",
            "4. ¿Sufre de mareos frecuentes o pérdidas temporales de conocimiento?"
        ]
        self.indice = 0

        layout = QtWidgets.QVBoxLayout(self)

        # --- Apartado Superior: Gráfico del Cuestionario ---
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot_decorativo = self.win_grafica.addPlot()
        self.plot_decorativo.setYRange(-0.5, 1.5)
        self.curve_dec = self.plot_decorativo.plot(pen='r')
        self.win_grafica.setMaximumHeight(180)
        layout.addWidget(self.win_grafica)

        # Texto dinámico de la pregunta
        self.lbl_pregunta = QtWidgets.QLabel(self.preguntas[self.indice])
        self.lbl_pregunta.setStyleSheet("font-size: 13px; font-weight: bold; margin: 15px 0px; color: #2c3e50;")
        layout.addWidget(self.lbl_pregunta)

        # --- Apartado Inferior: Los 3 botones solicitados ---
        layout_botones = QtWidgets.QHBoxLayout()
        self.btn_si = QtWidgets.QPushButton("Sí")
        self.btn_no = QtWidgets.QPushButton("No")
        self.btn_pnr = QtWidgets.QPushButton("Prefiero no responder")

        self.btn_si.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; height: 35px;")
        self.btn_no.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; height: 35px;")
        self.btn_pnr.setStyleSheet("background-color: #95a5a6; color: white; font-weight: bold; height: 35px;")

        layout_botones.addWidget(self.btn_si)
        layout_botones.addWidget(self.btn_no)
        layout_botones.addWidget(self.btn_pnr)
        layout.addLayout(layout_botones)

        self.btn_si.clicked.connect(lambda: self.guardar_respuesta("Sí"))
        self.btn_no.clicked.connect(lambda: self.guardar_respuesta("No"))
        self.btn_pnr.clicked.connect(lambda: self.guardar_respuesta("Prefiero no responder"))

        self.dibujar_pulso_ejemplo()

    def dibujar_pulso_ejemplo(self):
        # Dibujo rápido de un complejo electrocardiográfico estético en el cuestionario
        x = np.linspace(0, 2, 100)
        y = np.zeros_like(x)
        y[30:33] = 1.2; y[28:30] = -0.2; y[33:36] = -0.3 # Simulación R, Q, S
        self.curve_dec.setData(x, y)
        self.plot_decorativo.hideAxis('bottom')
        self.plot_decorativo.hideAxis('left')

    def guardar_respuesta(self, valor):
        self.respuestas[self.preguntas[self.indice]] = valor
        self.indice += 1
        if self.indice < len(self.preguntas):
            self.lbl_pregunta.setText(self.preguntas[self.indice])
        else:
            QtWidgets.QMessageBox.information(self, "Terminado", "Cuestionario guardado.")
            self.accept()


class VentanaPrincipalECG(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Monitor de ECG en Tiempo Real - Paciente: {paciente}")
        self.setGeometry(100, 100, 950, 600)
        self.crear_ui()

    def crear_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Selector de Puerto COM para que el usuario elija dinámicamente
        layout_com = QtWidgets.QHBoxLayout()
        layout_com.addWidget(QtWidgets.QLabel("<b>Seleccionar Puerto Serial de Conexión:</b>"))
        self.combo_puerto = QtWidgets.QComboBox()
        self.combo_puerto.addItems([f"COM{i}" for i in range(1, 9)])
        self.combo_puerto.setCurrentText(PORT)
        layout_com.addWidget(self.combo_puerto)
        
        self.btn_conectar = QtWidgets.QPushButton("Conectar Arduino Nano")
        self.btn_conectar.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_conectar.clicked.connect(self.conectar_serial)
        layout_com.addWidget(self.btn_conectar)
        layout.addLayout(layout_com)

        # Consola de texto central para reportes y logs
        self.consola = QtWidgets.QTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setPlaceholderText("Logs operativos e información clínica...")
        layout.addWidget(self.consola)

        # UI de Gráfica Pyqtgraph (Tus configuraciones exactas de YRange)
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot = self.win_grafica.addPlot(title="ECG")
        self.plot.setYRange(-2, 2)
        self.plot.enableAutoRange(axis='y', enable=False)
        self.curve = self.plot.plot(pen='g')

        self.hr_label = pg.TextItem(color='y')
        self.plot.addItem(self.hr_label)
        layout.addWidget(self.win_grafica)

        # Botonera de control
        layout_botones = QtWidgets.QHBoxLayout()
        self.btn_cuestionario = QtWidgets.QPushButton("Responder Cuestionario")
        self.btn_g = QtWidgets.QPushButton("Guardar Instantánea (G)")
        self.btn_r = QtWidgets.QPushButton("Guardar Reporte (R)")
        self.btn_f = QtWidgets.QPushButton("Análisis NeuroKit completo (F)")

        layout_botones.addWidget(self.btn_cuestionario)
        layout_botones.addWidget(self.btn_g)
        layout_botones.addWidget(self.btn_r)
        layout_botones.addWidget(self.btn_f)
        layout.addLayout(layout_botones)

        # Eventos
        self.btn_cuestionario.clicked.connect(self.abrir_cuestionario)
        self.btn_g.clicked.connect(export_pdf)
        self.btn_r.clicked.connect(report_pdf)
        self.btn_f.clicked.connect(full_analisis)

        # Configuración de tu bucle/loop de actualización mediante un QTimer nativo
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_loop)

    def conectar_serial(self):
        global ser
        puerto_seleccionado = self.combo_puerto.currentText()
        try:
            ser = serial.Serial(puerto_seleccionado, BAUD)
            self.consola.append(f"[HARDWARE] Conectado exitosamente al puerto {puerto_seleccionado}")
            self.timer.start(10) # Tu frecuencia de refresco original del timer de 10ms
            self.btn_conectar.setEnabled(False)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error Serial", f"No se pudo abrir el puerto: {e}")

    def abrir_cuestionario(self):
        dialogo = CuestionarioECG()
        if dialogo.exec_():
            global respuestas_cuestionario
            respuestas_cuestionario = dialogo.respuestas
            texto_reporte = [f"\n=== CUESTIONARIO PREVIO DEL PACIENTE ==="]
            for pr, re in respuestas_cuestionario.items():
                texto_reporte.append(f"· {pr} -> Resp: {re}")
            texto_reporte.append("=========================================\n")
            self.consola.append("\n".join(texto_reporte))

    def update_loop(self):
        """Tu función original 'update' de captura y ploteo adaptada al canvas de la clase"""
        global t, subtimer, ser
        if ser is None or not ser.is_open: return

        tiempo_subtimer = 3 
        control_subtimer = 85 * tiempo_subtimer

        while ser.in_waiting:
            try:
                value = int(ser.readline().decode().strip())
                ecg_buffer.append(value)
                time_buffer.append(t)
                t += 1 / FS
            except:
                pass

        subtimer += 1

        if len(ecg_buffer) > FS:
            signal = normalize(list(ecg_buffer))
            cleaned = filtrar_ECG(signal) 
            self.curve.setData(cleaned)

            if len(signal) > hr_size and subtimer >= control_subtimer:
                hr = float(compute_hr(signal))
                self.hr_label.setText(f"HR: {hr:.1f} bpm")
                self.hr_label.setPos(len(signal)*0.7, max(cleaned))
                subtimer = 0

    def keyPressEvent(self, event):
        """Tus atajos de teclado originales mapeados a las teclas"""
        if event.text() == 'g': export_pdf()
        elif event.text() == 'r': report_pdf()
        elif event.text() == 'h': reducir_divisor(); self.consola.append(f"[DIVISOR] Reducido a: {DIVISOR_TENSION}")
        elif event.text() == 'l': incrementar_divisor(); self.consola.append(f"[DIVISOR] Incrementado a: {DIVISOR_TENSION}")
        elif event.text() == 'f': full_analisis()


# ========================================================
# FLUJO DE ARRANQUE ORDENADO
# ========================================================
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    
    # 1. Se despliega la portada para tomar los datos del paciente sin romper la consola
    portada = PortadaECG()
    if portada.exec_() == QtWidgets.QDialog.Accepted:
        # 2. Si se aceptan los datos, se lanza la interfaz de monitoreo principal
        main_window = VentanaPrincipalECG()
        main_window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
