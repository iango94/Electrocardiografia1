import sys
import numpy as np
import serial
import neurokit2 as nk
from collections import deque
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import matplotlib.pyplot as plt
import matplotlib.backends
from datetime import datetime
import pytz

# =========================
# CONFIG
# =========================
def get_port():
    elect = int(input("Digite numero puerto serie (3 para COM3, 4 para COM4): "))
    match elect:
        case 1:
            return "COM1"
        case 2: 
            return "COM2"
        case 3:
            return "COM3"
        case 4:
            return "COM4"
        case 5:
            return "COM5"
        case 6:
            return "COM6"
        case 7:
            return "COM7"
        case 8:
            return "COM8"
        case _:
            return "COM5"

PORT = get_port() 
BAUD = 115200
FS = 360


BUFFER_SECONDS = 6
HR_WINDOW = 3

buffer_size = FS * BUFFER_SECONDS
hr_size = FS * HR_WINDOW

PACIENTE = "PresentacionClase"
FILE_NAME = "ECG_" + PACIENTE + ".pdf"
RUTA = "C:\\Users\\Jacobo\\Documents\\Nacho\\1 Semestre\\Intro Electronica\\PresentacionECG\\Electrocardiografia1\\ECGs\\"

print(f"presione:\n 'g' para guardar instantanea\n 'r' para guardar istantanea con reporte\n 'h' para incrementar amplitud \n 'l' para reducir amplitud")

DIVISOR_TENSION = 250
DIVISOR_TENSION2 = 180

# =========================
# SERIAL
# =========================
ser = serial.Serial(PORT, BAUD)

# =========================
# BUFFERS
# =========================
ecg_buffer = deque(maxlen=buffer_size)
time_buffer = deque(maxlen=buffer_size)

# =========================
# QT APP
# =========================
app = QtWidgets.QApplication([])
win = pg.GraphicsLayoutWidget(title="ECG en Tiempo Real")
plot = win.addPlot(title="ECG")

#agregado 1
plot.setYRange(-1.5, 1.5)
plot.enableAutoRange(axis='y', enable=False)
#fin agregado 1

curve = plot.plot(pen='g')


hr_label = pg.TextItem(color='y')
plot.addItem(hr_label)

win.show()

t = 0
subtimer = 0

# =========================
# MICELANEOS
# =========================

def obtener_tiempo():
    zona = pytz.timezone("America/Bogota")
    ahora = datetime.now(zona)
    return ahora.strftime("%Y-%m-%d %H:%M:%S")

# =========================
# NORMALIZACIÓN
# =========================
def incrementar_divisor():
    global DIVISOR_TENSION
    DIVISOR_TENSION += 20
    DIVISOR_TENSION2 += 20

def reducir_divisor():
    global DIVISOR_TENSION
    if DIVISOR_TENSION > 20:
        DIVISOR_TENSION -= 20
    else:
        print("Error Divisor 1 en rango minimo")

    if DIVISOR_TENSION2 > 20:
        DIVISOR_TENSION2 -= 20
    else:
        print("Error Divisor 2 en rango minimo")

def normalize(signal, protocolo = 1):
    signal = np.array(signal)
    
    if protocolo == 1:
        signal = (signal - np.mean(signal)) / DIVISOR_TENSION # np.std(signal)
    else:
        signal = (signal - np.mean(signal)) / DIVISOR_TENSION2 # np.std(signal)
    
    return signal

# =========================
# FRECUENCIA CARDIACA
# =========================
def compute_hr(signal):
    try:
        ecg_signals, info = nk.ecg_process(signal, sampling_rate=FS)

        average_hr = ecg_signals["ECG_Rate"]

    except:
        return -1
    return average_hr[1]

def compute_avr_hr(signal):
    try:
        ecg_signals, info = nk.ecg_process(signal, sampling_rate=FS)

        average_hr = ecg_signals["ECG_Rate"]

    except:
        return -1
    
    cont = 0
    acum = 0
    for time_rr in average_hr:
        acum += float(time_rr)
        cont += 1


    return acum / cont

# ========================
# ANALISIS DEL ECG
#=========================

def calculate_qrs(ecg_signal):
    """
    Calculate QRS durations from a normalized ECG signal.

    Parameters:
        ecg_signal (np.array): Normalized ECG signal (-1 to 1)
        sampling_rate (int): Sampling rate in Hz

    Returns:
        
        intervalo QRS minimo in milisegundos
        promedio intervalos QRS em milisegundos
        intervalo QRS maximo in milisegundos
    """
    ecg, info = nk.ecg_process(ecg_signal, sampling_rate=FS)

    results, waves = nk.ecg_delineate(ecg, info["ECG_R_Peaks"], 
                                    sampling_rate=FS, 
                                    show=False)

    qrs_onsets = waves['ECG_Q_Peaks']
    qrs_offsets = waves['ECG_S_Peaks']

    qrs_durations = (np.array(qrs_offsets) - np.array(qrs_onsets)) / FS

    # print("QRS Durations (seconds):", qrs_durations) #linea de prueba

    avr = np.nanmean(qrs_durations) * 1000
    qrs_max = 0
    qrs_min = 10000000000

    for times in qrs_durations:
        ftimes = times.astype(float) * 1000
        if ftimes < qrs_min:
            qrs_min = ftimes
        if ftimes > qrs_max:
            qrs_max = ftimes


    
    return qrs_min.round(2), avr.round(2), qrs_max.round(2)

# =========================
# EXPORTAR PDF
# =========================

def export_pdf():
    
    global FILE_NAME
    global PACIENTE
    global RUTA

    archivo = RUTA + FILE_NAME

    if len(ecg_buffer) < buffer_size:
        return
    
    buffer_list = list(ecg_buffer)
    # buffer_list = buffer_list[-3600]  #da error ???

    signal = normalize(buffer_list, 2)
    cleaned = nk.ecg_clean(signal, sampling_rate=FS, method='neurokit')

    # Tiempo real (10 s)
    time = np.linspace(0, BUFFER_SECONDS, len(signal))

    fig, ax = plt.subplots(figsize=(12, 4))

    # =========================
    # ECG GRID (ROJO)
    # =========================

    # Límites
    ax.set_xlim(0, BUFFER_SECONDS)
    ax.set_ylim(-3, 3)

    # Cuadros pequeños (0.04 s)
    small_x = 0.04
    small_y = 0.1

    # Cuadros grandes (0.2 s)
    big_x = 0.2
    big_y = 0.5

    # Líneas verticales pequeñas
    for x in np.arange(0, BUFFER_SECONDS, small_x):
        ax.axvline(x, color='#ffcccc', linewidth=0.5)

    # Líneas verticales grandes
    for x in np.arange(0, BUFFER_SECONDS, big_x):
        ax.axvline(x, color='#ff6666', linewidth=1)

    # Líneas horizontales pequeñas
    for y in np.arange(-2, 2, small_y):
        ax.axhline(y, color='#ffcccc', linewidth=0.5)

    # Líneas horizontales grandes
    for y in np.arange(-2, 2, big_y):
        ax.axhline(y, color='#ff6666', linewidth=1)

    # =========================
    # SEÑAL ECG
    # =========================
    ax.plot(time, cleaned, color='black', linewidth=1.2)

    # Quitar bordes y ticks
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title(f"ECG {PACIENTE} {obtener_tiempo()}", fontsize=12)


    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"PDF guardado como: {FILE_NAME}")


def report_pdf():
    global FILE_NAME
    global PACIENTE
    global RUTA

    archivo = RUTA + "Reporte" + FILE_NAME

    if len(ecg_buffer) < buffer_size:
        return

    signal = normalize(list(ecg_buffer), 2)
    cleaned = nk.ecg_clean(signal, sampling_rate=FS, method='neurokit')

    qrs_min, qrs_time_avr, qrs_max = calculate_qrs(signal)

    pulso = compute_avr_hr(signal)


    # Tiempo real (10 s)
    time = np.linspace(0, BUFFER_SECONDS, len(signal))

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.text(0.5, 1.1, f"Pulso: {pulso:.1f} bpm\nIntervalo QRS: {qrs_min}ms {qrs_time_avr}ms {qrs_max}ms")

    # =========================
    # ECG GRID (ROJO)
    # =========================

    # Límites
    ax.set_xlim(0, BUFFER_SECONDS)
    ax.set_ylim(-2, 2)

    # Cuadros pequeños (0.04 s)
    small_x = 0.04
    small_y = 0.1

    # Cuadros grandes (0.2 s)
    big_x = 0.2
    big_y = 0.5

    # Líneas verticales pequeñas
    for x in np.arange(0, BUFFER_SECONDS, small_x):
        ax.axvline(x, color='#ffcccc', linewidth=0.5)

    # Líneas verticales grandes
    for x in np.arange(0, BUFFER_SECONDS, big_x):
        ax.axvline(x, color='#ff6666', linewidth=1)

    # Líneas horizontales pequeñas
    for y in np.arange(-2, 2, small_y):
        ax.axhline(y, color='#ffcccc', linewidth=0.5)

    # Líneas horizontales grandes
    for y in np.arange(-2, 2, big_y):
        ax.axhline(y, color='#ff6666', linewidth=1)

    # =========================
    # SEÑAL ECG
    # =========================
    ax.plot(time, cleaned, color='black', linewidth=1.2)

    # Quitar bordes y ticks
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title(f"ECG {PACIENTE} {obtener_tiempo()}", fontsize=12)


    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"PDF guardado como: Reporte{FILE_NAME}")
    print(f"Pulso: {pulso} bpm\n intervalo QRS: {qrs_min}ms {qrs_time_avr}ms {qrs_max}")


def neurokit_analisis():
    if len(ecg_buffer) < buffer_size:
        return
    
    ekg = normalize(list(ecg_buffer))
    ecg = np.array(ekg)
    archivo = RUTA + "NK_ANALISIS_" + PACIENTE + ".pdf"

    # Process ECG with NeuroKit2
    signals, info = nk.ecg_process(ecg, sampling_rate=FS)

    # Plot using NeuroKit2 built-in plot
    nk.ecg_plot(signals, info)

    fig = plt.gcf() 
    fig.set_size_inches(10, 12, forward=True) 
    fig.savefig(archivo)

def full_analisis():
    try:
        neurokit_analisis()
        report_pdf()
        return True
    except:
        print("Error en creacion de reportes")
        return False

# =========================
# LOOP
# =========================
def update():
    global t
    global subtimer

    tiempo_subtimer = 3 #cambiar para recalcular la frecuencia cardiaca cada x segundos (default 3)
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
    # print(subtimer) #linea de prueba

    if len(ecg_buffer) > FS:

        signal = normalize(list(ecg_buffer))
        cleaned = nk.ecg_clean(signal, sampling_rate=FS)

        # curve.setData(signal)
        curve.setData(cleaned)

        # HR
        if len(signal) > hr_size and subtimer >= control_subtimer:
            hr_signal = signal[-hr_size:]

            hr = float(compute_hr(signal))

            hr_label.setText(f"HR: {hr:.1f} bpm")
            hr_label.setPos(len(signal)*0.7, max(signal))
            subtimer = 0

# =========================
# TECLADO
# =========================
def keyPressEvent(event):
    if event.text() == 'g':
        export_pdf()
    elif event.text() == 'r':
        report_pdf()
    elif event.text() == 'h':
        reducir_divisor()
    elif event.text() == 'l':
        incrementar_divisor()
    elif event.text() == 'f':
       full_analisis()

win.keyPressEvent = keyPressEvent

# =========================
# TIMER
# =========================
timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(10)

# =========================
# RUN
# =========================
if __name__ == '__main__':
    sys.exit(app.exec_())