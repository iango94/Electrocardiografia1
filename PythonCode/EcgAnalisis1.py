import numpy as np
import neurokit2 as nk
from collections import deque
from scipy.signal import butter, sosfiltfilt
from datetime import datetime
import pytz
import matplotlib.pyplot as plt

# Configuración de Hardware
FS = 360
buffer_size = FS * 6
hr_size = FS * 3

DIVISOR_TENSION = 1023
ecg_buffer = deque(maxlen=buffer_size)

# Variables del Paciente
paciente = "Paciente_Raspberry"
file_name = f"ECG_{paciente}.pdf"
# Nota: Cambia esta ruta a una carpeta válida en tu Raspberry Pi (ej. "/home/pi/Documents/")
RUTA = "C:\\Users\\Jacobo\\Documents\\proyectosActuales\\ECG\\ElectrosTomados\\"
diagnostico = {'edad': 20, 'sexo': 'M'}

def obtener_tiempo():
    zona = pytz.timezone("America/Bogota")
    return datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")

def normalize(signal):
    return ((np.array(signal) / DIVISOR_TENSION) * 3.3) - 1.65 

def filtrar_ECG(senal):
    # Filtro Butterworth Pasa-banda (0.5 - 150 Hz) + Notch (60 Hz) para quitar ruido de cables
    sos_pasabanda = butter(4, [0.5, 150], fs=FS, btype='band', output='sos')
    prefiltrado = sosfiltfilt(sos_pasabanda, senal)
    sos_notch = butter(4, [55, 65], fs=FS, btype='bandstop', output='sos')
    return sosfiltfilt(sos_notch, prefiltrado)

def compute_hr(signal):
    try:
        ecg_signals, _ = nk.ecg_process(signal, sampling_rate=FS)
        return ecg_signals["ECG_Rate"][1]
    except:
        return -1

def report_pdf():
    global file_name, paciente, RUTA
    archivo = RUTA + "Reporte_" + file_name
    if len(ecg_buffer) < buffer_size: return False

    signal = normalize(list(ecg_buffer))
    cleaned = filtrar_ECG(signal)
    time = np.linspace(0, 6, len(signal))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_xlim(0, 6)
    ax.set_ylim(-2, 2)
    
    # Cuadrícula roja de papel milimetrado para ECG
    for x in np.arange(0, 6, 0.04): ax.axvline(x, color='#ffcccc', linewidth=0.5)
    for x in np.arange(0, 6, 0.2): ax.axvline(x, color='#ff6666', linewidth=1)
    for y in np.arange(-2, 2, 0.1): ax.axhline(y, color='#ffcccc', linewidth=0.5)
    for y in np.arange(-2, 2, 0.5): ax.axhline(y, color='#ff6666', linewidth=1)
    
    ax.plot(time, cleaned, color='black', linewidth=1.2)
    ax.set_xticks([]); ax.set_yticks([])
    plt.title(f"ECG: {paciente} - {obtener_tiempo()}")
    plt.savefig(archivo, dpi=200, bbox_inches='tight')
    plt.close()
    return True
