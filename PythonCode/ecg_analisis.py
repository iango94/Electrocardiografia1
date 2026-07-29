import sys
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any

from PySide6 import QtWidgets, QtCore
import pyqtgraph as pg

import smbus2

# ========================================================
# 1. ESTRUCTURA DE DATOS DEL PACIENTE
# ========================================================

@dataclass
class DatosPaciente:
    nombre: str = "Paciente_Raspberry"
    edad: int = 25
    sexo: str = "M"
    cuestionario: Dict[str, Any] = field(default_factory=dict)


# ========================================================
# HILO DE LECTURA OPTIMIZADO (RINDE ~300-350 SPS)
# ========================================================

class HiloLecturaI2C(QtCore.QThread):
    nuevos_datos = QtCore.Signal(list)
    sps_actualizado = QtCore.Signal(float)
    error_i2c = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ejecutando = False

    def run(self):
        try:
            bus = smbus2.SMBus(1)
            ADDR1 = 0x48

            # Configuración ADS1115 (860 SPS, Gain +/-4.096V, Single-Shot):
            # Bit 15 = 1 (Iniciar conversión)
            # MUX A0-A1 (DI)  -> 0x83E3
            # MUX A2-A3 (DII) -> 0xB3E3
            CONF_DI_BYTES  = [0x83, 0xE3]
            CONF_DII_BYTES = [0xB3, 0xE3]

            REG_CONV = 0x00
            REG_CFG  = 0x01

            def leer_canal(bytes_config):
                # 1. Escribir en el registro de configuración para cambiar MUX e INICIAR conversión
                bus.write_i2c_block_data(ADDR1, REG_CFG, bytes_config)
                
                # 2. Esperar a que el bit OS (Bit 15) vuelva a 1 (Conversión completada)
                # A 860 SPS, tarda exactamente ~1.16 milisegundos por canal
                time.sleep(0.0012)
                
                # 3. Leer el registro de conversión (0x00)
                data = bus.read_i2c_block_data(ADDR1, REG_CONV, 2)
                raw = (data[0] << 8) | data[1]
                
                return raw - 65536 if raw > 32767 else raw

            self.ejecutando = True

        except Exception as e:
            self.error_i2c.emit(f"Error I2C: {e}")
            return

        volts_per_bits = 4.096 / 32767.0

        contador_muestras = 0
        tiempo_inicio = time.time()

        while self.ejecutando:
            try:
                # Lectura individual forzada paso a paso
                raw_DI  = leer_canal(CONF_DI_BYTES)
                raw_DII = leer_canal(CONF_DII_BYTES)

                # Convertir a voltios
                v_DI  = raw_DI * volts_per_bits
                v_DII = raw_DII * volts_per_bits

                # Cálculo de las 6 derivaciones
                v_DIII = v_DII - v_DI
                v_aVR  = -(v_DI + v_DII) / 2.0
                v_aVL  = v_DI - (v_DII / 2.0)
                v_aVF  = v_DII - (v_DI / 2.0)

                self.nuevos_datos.emit([v_DI, v_DII, v_DIII, v_aVR, v_aVL, v_aVF])

                # Benchmark SPS
                contador_muestras += 1
                if contador_muestras >= 50:
                    t_actual = time.time()
                    dt = t_actual - tiempo_inicio
                    if dt > 0:
                        self.sps_actualizado.emit(contador_muestras / dt)
                    contador_muestras = 0
                    tiempo_inicio = t_actual

            except Exception as e:
                self.error_i2c.emit(f"Fallo I2C: {e}")
                time.sleep(0.01)

    def detener(self):
        self.ejecutando = False
        self.wait()

# ========================================================
# 3. INTERFAZ Y MONITOR ECG CON INDICADOR DE SPS
# ========================================================

class MonitorECG(QtWidgets.QWidget):
    NOMBRES_DERIVACIONES = ["DI", "DII", "DIII", "aVR", "aVL", "aVF"]
    TAMANO_BUFFER = 1000

    def __init__(self, datos_paciente: DatosPaciente):
        super().__init__()
        self.paciente = datos_paciente

        self.setWindowTitle("Monitor ECG Differential - ADS1115 Benchmark")
        self.showFullScreen()
        self.setStyleSheet("background-color: #0d0d0d; color: white; font-family: Arial;")

        self.buffers = {lead: np.zeros(self.TAMANO_BUFFER, dtype=np.float32) for lead in self.NOMBRES_DERIVACIONES}
        self.curves = {}

        self.inicializar_interfaz()

        self.hilo_i2c = HiloLecturaI2C()
        self.hilo_i2c.nuevos_datos.connect(self.recibir_muestra_i2c)
        self.hilo_i2c.sps_actualizado.connect(self.actualizar_sps_gui)
        self.hilo_i2c.error_i2c.connect(self.mostrar_error)

        # Refresco visual desacoplado a ~30 FPS
        self.timer_gui = QtCore.QTimer(self)
        self.timer_gui.setInterval(33)
        self.timer_gui.timeout.connect(self.actualizar_graficas_gui)

    def inicializar_interfaz(self):
        layout_principal = QtWidgets.QVBoxLayout(self)

        # Barra superior con información de estado y Benchmark SPS
        layout_top = QtWidgets.QHBoxLayout()
        self.lbl_paciente = QtWidgets.QLabel(f"<b>Paciente:</b> {self.paciente.nombre}")
        self.lbl_paciente.setStyleSheet("font-size: 14px; color: #ffffff;")
        
        self.lbl_sps = QtWidgets.QLabel("<b>Velocidad Muestreo:</b> -- SPS")
        self.lbl_sps.setStyleSheet("font-size: 16px; color: #00ffcc; font-weight: bold; background-color: #1a1a1a; padding: 6px; border-radius: 4px;")

        layout_top.addWidget(self.lbl_paciente)
        layout_top.addStretch()
        layout_top.addWidget(self.lbl_sps)
        layout_principal.addLayout(layout_top)

        # Rejilla 2x3 para Gráficas ECG
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.win_grafica.setBackground('#0d0d0d')
        pg.setConfigOptions(useOpenGL=True, antialias=False)

        for idx, lead_name in enumerate(self.NOMBRES_DERIVACIONES):
            row = idx // 2
            col = idx % 2

            plot = self.win_grafica.addPlot(row=row, col=col, title=f"Derivación {lead_name}")
            plot.setYRange(-1.5, 3.5)
            plot.enableAutoRange(axis='y', enable=False)
            plot.showGrid(x=True, y=True, alpha=0.2)

            plot.setDownsampling(auto=True, mode='peak')
            plot.setClipToView(True)

            curve = plot.plot(pen=pg.mkPen(color='#39ff14', width=1.5))
            self.curves[lead_name] = curve

        layout_principal.addWidget(self.win_grafica, stretch=4)

        # Panel de Botones y Consola
        layout_inferior = QtWidgets.QHBoxLayout()
        
        self.consola = QtWidgets.QTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setStyleSheet("background-color: #141414; color: #00ffcc; font-size: 11px;")
        self.consola.append("[BENCHMARK] Medidor de SPS activo. Presiona Iniciar...")
        layout_inferior.addWidget(self.consola, stretch=3)

        layout_botones = QtWidgets.QVBoxLayout()
        self.btn_iniciar = QtWidgets.QPushButton("⚡ Iniciar Muestreo")
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
        self.consola.append("[I2C] Iniciando captura y benchmark de velocidad...")
        self.hilo_i2c.start()
        self.timer_gui.start()
        self.btn_iniciar.setEnabled(False)
        self.btn_detener.setEnabled(True)

    def detener_captura(self):
        self.hilo_i2c.detener()
        self.timer_gui.stop()
        self.lbl_sps.setText("<b>Velocidad Muestreo:</b> Detenido")
        self.consola.append("[I2C] Muestreo detenido.")
        self.btn_iniciar.setEnabled(True)
        self.btn_detener.setEnabled(False)

    def recibir_muestra_i2c(self, datos_6ch: list):
        for lead_name, val in zip(self.NOMBRES_DERIVACIONES, datos_6ch):
            self.buffers[lead_name] = np.roll(self.buffers[lead_name], -1)
            self.buffers[lead_name][-1] = val

    def actualizar_sps_gui(self, sps: float):
        # Muestra las muestras/conversiones completas por segundo en la GUI
        self.lbl_sps.setText(f"<b>Velocidad Muestreo:</b> {sps:.1f} SPS")

    def actualizar_graficas_gui(self):
        for lead_name in self.NOMBRES_DERIVACIONES:
            self.curves[lead_name].setData(self.buffers[lead_name])

    def mostrar_error(self, msj: str):
        self.consola.append(f"[ERROR I2C] {msj}")

    def closeEvent(self, event):
        self.timer_gui.stop()
        self.hilo_i2c.detener()
        event.accept()


# ========================================================
# 4. EJECUCIÓN
# ========================================================

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    paciente_test = DatosPaciente(nombre="Prueba_SPS")
    monitor = MonitorECG(datos_paciente=paciente_test)
    monitor.show()
    sys.exit(app.exec())