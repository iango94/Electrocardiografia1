import numpy as np
import neurokit2 as nk
from collections import deque
from datetime import datetime
import pytz
import matplotlib.pyplot as plt

# ========================================================
# CONFIGURACIÓN GENERAL Y METADATOS
# ========================================================
FS = 360
BUFFER_SECONDS = 6
HR_WINDOW = 3

buffer_size = FS * BUFFER_SECONDS
hr_size = FS * HR_WINDOW

# NOTA: En la Raspberry Pi, cambia esta ruta a una local, por ejemplo: "/home/pi/ECG_Reports/"
RUTA = "C:\\Users\\Jacobo\\Documents\\proyectosActuales\\ECG\\ElectrosTomados\\"
paciente = "Paciente_Defecto"
file_name = f"ECG_{paciente}.pdf"

diagnostico = {'edad': 22, 'sexo': 'M'}
cuestionario = {

    # síntomas
    "dolor_torax": "",
    "dolor_intensidad": "",
    "duracion_dolor": "",
    "dolor_tipo": "",

    "dificultad_respirar": "",
    "sudoracion_fria": "",
    "nauseas": "",
    "vomito": "",
    "mareo": "",
    "sincope": "",

    # irradiación
    "dolor_mandibula": "",
    "dolor_cuello": "",
    "dolor_brazo_izquierdo": "",
    "dolor_brazo_derecho": "",
    "dolor_espalda": "",
    "dolor_epigastrio": "",

    # antecedentes
    "angina_diagnosticada": "",
    "infarto_previo": "",
    "stent_coronario": "",
    "cirugia_cardiaca": "",
    "arritmias": "",

    # factores riesgo
    "hipertension": "",
    "diabetes": "",
    "dislipidemia": "",
    "tabaquismo": "",
    "obesidad": "",
    "antecedentes_familiares": "",

    # contraindicaciones
    "alergia_ASA": "",
    "hemorragias_activas": "",
    "potenciadores_sex": ""
}

DIVISOR_TENSION = 600
NK_METHOD = 'neurokit'

SHOW_Q = True   
SHOW_R = True   
SHOW_S = True   
SHOW_J_POINT = True  # Activado para marcar el inicio del Segmento ST

ecg_buffer = deque(maxlen=buffer_size)

# ========================================================
# PROCESAMIENTO DIGITAL Y ADQUISICIÓN
# ========================================================
def obtener_tiempo():
    zona = pytz.timezone("America/Bogota")
    return datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S")

def normalize(signal):
    return ((np.array(signal) / DIVISOR_TENSION) * 3.3) - 1.65 

def filtrar_ECG(senal):
    return nk.ecg_clean(senal, sampling_rate=FS, method=NK_METHOD)

# ========================================================
# ALGORITMO MÉDICO: EVALUACIÓN DE ISQUEMIA (Árbol AHA / ESC)
# ========================================================
def analizar_criterios_isquemia(signal_clean, info_peaks):
    alertas = []
    probabilidad = "Baja / Normal"
    
    try:
        # Delinear sub-ondas usando Ondícula Discreta (DWT)
        _, waves = nk.ecg_delineate(signal_clean, info_peaks["ECG_R_Peaks"], sampling_rate=FS, method="dwt")
        
        r_offsets = waves['ECG_R_Offsets']  # El final del QRS = Punto J
        t_peaks = waves['ECG_T_Peaks']
        p_peaks = waves['ECG_P_Peaks']
        
        st_elevations = []
        st_slopes = []
        t_wave_amplitudes = []
        
        for i in range(len(info_peaks["ECG_R_Peaks"]) - 1):
            j_point_idx = r_offsets[i]
            t_peak_idx = t_peaks[i]
            
            if np.isnan(j_point_idx) or np.isnan(t_peak_idx):
                continue
                
            j_point_idx = int(j_point_idx)
            t_peak_idx = int(t_peak_idx)
            
            # Línea base fisiológica (Onda P)
            base_idx = int(info_peaks["ECG_R_Peaks"][i] - (0.05 * FS)) 
            if i < len(p_peaks) and not np.isnan(p_peaks[i]):
                base_idx = int(p_peaks[i])
            v_linea_base = signal_clean[base_idx]
            
            # Evaluación del ST a J + 60ms (21 muestras a 360Hz)
            st_sample_idx = min(j_point_idx + int(0.06 * FS), len(signal_clean) - 1)
            st_amplitude_mv = signal_clean[st_sample_idx] - v_linea_base
            st_elevations.append(st_amplitude_mv)
            
            # Pendiente del Segmento ST
            slope = (signal_clean[st_sample_idx] - signal_clean[j_point_idx]) / (st_sample_idx - j_point_idx)
            st_slopes.append(slope)
            
            # Amplitud Onda T
            t_amp_mv = signal_clean[t_peak_idx] - v_linea_base
            t_wave_amplitudes.append(t_amp_mv)
            
        if len(st_elevations) == 0:
            return "Datos insuficientes", ["Muestras inestables en el buffer."], []

        avg_st_elevation = np.nanmean(st_elevations)
        avg_st_slope = np.nanmean(st_slopes)
        avg_t_amplitude = np.nanmean(t_wave_amplitudes)
        
        # Conversión médica estricta: 0.1 mV = 1 mm
        st_mm = avg_st_elevation * 10.0 
        t_mm = avg_t_amplitude * 10.0

        # --- ÁRBOL DE DECISIÓN LÓGICA ---
        if t_mm > 8.0:
            alertas.append("Ondas T hiperagudas (Sugerente de Isquemia Temprana)")
            probabilidad = "EXTREMA"
            
        if st_mm >= 1.0:
            alertas.append(f"Elevación franca del segmento ST ({st_mm:.2f} mm). Alerta IAMCEST.")
            probabilidad = "EXTREMA" if probabilidad == "EXTREMA" else "ALTA"
        elif st_mm <= -0.5:
            alertas.append(f"Depresión del segmento ST ({abs(st_mm):.2f} mm). Alerta IAMSEST.")
            probabilidad = "EXTREMA" if probabilidad == "EXTREMA" else "ALTA"
            
        if t_mm < -2.0:
            alertas.append("Inversión profunda de onda T (Isquemia evolucionada).")
            if probabilidad == "Baja / Normal": probabilidad = "ALTA"

        if (0.5 > st_mm > 0.2) and avg_st_slope < 0:
            alertas.append("Desviación menor del ST con pendiente negativa.")
            if probabilidad == "Baja / Normal": probabilidad = "MEDIA"

    except Exception as e:
        alertas.append(f"Error analítico: {str(e)}")
        return "Error", alertas, []
        
    return probabilidad, alertas, r_offsets

# ========================================================
# GENERACIÓN DE INFORME CLÍNICO PDF
# ========================================================
def report_pdf():
    global file_name, paciente, RUTA
    archivo = RUTA + "Reporte_" + file_name

    if len(ecg_buffer) < buffer_size:
        return False, "Buffer insuficiente"

    signal = normalize(list(ecg_buffer))
    cleaned = filtrar_ECG(signal)

    # Detección de picos R
    _, info = nk.ecg_peaks(cleaned, sampling_rate=FS)
    
    # Procesar diagnóstico inteligente
    prob_medica, lista_alertas, j_points = analizar_criterios_isquemia(cleaned, info)
    
    # Calcular Ritmo Cardíaco promedio
    try:
        signals_processed, _ = nk.ecg_process(signal, sampling_rate=FS)
        pulso = np.nanmean(signals_processed["ECG_Rate"])
    except:
        pulso = (len(info["ECG_R_Peaks"]) / BUFFER_SECONDS) * 60.0

    # Construir Gráfica de Reporte
    fig, ax = plt.subplots(figsize=(11, 5))
    
    sex_str = 'Masculino' if diagnostico['sexo'] == 'M' else 'Femenino'
    info_paciente = f"Paciente: {paciente} | Edad: {diagnostico['edad']} años | Sexo: {sex_str}\nFecha/Hora: {obtener_tiempo()}"
    info_clinica = f"Frecuencia Cardíaca: {pulso:.1f} BPM\nPROBABILIDAD ISQUÉMICA: {prob_medica}"
    
    ax.text(0.1, 2.4, info_paciente, fontsize=9, fontweight='bold')
    ax.text(3.8, 2.4, info_clinica, fontsize=10, color='red' if prob_medica in ['ALTA','EXTREMA'] else 'black', fontweight='bold')
    
    txt_alertas = "Hallazgos clínicos:\n" + ("\n".join(lista_alertas) if lista_alertas else "- Parámetros ST y Onda T estables bajo criterios AHA.")
    ax.text(0.1, -2.8, txt_alertas, fontsize=9, color='darkred' if lista_alertas else 'green')

    # Cuadrícula electrocardiográfica
    ax.set_xlim(0, BUFFER_SECONDS)
    ax.set_ylim(-3, 3)
    for x in np.arange(0, BUFFER_SECONDS, 0.04): ax.axvline(x, color='#ffcccc', linewidth=0.4)
    for x in np.arange(0, BUFFER_SECONDS, 0.2): ax.axvline(x, color='#ff6666', linewidth=0.8)
    for y in np.arange(-2, 2, 0.1): ax.axhline(y, color='#ffcccc', linewidth=0.4)
    for y in np.arange(-2, 2, 0.5): ax.axhline(y, color='#ff6666', linewidth=0.8)

    time_axis = np.linspace(0, BUFFER_SECONDS, len(cleaned))
    ax.plot(time_axis, cleaned, color='black', linewidth=1.2)

    # Dibujar puntos diagnósticos sobre el PDF
    if SHOW_R and len(info["ECG_R_Peaks"]) > 0:
        ax.scatter(np.array(info["ECG_R_Peaks"])/FS, cleaned[info["ECG_R_Peaks"]], color='orange', s=20, zorder=5)
    if SHOW_J_POINT and len(j_points) > 0:
        j_points_clean = [int(x) for x in j_points if not np.isnan(x)]
        ax.scatter(np.array(j_points_clean)/FS, cleaned[j_points_clean], color='cyan', s=25, marker='X', zorder=5)

    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)

    plt.savefig(archivo, dpi=300, bbox_inches='tight')
    plt.close()
    
    res_resumen = f"Ritmo: {pulso:.1f} BPM | Estado: {prob_medica}"
    return True, res_resumen
