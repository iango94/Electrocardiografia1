import sys
import serial
import numpy as np
from PyQt5 import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

# === IMPORTANTE: IMPORTAMOS TU MODULO DE ANALISIS ===
import Ecg_Analisis1 

ser = None
t_local = 0
subtimer_local = 0
respuestas_cuestionario = {}

# ========================================================
# CLASES DE INTERFAZ GRÁFICA
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
        # Actualizamos las variables del módulo médico de forma directa
        ecg_analisis.paciente = self.txt_nombre.text().strip()
        ecg_analisis.file_name = f"ECG_{ecg_analisis.paciente}.pdf"
        ecg_analisis.diagnostico['edad'] = int(self.txt_edad.text())
        ecg_analisis.diagnostico['sexo'] = self.cb_sexo.currentText()
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

        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot_decorativo = self.win_grafica.addPlot()
        self.plot_decorativo.setYRange(-0.5, 1.5)
        self.curve_dec = self.plot_decorativo.plot(pen='r')
        self.win_grafica.setMaximumHeight(180)
        layout.addWidget(self.win_grafica)

        self.lbl_pregunta = QtWidgets.QLabel(self.preguntas[self.indice])
        self.lbl_pregunta.setStyleSheet("font-size: 13px; font-weight: bold; margin: 15px 0px; color: #2c3e50;")
        layout.addWidget(self.lbl_pregunta)

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
        x = np.linspace(0, 2, 100)
        y = np.zeros_like(x)
        y[30:33] = 1.2; y[28:30] = -0.2; y[33:36] = -0.3
        self.curve_dec.setData(x, y)
        self.plot_decorativo.hideAxis('bottom')
        self.plot_decorativo.hideAxis('left')

    def guardar_respuesta(self, valor):
        self.respuestas[self.preguntas[self.indice]] = valor
        self.indice += 1
        if self.indice < len(self.preguntas):
            self.lbl_pregunta.setText(self.preguntas[self.indice])
        else:
            QtWidgets.QMessageBox.information(self, "Terminado", "Cuestionario guardado exitosamente.")
            self.accept()


class VentanaPrincipalECG(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Monitor de ECG en Tiempo Real - Paciente: {ecg_analisis.paciente}")
        self.setGeometry(100, 100, 950, 600)
        self.crear_ui()

    def crear_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        layout_com = QtWidgets.QHBoxLayout()
        layout_com.addWidget(QtWidgets.QLabel("<b>Seleccionar Puerto Serial de Conexión:</b>"))
        self.combo_puerto = QtWidgets.QComboBox()
        self.combo_puerto.addItems([f"COM{i}" for i in range(1, 10)])
        self.combo_puerto.setCurrentText('COM5')
        layout_com.addWidget(self.combo_puerto)
        
        self.btn_conectar = QtWidgets.QPushButton("Conectar Arduino Nano")
        self.btn_conectar.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_conectar.clicked.connect(self.conectar_serial)
        layout_com.addWidget(self.btn_conectar)
        layout.addLayout(layout_com)

        self.consola = QtWidgets.QTextEdit()
        self.consola.setReadOnly(True)
        self.consola.setPlaceholderText("Logs operativos e información clínica...")
        layout.addWidget(self.consola)

        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot = self.win_grafica.addPlot(title="ECG Real-Time")
        self.plot.setYRange(-2, 2)
        self.plot.enableAutoRange(axis='y', enable=False)
        self.curve = self.plot.plot(pen='g')

        self.hr_label = pg.TextItem(color='y')
        self.plot.addItem(self.hr_label)
        layout.addWidget(self.win_grafica)

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

        # Triggers visuales vinculados a llamadas de funciones del módulo importado
        self.btn_cuestionario.clicked.connect(self.abrir_cuestionario)
        self.btn_g.clicked.connect(self.disparar_export)
        self.btn_r.clicked.connect(self.disparar_reporte)
        self.btn_f.clicked.connect(self.disparar_full_analisis)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_loop)

    def conectar_serial(self):
        global ser
        puerto_seleccionado = self.combo_puerto.currentText()
        try:
            ser = serial.Serial(puerto_seleccionado, ecg_analisis.BAUD)
            self.consola.append(f"[HARDWARE] Conectado exitosamente al puerto {puerto_seleccionado}")
            self.timer.start(10)
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

    def disparar_export(self):
        if ecg_analisis.export_pdf():
            self.consola.append(f"[EXPORT] PDF Guardado de forma exitosa como: {ecg_analisis.file_name}")
        else:
            self.consola.append("[ADVERTENCIA] Buffer insuficiente para exportar.")

    def disparar_reporte(self):
        res = ecg_analisis.report_pdf()
        if res:
            self.consola.append(f"[REPORTE] Guardado Reporte{ecg_analisis.file_name}. Métricas calculadas: {res}")
        else:
            self.consola.append("[ADVERTENCIA] Buffer insuficiente para generar reporte.")

    def disparar_full_analisis(self):
        ok, msg = ecg_analisis.full_analisis()
        if ok:
            self.consola.append(f"[NEUROKIT] Análisis global ejecutado. Reporte médico actualizado.")
        else:
            self.consola.append(f"[ERROR] {msg}")

    def update_loop(self):
        global t_local, subtimer_local, ser
        if ser is None or not ser.is_open: return

        tiempo_subtimer = 3 
        control_subtimer = 85 * tiempo_subtimer

        while ser.in_waiting:
            try:
                value = int(ser.readline().decode().strip())
                ecg_analisis.ecg_buffer.append(value)
                ecg_analisis.time_buffer.append(t_local)
                t_local += 1 / ecg_analisis.FS
            except:
                pass

        subtimer_local += 1

        if len(ecg_analisis.ecg_buffer) > ecg_analisis.FS:
            signal = ecg_analisis.normalize(list(ecg_analisis.ecg_buffer))
            cleaned = ecg_analisis.filtrar_ECG(signal) 
            self.curve.setData(cleaned)

            if len(signal) > ecg_analisis.hr_size and subtimer_local >= control_subtimer:
                hr = float(ecg_analisis.compute_hr(signal))
                self.hr_label.setText(f"HR: {hr:.1f} bpm")
                self.hr_label.setPos(len(signal)*0.7, max(cleaned))
                subtimer_local = 0

    def keyPressEvent(self, event):
        if event.text() == 'g': self.disparar_export()
        elif event.text() == 'r': self.disparar_reporte()
        elif event.text() == 'f': self.disparar_full_analisis()
        elif event.text() == 'h': 
            div = ecg_analisis.reducir_divisor()
            self.consola.append(f"[DIVISOR] Ajustado vía teclado a: {div}")
        elif event.text() == 'l': 
            div = ecg_analisis.incrementar_divisor()
            self.consola.append(f"[DIVISOR] Ajustado vía teclado a: {div}")


# ========================================================
# FLUJO PRINCIPAL DE CONTROL
# ========================================================
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    
    portada = PortadaECG()
    if portada.exec_() == QtWidgets.QDialog.Accepted:
        main_window = VentanaPrincipalECG()
        main_window.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
