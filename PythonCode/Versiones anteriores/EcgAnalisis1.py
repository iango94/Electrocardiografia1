import sys
import numpy as np
import serial
import neurokit2 as nk
from collections import deque
from scipy.signal import butter, sosfiltfilt
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import matplotlib.pyplot as plt
import matplotlib.backends
from datetime import datetime
import pytz

# =========================
# CONFIG
# =========================

# Puerto serie
PORT = 'COM5'
BAUD = 115200

# Electrocardiografo 
FS = 360
RESOLUCION = [0,1023]
GANANCIA = 1000 

# Tiempos de conjuntos de muestra
BUFFER_SECONDS = 6
HR_WINDOW = 3

buffer_size = FS * BUFFER_SECONDS
hr_size = FS * HR_WINDOW

# Archivos de salida
RUTA = "C:\\Users\\Jacobo\\Documents\\proyectosActuales\\ECG\\ElectrosTomados\\"

paciente = input("Digite nombre paciente: ")
file_name = "ECG_" + paciente + ".pdf"

SHOW_Q = True   # Marcar pico onda Q
SHOW_R = True   # Marcar pico onda R
SHOW_S = True   # Marcar pico onda S
SHOW_R_ON = True
SHOW_R_OF = True

# Info para diagnostico
diagnostico = dict()

aux = int(input("Digite edad paciente (años): "))
diagnostico.update({'edad':aux})

aux = input("Digite sexo biologico paciente (F - M): ")
aux = 'F' if (aux == 'f' or aux =='F') else 'M'
diagnostico.update({'sexo':aux})


print(f"presione:\n 'g' para guardar instantanea\n 'r' para guardar instantanea con reporte\n 'h' para incrementar amplitud \n 'l' para reducir amplitud")

DIVISOR_TENSION = 1023
NK_METHOD = 'neurokit'

# =========================
# Variables ECG procesado
# =========================
nk_ECG_dataframe = None
nk_ECG_info = None
nk_ECG_error = None

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
plot.setYRange(-2, 2)
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

def reducir_divisor():
    global DIVISOR_TENSION
    DIVISOR_TENSION -= 20

def normalize(signal):
    signal = np.array(signal)
    signal = ((signal / DIVISOR_TENSION) * 3.3) - 1.65 # np.std(signal)
    return signal

# =========================
# FILTRADO
# =========================
CORTE_BAJO = 0.5
CORTE_ALTO = 150
FR_RED = 60
ORDEN_FILTRO = 4

def filtrar_ECG(senal, modo = 1):
    match modo:
        case 1:
            return nk.ecg_clean(senal, sampling_rate=FS)
        
        case 2:
            return nk.ecg_clean(senal, sampling_rate=FS)
        
        case 3:
            sos_pasabanda = butter(
                N = ORDEN_FILTRO, 
                Wn =[CORTE_BAJO, CORTE_ALTO],
                fs = 360,
                btype = 'band',
                output = 'sos'
                )
            prefiltrado = sosfiltfilt(sos_pasabanda, senal)

            sos_notch = butter(
                N = ORDEN_FILTRO, 
                Wn = [(FR_RED-5), (FR_RED+5)],
                fs=360,
                btype='bandstop',
                output='sos'
                )
            return sosfiltfilt(sos_notch, senal)
        case _:
            print("Error: modo de filtrado incorrecto")
            return


# ============================
# NEUROKIT2 ANALISIS FUCTIONS
# ============================

def procesar_ecg(signal):
    global nk_ECG_dataframe
    global nk_ECG_info

    try:
        nk_ECG_dataframe, nk_ECG_info = nk.ecg_process(signal, sampling_rate=FS)
    except Exception as e:
        nk_ECG_dataframe = None
        nk_ECG_info = None
        nk_ECG_error = e    


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
    Calculate QRS durations from a ECG signal in mV.

    Parameters:
        ecg_signal (np.array): ECG signal in mV 

    Returns:
        
        intervalo QRS minimo in milisegundos
        promedio intervalos QRS em milisegundos
        intervalo QRS maximo in milisegundos
    """
    ecg, info = nk.ecg_process(ecg_signal, sampling_rate=FS)

    #metodo con los picos de las ondas Q y S (aveces detecta mal la S dando intervalos muy largos) cambiar a true para ejecutar este metodo
    if False:
        _, waves = nk.ecg_delineate(ecg, info["ECG_R_Peaks"], 
                                        sampling_rate=FS, 
                                        show=False)

        qrs_onsets = waves['ECG_Q_Peaks']
        qrs_offsets = waves['ECG_S_Peaks']
    else:
        _, waves = nk.ecg_delineate(ecg, info["ECG_R_Peaks"], 
                                        sampling_rate=FS, 
                                        show=False, 
                                        method="dwt")

        qrs_onsets = waves['ECG_R_Onsets']
        qrs_offsets = waves['ECG_R_Offsets']

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


    qrs_peaks = [info['ECG_Q_Peaks'], info['ECG_R_Peaks'] ,info['ECG_S_Peaks']]
    qrs_times = [qrs_min.round(2), avr.round(2), qrs_max.round(2)]
    qrs_ons_offs = [waves['ECG_R_Onsets'], waves['ECG_R_Offsets']]

    if qrs_times[1] < 120:
        analisis = "QRS normal"
    else:
        analisis = "QRS ancho"

    return qrs_times, qrs_peaks, qrs_ons_offs, analisis

# =========================
# EXPORTAR PDF
# =========================

def export_pdf():
    
    global file_name
    global paciente
    global RUTA

    archivo = RUTA + file_name

    if len(ecg_buffer) < buffer_size:
        return
    
    buffer_list = list(ecg_buffer)
    # buffer_list = buffer_list[-3600]  #da error ???

    signal = normalize(buffer_list)
    cleaned = nk.ecg_clean(signal, sampling_rate=FS, method=NK_METHOD)

    # Tiempo real (6 s)
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

    plt.title(f"ECG {paciente} {obtener_tiempo()}", fontsize=12)


    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"PDF guardado como: {file_name}")


def report_pdf():
    global file_name
    global paciente
    global RUTA

    archivo = RUTA + "Reporte" + file_name

    analisis = []

    if len(ecg_buffer) < buffer_size:
        print("Buffer muy corto, no se pudo realizar reporte")
        return

    signal = normalize(list(ecg_buffer))
    cleaned = nk.ecg_clean(signal, sampling_rate=FS, method='neurokit')

    qrs_times, qrs_peaks, qrs_ons_offs, qrs_analisis = calculate_qrs(signal)
    analisis.append(qrs_analisis)

    pulso = compute_avr_hr(signal)


    # Tiempo real (10 s)
    time = np.linspace(0, BUFFER_SECONDS, len(signal))

    fig, ax = plt.subplots(figsize=(12, 3))


    # Texto dentro del ECG (identificacion, overview, interpretacion) 
    if diagnostico['sexo'] == 'M':
        sex = 'Masculino'
    elif diagnostico['sexo'] == 'F':
        sex = 'Femenino'
    else:
        sex = ""

    ax.text(
        0.5, 
        1.2, 
        f"Nombre: {paciente}\nEdad: {diagnostico['edad']}\nSexo: {sex}" 
    )
    ax.text(
        2.0, 
        1.2, 
        f"Pulso: {pulso:.1f} bpm\nInt. QRS promedio: {qrs_times[1]}ms"
    )

    interpretacion = "\n".join(analisis)
    ax.text(
        3.5, 
        1.5, 
        interpretacion
    )

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

    # mostrar picos QRS
    if SHOW_Q:
        alturas = [(float(cleaned[k])-0.04) for k in qrs_peaks[0]]
        q_pks = [k/FS for k in [int(r) for r in qrs_peaks[0]]] 
        ax.scatter(q_pks, alturas, color='red', s=5, zorder=5)
    
    if SHOW_R:
        alturas = [(float(cleaned[k])+0.04) for k in qrs_peaks[1]]
        r_pks = [k/FS for k in [int(r) for r in qrs_peaks[1]]] 
        ax.scatter(r_pks, alturas, color='yellow', s=5, zorder=5)

    if SHOW_S:
        alturas = [(float(cleaned[k])-0.04) for k in qrs_peaks[2]]
        s_pks = [k/FS for k in [int(r) for r in qrs_peaks[2]]] 
        ax.scatter(s_pks, alturas, color='blue', s=5, zorder=5)

    #mostrar R onsets y offsets
    if SHOW_R_ON:
        for ri in qrs_ons_offs[0]:
            if not np.isnan(ri):
                plt.axvline(float(ri)/FS, color='green', linestyle='--')
    if SHOW_R_OF:
        for rf in qrs_ons_offs[1]:
            if not np.isnan(rf):
                plt.axvline(float(rf)/FS, color='blue', linestyle='--')
    print(q_pks, alturas)

    # Quitar bordes y ticks
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.title(f"ECG {paciente} {obtener_tiempo()}", fontsize=12)


    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"PDF guardado como: Reporte{file_name}")
    print(f"Pulso: {pulso} bpm\n intervalo QRS: {qrs_times[0]}ms {qrs_times[1]}ms {qrs_times[2]}")


def neurokit_analisis():
    if len(ecg_buffer) < buffer_size:
        return
    
    ekg = normalize(list(ecg_buffer))
    ecg = np.array(ekg)
    archivo = RUTA + "NK_ANALISIS_" + paciente + ".pdf"

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
        #cleaned = nk.ecg_clean(signal, sampling_rate=FS)
        cleaned = filtrar_ECG(signal) 

        # Eliminar distorsion del filtro al inicio y final?
        #cleaned = cleaned[360:]
        #cleaned = cleaned[:-360]

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