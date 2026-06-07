import numpy as np
import neurokit2 as nk
from collections import deque
from scipy.signal import butter, sosfiltfilt
from datetime import datetime
import pytz
import matplotlib.pyplot as plt

FS = 360
RESOLUCION = [0, 1023]
GANANCIA = 1000 

BUFFER_SECONDS = 6
HR_WINDOW = 3
buffer_size = FS * BUFFER_SECONDS
hr_size = FS * HR_WINDOW

DIVISOR_TENSION = 1023
NK_METHOD = 'neurokit'

# Búferes circulares de datos
ecg_buffer = deque(maxlen=buffer_size)
time_buffer = deque(maxlen=buffer_size)

# Parámetros de filtrado
CORTE_BAJO = 0.5
CORTE_ALTO = 150
FR_RED = 60
ORDEN_FILTRO = 4

# Variables del paciente compartidas con la interfaz
paciente = "PresentacionClase"
file_name = f"ECG_{paciente}.pdf"
RUTA = "C:\\Users\\Jacobo\\Documents\\proyectosActuales\\ECG\\ElectrosTomados\\"
diagnostico = {'edad': 20, 'sexo': 'M'}

SHOW_Q = True    
SHOW_R = True    
SHOW_S = True    
SHOW_R_ON = True
SHOW_R_OF = True

def obtener_tiempo():
    zona = pytz.timezone("America/Bogota")
    ahora = datetime.now(zona)
    return ahora.strftime("%Y-%m-%d %H:%M:%S")

def incrementar_divisor():
    global DIVISOR_TENSION
    DIVISOR_TENSION += 20
    return DIVISOR_TENSION

def reducir_divisor():
    global DIVISOR_TENSION
    DIVISOR_TENSION -= 20
    return DIVISOR_TENSION

def normalize(signal):
    signal = np.array(signal)
    return ((signal / DIVISOR_TENSION) * 3.3) - 1.65 

def filtrar_ECG(senal, modo=3):
    if modo == 3:
        # Filtro Butterworth Pasa-banda
        sos_pasabanda = butter(N=ORDEN_FILTRO, Wn=[CORTE_BAJO, CORTE_ALTO], fs=FS, btype='band', output='sos')
        prefiltrado = sosfiltfilt(sos_pasabanda, senal)
        # Filtro Notch (Eliminación de la red eléctrica 60 Hz)
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
    exceptException as e:
        return [0,0,0], [[],[],[]], [[],[]], "Error análisis"

def export_pdf():
    global file_name, paciente, RUTA
    archivo = RUTA + file_name
    if len(ecg_buffer) < buffer_size: return False
    
    signal = normalize(list(ecg_buffer))
    cleaned = filtrar_ECG(signal)
    time = np.linspace(0, BUFFER_SECONDS, len(signal))
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_xlim(0, BUFFER_SECONDS)
    ax.set_ylim(-3, 3)
    
    # Cuadrícula milimetrada clásica de ECG
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
    return True

def report_pdf():
    global file_name, paciente, RUTA
    archivo = RUTA + "Reporte" + file_name
    if len(ecg_buffer) < buffer_size: return False

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

    # Marcado de ondas sobreimpresas
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
    return f"Pulso: {pulso:.1f} bpm | QRS: {qrs_times[1]}ms ({qrs_analisis})"

def neurokit_analisis():
    if len(ecg_buffer) < buffer_size: return False
    ekg = normalize(list(ecg_buffer))
    archivo = RUTA + "NK_ANALISIS_" + paciente + ".pdf"
    signals, info = nk.ecg_process(np.array(ekg), sampling_rate=FS)
    nk.ecg_plot(signals, info)
    fig = plt.gcf()
    fig.set_size_inches(10, 12, forward=True)
    fig.savefig(archivo)
    plt.close()
    return True

def full_analisis():
    try:
        neurokit_analisis()
        msg = report_pdf()
        return True, msg
    except:
        return False, "Error al generar reportes integrados."
