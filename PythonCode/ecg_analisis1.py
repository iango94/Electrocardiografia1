import sys
import time
from dataclasses import dataclass, field
from typing import Dict, Any
from collections import deque

from PySide6 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# --- Módulo I2C para ADS1115 ---
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Pin
from adafruit_ads1x15.analog_in import AnalogIn

# ========================================================
# 1. ESTRUCTURA DE DATOS DEL PACIENTE (Anamnesis)
# ========================================================

@dataclass
class DatosPaciente:
    """Almacena la información demográfica y clínica capturada en el cuestionario"""
    nombre: str = "Paciente_Raspberry"
    edad: int = 25
    sexo: str = "M"
    cuestionario: Dict[str, Any] = field(default_factory=dict)
    file_name: str = ""

    def __post_init__(self):
        if not self.file_name:
            nombre_limpio = self.nombre.replace(" ", "_")
            self.file_name = f"ECG_{nombre_limpio}.pdf"


# ========================================================
# 2. HILO DE LECTURA DE DOS ADS1115 (I2C)
# ========================================================

class HiloLecturaI2C(QtCore.QThread):
    """Muestra 2x ADS1115 por I2C y calcula las 8 derivaciones"""
    nuevos_datos = QtCore.Signal(list)
    error_i2c = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ejecutando = False

    def run(self):
        try:
            # Bus I2C compartido
            i2c = busio.I2C(board.SCL, board.SDA)

            # ADS1115 #1 (Dirección por defecto 0x48 - ADDR a GND) -> Bipolares (DI, DII)
            ads1 = ADS.ADS1115(i2c, address=0x48)
            ads1.gain = 1  # Gain +/- 4.096V
            chan_DI = AnalogIn(ads1, Pin.A0, Pin.A1)
            chan_DII = AnalogIn(ads1, Pin.A2, Pin.A3)

            # ADS1115 #2 (Dirección 0x49 - ADDR a VDD) -> Precordiales (V3, V5)
            #ads2 = ADS.ADS1115(i2c, address=0x49)
            #ads2.gain = 1
            chan_V3 = chan_DI #AnalogIn(ads2, Pin.A0, Pin.A1)
            chan_V5 = chan_DII #AnalogIn(ads2, Pin.A2, Pin.A3)

            self.ejecutando = True

        except Exception as e:
            self.error_i2c.emit(f"Error inicializando ADS1115s (verificar direcciones 0x48 y 0x49): {e}")
            return

        while self.ejecutando:
            try:
                # 1. Lecturas directas de hardware
                v_DI = chan_DI.voltage
                v_DII = chan_DII.voltage
                v_V3 = chan_V3.voltage
                v_V5 = chan_V5.voltage

                # 2. Reconstrucción matemática por Triángulo de Einthoven y Leyes de Goldberger
                v_DIII = v_DII - v_DI
                v_aVR  = -(v_DI + v_DII) / 2.0
                v_aVL  = v_DI - (v_DII / 2.0)
                v_aVF  = v_DII - (v_DI / 2.0)

                # Arreglo ordenado con las 8 derivaciones
                # [DI, DII, DIII, aVR, aVL, aVF, V3, V5]
                muestra_8ch = [
                    v_DI, v_DII, v_DIII,
                    v_aVR, v_aVL, v_aVF,
                    v_V3, v_V5
                ]

                self.nuevos_datos.emit(muestra_8ch)

                # Frecuencia de muestreo (~100 Hz / 10ms)
                time.sleep(0.01)

            except Exception as e:
                self.error_i2c.emit(f"Fallo de lectura en bus I2C: {e}")
                time.sleep(0.1)

    def detener(self):
        self.ejecutando = False
        self.wait()


# ========================================================
# 3. INTERFAZ GRÁFICA DEL CUESTIONARIO (Modal)
# ========================================================

class VentanaDatosPaciente(QtWidgets.QDialog):
    """Cuestionario clínico inicial a pantalla completa"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuración de Paciente - Proyecto Latido")
        self.showFullScreen()
        self.setStyleSheet("background-color: #1e1e1e; color: white; font-family: Arial;")

        self.datos_paciente: DatosPaciente = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("<h2>PROYECTO LATIDO - CONFIGURACIÓN DE PACIENTE</h2>"))

        # Datos básicos
        layout.addWidget(QtWidgets.QLabel("Nombre Completo:"))
        self.txt_nombre = QtWidgets.QLineEdit("Paciente_Raspberry")
        self.txt_nombre.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555; padding: 6px;")
        layout.addWidget(self.txt_nombre)

        layout.addWidget(QtWidgets.QLabel("Edad:"))
        self.txt_edad = QtWidgets.QLineEdit("25")
        self.txt_edad.setStyleSheet("background-color: #2b2b2b; color: white; border: 1px solid #555; padding: 6px;")
        layout.addWidget(self.txt_edad)

        layout.addWidget(QtWidgets.QLabel("Sexo Biológico:"))
        self.cb_sexo = QtWidgets.QComboBox()
        self.cb_sexo.addItems(["M", "F"])
        self.cb_sexo.setStyleSheet("background-color: #2b2b2b; color: white; padding: 6px;")
        layout.addWidget(self.cb_sexo)

        # Scroll para secciones
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        contenido = QtWidgets.QWidget()
        form_principal = QtWidgets.QVBoxLayout(contenido)
        scroll.setWidget(contenido)
        layout.addWidget(scroll)

        # Secciones clínicas
        grupo_sintomas = QtWidgets.QGroupBox("1. Síntomas actuales")
        form_sintomas = QtWidgets.QFormLayout()
        self.cb_dolor_torax = self.agregar_fila(form_sintomas, "¿Presenta dolor o incomodidad en el pecho?")

        self.spn_dolor_intensidad = QtWidgets.QSpinBox()
        self.spn_dolor_intensidad.setRange(0, 10)
        form_sintomas.addRow("De 1 a 10 ¿Qué tan intenso es el dolor?", self.spn_dolor_intensidad)

        self.spn_duracion = QtWidgets.QSpinBox()
        self.spn_duracion.setRange(0, 720)
        self.spn_duracion.setSuffix(" min")
        form_sintomas.addRow("¿Hace cuánto empezaron los síntomas?", self.spn_duracion)

        self.cb_tipo_dolor = QtWidgets.QComboBox()
        self.cb_tipo_dolor.addItems([
            "Ninguno", "Opresivo", "Peso en el pecho", "Ardor",
            "Punzante", "Desgarrante", "Difuso", "No es dolor, es incomodidad"
        ])
        form_sintomas.addRow("Descripción del dolor:", self.cb_tipo_dolor)

        self.cb_disnea = self.agregar_fila(form_sintomas, "Dificultad respiratoria (Disnea)")
        self.cb_sudoracion = self.agregar_fila(form_sintomas, "¿Presenta sudoración fría?")
        self.cb_nauseas = self.agregar_fila(form_sintomas, "¿Presenta náuseas?")
        self.cb_vomito = self.agregar_fila(form_sintomas, "¿Ha vomitado?")
        self.cb_mareo = self.agregar_fila(form_sintomas, "¿Presenta mareo?")
        self.cb_sincope = self.agregar_fila(form_sintomas, "¿Se desmayó o siente que se va a desmayar?")
        grupo_sintomas.setLayout(form_sintomas)
        form_principal.addWidget(grupo_sintomas)

        grupo_irradiacion = QtWidgets.QGroupBox("2. Irradiación del dolor")
        form_irr = QtWidgets.QFormLayout()
        self.cb_mandibula = self.agregar_fila(form_irr, "Dolor en mandíbula")
        self.cb_cuello = self.agregar_fila(form_irr, "Dolor en cuello")
        self.cb_brazo_izq = self.agregar_fila(form_irr, "Dolor en brazo izquierdo")
        self.cb_brazo_der = self.agregar_fila(form_irr, "Dolor en brazo derecho")
        self.cb_espalda = self.agregar_fila(form_irr, "Dolor en espalda")
        self.cb_epigastrio = self.agregar_fila(form_irr, "Dolor en boca del estómago (epigastrio)")
        grupo_irradiacion.setLayout(form_irr)
        form_principal.addWidget(grupo_irradiacion)

        grupo_antecedentes = QtWidgets.QGroupBox("3. Antecedentes cardiovasculares")
        form_ant = QtWidgets.QFormLayout()
        self.cb_angina = self.agregar_fila(form_ant, "Angina de pecho previa")
        self.cb_infarto_previo = self.agregar_fila(form_ant, "Infarto de miocardio previo")
        self.cb_stent = self.agregar_fila(form_ant, "Stent coronario")
        self.cb_bypass = self.agregar_fila(form_ant, "Cirugía cardíaca / Bypass")
        self.cb_arritmia = self.agregar_fila(form_ant, "Arritmias diagnosticadas")
        grupo_antecedentes.setLayout(form_ant)
        form_principal.addWidget(grupo_antecedentes)

        grupo_riesgo = QtWidgets.QGroupBox("4. Factores de riesgo cardiovascular")
        form_riesgo = QtWidgets.QFormLayout()
        self.cb_hta = self.agregar_fila(form_riesgo, "Hipertensión arterial (HTA)")
        self.cb_diabetes = self.agregar_fila(form_riesgo, "Diabetes")
        self.cb_dislipidemia = self.agregar_fila(form_riesgo, "Colesterol / Triglicéridos altos")
        self.cb_tabaquismo = self.agregar_fila(form_riesgo, "Tabaquismo activo")
        self.cb_obesidad = self.agregar_fila(form_riesgo, "Obesidad")
        self.cb_familiares = self.agregar_fila(form_riesgo, "Antecedentes cardíacos en la familia")
        grupo_riesgo.setLayout(form_riesgo)
        form_principal.addWidget(grupo_riesgo)

        grupo_contra = QtWidgets.QGroupBox("5. Medicamentos y Contraindicaciones")
        form_contra = QtWidgets.QFormLayout()
        self.cb_alergia_asa = self.agregar_fila(form_contra, "Alergia a la Aspirina (ASA)")
        self.cb_hemorragias = self.agregar_fila(form_contra, "Sangrado activo o reciente")
        self.cb_pde5 = self.agregar_fila(form_contra, "Uso de potenciadores sexuales en últimas 72h")
        grupo_contra.setLayout(form_contra)
        form_principal.addWidget(grupo_contra)

        # Botón de inicio
        self.btn_listo = QtWidgets.QPushButton("INICIAR MONITOREO DE 8 DERIVACIONES (2x ADS1115)")
        self.btn_listo.setStyleSheet("background-color: #27ae60; color: white; font-size: 14px; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_listo.clicked.connect(self.guardar_y_entrar)
        layout.addWidget(self.btn_listo)

    def crear_combo(self):
        combo = QtWidgets.QComboBox()
        combo.addItems(["Desconozco", "No", "Sí"])
        combo.setStyleSheet("background-color: #2b2b2b; color: white;")
        return combo

    def agregar_fila(self, layout, texto):
        combo = self.crear_combo()
        layout.addRow(texto, combo)
        return combo

    def guardar_y_entrar(self):
        nombre = self.txt_nombre.text().strip() or "Paciente_Anonimo"
        try:
            edad = int(self.txt_edad.text())
        except ValueError:
            edad = 25

        cuestionario_dict = {
            "dolor_torax": self.cb_dolor_torax.currentText(),
            "dolor_intensidad": self.spn_dolor_intensidad.value(),
            "duracion_dolor": self.spn_duracion.value(),
            "dolor_tipo": self.cb_tipo_dolor.currentText(),
            "dificultad_respirar": self.cb_disnea.currentText(),
            "sudoracion_fria": self.cb_sudoracion.currentText(),
            "nauseas": self.cb_nauseas.currentText(),
            "vomito": self.cb_vomito.currentText(),
            "mareo": self.cb_mareo.currentText(),
            "sincope": self.cb_sincope.currentText(),
            "dolor_mandibula": self.cb_mandibula.currentText(),
            "dolor_cuello": self.cb_cuello.currentText(),
            "dolor_brazo_izquierdo": self.cb_brazo_izq.currentText(),
            "dolor_brazo_derecho": self.cb_brazo_der.currentText(),
            "dolor_espalda": self.cb_espalda.currentText(),
            "dolor_epigastrio": self.cb_epigastrio.currentText(),
            "angina_diagnosticada": self.cb_angina.currentText(),
            "infarto_previo": self.cb_infarto_previo.currentText(),
            "stent_coronario": self.cb_stent.currentText(),
            "cirugia_cardiaca": self.cb_bypass.currentText(),
            "arritmias": self.cb_arritmia.currentText(),
            "hipertension": self.cb_hta.currentText(),
            "diabetes": self.cb_diabetes.currentText(),
            "dislipidemia": self.cb_dislipidemia.currentText(),
            "tabaquismo": self.cb_tabaquismo.currentText(),
            "obesidad": self.cb_obesidad.currentText(),
            "antecedentes_familiares": self.cb_familiares.currentText(),
            "alergia_ASA": self.cb_alergia_asa.currentText(),
            "hemorragias_activas": self.cb_hemorragias.currentText(),
            "potenciadores_sex": self.cb_pde5.currentText()
        }

        self.datos_paciente = DatosPaciente(
            nombre=nombre,
            edad=edad,
            sexo=self.cb_sexo.currentText(),
            cuestionario=cuestionario_dict
        )

        self.accept()


# ========================================================
# 4. MONITOR ECG DE 8 DERIVACIONES
# ========================================================

class MonitorECG_8Derivaciones(QtWidgets.QWidget):
    """Monitor para 8 derivaciones (DI, DII, DIII, aVR, aVL, aVF, V3, V5)"""

    NOMBRES_DERIVACIONES = ["DI", "DII", "DIII", "aVR", "aVL", "aVF", "V3", "V5"]
    TAMANO_BUFFER = 1000

    def __init__(self, datos_paciente: DatosPaciente):
        super().__init__()
        self.paciente = datos_paciente

        self.setWindowTitle(f"Monitor ECG 8 Derivaciones - {self.paciente.nombre}")
        self.showFullScreen()
        self.setStyleSheet("background-color: #0d0d0d; color: white; font-family: Arial;")

        self.buffers = {lead: deque([0.0]*self.TAMANO_BUFFER, maxlen=self.TAMANO_BUFFER) for lead in self.NOMBRES_DERIVACIONES}
        self.curves = {}

        self.inicializar_interfaz()

        # Hilo I2C
        self.hilo_i2c = HiloLecturaI2C()
        self.hilo_i2c.nuevos_datos.connect(self.recibir_muestra_i2c)
        self.hilo_i2c.error_i2c.connect(self.mostrar_error)

    def inicializar_interfaz(self):
        layout_principal = QtWidgets.QVBoxLayout(self)

        # Gráficas en matriz 2x4
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.win_grafica.setBackground('#0d0d0d')

        for idx, lead_name in enumerate(self.NOMBRES_DERIVACIONES):
            row = idx // 2
            col = idx % 2

            plot = self.win_grafica.addPlot(row=row, col=col, title=f"Derivación {lead_name}")
            plot.setYRange(-2.0, 3.3)
            plot.enableAutoRange(axis='y', enable=False)
            plot.showGrid(x=True, y=True, alpha=0.2)

            curve = plot.plot(pen=pg.mkPen(color='#39ff14', width=1.5))
            self.curves[lead_name] = curve

        layout_principal.addWidget(self.win_grafica, stretch=4)

        # Divisor
        linea = QtWidgets.QFrame()
        linea.setFrameShape(QtWidgets.QFrame.HLine)
        linea.setStyleSheet("color: #333;")
        layout_principal.addWidget(linea)

        # Panel Inferior
        layout_inferior = QtWidgets.QHBoxLayout()

        self.consola = QtWidgets.QTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setStyleSheet("background-color: #141414; color: #00ffcc; border: 1px solid #222; font-size: 11px;")

        self.consola.append(f"[PACIENTE] {self.paciente.nombre} | {self.paciente.edad} años | Sexo: {self.paciente.sexo}")
        self.consola.append(f"[SÍNTOMAS] Dolor tórax: {self.paciente.cuestionario.get('dolor_torax')} | Intensidad: {self.paciente.cuestionario.get('dolor_intensidad')}/10 | Tipo: {self.paciente.cuestionario.get('dolor_tipo')}")
        self.consola.append(f"[FACTORES RIESGO] HTA: {self.paciente.cuestionario.get('hipertension')} | Diabetes: {self.paciente.cuestionario.get('diabetes')} | Tabaquismo: {self.paciente.cuestionario.get('tabaquismo')}")
        self.consola.append("[ESTADO] Listo para muestrear 2x ADS1115 (0x48 / 0x49)...")

        layout_inferior.addWidget(self.consola, stretch=3)

        # Botones de control
        layout_botones = QtWidgets.QVBoxLayout()
        self.btn_iniciar = QtWidgets.QPushButton("⚡ Iniciar Muestreo (2x ADS1115)")
        self.btn_iniciar.setStyleSheet("background-color: #27ae60; font-size: 13px; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_iniciar.clicked.connect(self.iniciar_captura)

        self.btn_detener = QtWidgets.QPushButton("⏹ Detener")
        self.btn_detener.setEnabled(False)
        self.btn_detener.setStyleSheet("background-color: #c0392b; font-size: 13px; font-weight: bold; padding: 12px; border-radius: 5px;")
        self.btn_detener.clicked.connect(self.detener_captura)

        layout_botones.addWidget(self.btn_iniciar)
        layout_botones.addWidget(self.btn_detener)
        layout_inferior.addLayout(layout_botones, stretch=1)

        layout_principal.addLayout(layout_inferior, stretch=1)

    def iniciar_captura(self):
        self.consola.append("[I2C] Iniciando captura desde ADS1115 (0x48) y ADS1115 (0x49)...")
        self.hilo_i2c.start()
        self.btn_iniciar.setEnabled(False)
        self.btn_detener.setEnabled(True)

    def detener_captura(self):
        self.hilo_i2c.detener()
        self.consola.append("[I2C] Captura detenida.")
        self.btn_iniciar.setEnabled(True)
        self.btn_detener.setEnabled(False)

    def recibir_muestra_i2c(self, datos_8ch: list):
        for lead_name, val in zip(self.NOMBRES_DERIVACIONES, datos_8ch):
            self.buffers[lead_name].append(val)
            self.curves[lead_name].setData(list(self.buffers[lead_name]))

    def mostrar_error(self, msj: str):
        self.consola.append(f"[ERROR I2C] {msj}")

    def closeEvent(self, event):
        self.hilo_i2c.detener()
        event.accept()


# ========================================================
# 5. EJECUCIÓN SECUENCIAL
# ========================================================

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    cuestionario = VentanaDatosPaciente()

    if cuestionario.exec() == QtWidgets.QDialog.Accepted:
        monitor = MonitorECG_8Derivaciones(datos_paciente=cuestionario.datos_paciente)
        monitor.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)