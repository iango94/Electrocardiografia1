import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QDialog, QLabel, 
                             QPushButton, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QMessageBox, QComboBox, QLineEdit)
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import ecg_analisis as utils

respuestas_cuestionario = {}

def mostrar_portada():
    portada = PortadaGrupo()
    return portada.exec_()

def ejecutar_cuestionario():
    dialogo = CuestionarioGrafico()
    if dialogo.exec_():
        return 0, dialogo.respuestas
    return 1, "Cuestionario cancelado."

class PortadaGrupo(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PORTADA DEL PROYECTO - ECG")
        self.setFixedSize(500, 380)
        self.setModal(True)

        layout = QVBoxLayout(self)

        titulo = QLabel("<h2>UNIVERSIDAD NACIONAL DE COLOMBIA</h2><h3>Sistema Biomédico de ECG - Arduino Nano</h3>")
        titulo.setStyleSheet("color: #1a5276; text-align: center;")
        layout.addWidget(titulo)

        info = QLabel(
            "<b>Asignatura:</b> Introducción a la Electrónica / Biomédica<br><br>"
            "<b>Docente Titular:</b> Profesor Encargado<br><br>"
            "<b>Grupo de Trabajo / Diseñadores:</b><br>"
            "· Jacobo (Diseñador de Hardware / Software)<br>"
            "· Integrante 2<br><br>"
            "<b>Frecuencia de Muestreo:</b> 360 Hz (Muestreo síncrono por Timer1)"
        )
        info.setStyleSheet("background-color: #f4f6f7; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)

        layout.addWidget(QLabel("<b>Nombre del Paciente a Evaluar:</b>"))
        self.txt_nombre = QLineEdit("PresentacionClase")
        layout.addWidget(self.txt_nombre)

        btn_entrar = QPushButton("INGRESAR AL MONITOR")
        btn_entrar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 35px;")
        btn_entrar.clicked.connect(self.guardar_y_entrar)
        layout.addWidget(btn_entrar)

    def guardar_y_entrar(self):
        # Configuramos los datos globales en el backend antes de lanzar el monitor principal
        utils.paciente = self.txt_nombre.text().strip()
        utils.file_name = f"ECG_{utils.paciente}.pdf"
        self.accept()


class CuestionarioGrafico(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Evaluación de Descarte Médico")
        self.setFixedSize(600, 450)
        self.setModal(True)

        self.respuestas = {}
        self.preguntas = [
            "1. ¿Presenta actualmente dolor opresivo en el pecho o sensación de ahogo?",
            "2. ¿Ha sentido palpitaciones aceleradas o arrítmicas en estado de reposo?",
            "3. ¿Sufre de síncopes (desmayos) repentinos o mareos agudos?",
            "4. ¿Posee diagnósticos previos de hipertensión arterial o insuficiencia cardíaca?"
        ]
        self.indice = 0

        layout_principal = QVBoxLayout(self)

        # --- APARTADO SUPERIOR DE GRÁFICO (Solicitado) ---
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot_decorativo = self.win_grafica.addPlot()
        self.plot_decorativo.setYRange(-1, 1.5)
        self.curve_decorativa = self.plot_decorativo.plot(pen='r', width=2)
        self.win_grafica.setMaximumHeight(200)
        layout_principal.addWidget(self.win_grafica)

        # Pregunta en texto plano destacado
        self.lbl_pregunta = QLabel(self.preguntas[self.indice])
        self.lbl_pregunta.setStyleSheet("font-size: 13px; font-weight: bold; margin: 15px 0px; color: #2c3e50;")
        layout_principal.addWidget(self.lbl_pregunta)

        # --- APARTADO INFERIOR: BOTONES SOLICITADOS (Sí, No, Prefiero no responder) ---
        layout_botones = QHBoxLayout()
        self.btn_si = QPushButton("Sí")
        self.btn_no = QPushButton("No")
        self.btn_pnr = QPushButton("Prefiero no responder")

        self.btn_si.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold; height: 35px; border-radius: 4px;")
        self.btn_no.setStyleSheet("background-color: #3498db; color: white; font-weight: bold; height: 35px; border-radius: 4px;")
        self.btn_pnr.setStyleSheet("background-color: #7f8c8d; color: white; font-weight: bold; height: 35px; border-radius: 4px;")

        layout_botones.addWidget(self.btn_si)
        layout_botones.addWidget(self.btn_no)
        layout_botones.addWidget(self.btn_pnr)
        layout_principal.addLayout(layout_botones)

        # Conexión de eventos por expresiones Lambda
        self.btn_si.clicked.connect(lambda: self.registrar("Sí"))
        self.btn_no.clicked.connect(lambda: self.registrar("No"))
        self.btn_pnr.clicked.connect(lambda: self.registrar("Prefiero no responder"))

        self.animar_grafico_pregunta()

    def animar_grafico_pregunta(self):
        """Genera un pulso cardíaco ilustrativo para el apartado gráfico superior"""
        x = np.linspace(0, 4, 200)
        # Simulación matemática rápida de un complejo QRS estético
        y = np.zeros_like(x)
        y[(x > 0.8) & (x < 0.9)] = (x[(x > 0.8) & (x < 0.9)] - 0.8) * 10  # Onda P
        y[(x > 1.4) & (x < 1.5)] = -0.3  # Onda Q
        y[(x > 1.5) & (x < 1.6)] = (x[(x > 1.5) & (x < 1.6)] - 1.5) * 15 # Onda R
        y[(x > 1.6) & (x < 1.7)] = -0.5  # Onda S
        self.curve_decorativa.setData(x, y)
        self.plot_decorativo.getAxis('bottom').setStyle(showValues=False)
        self.plot_decorativo.getAxis('left').setStyle(showValues=False)

    def registrar(self, respuesta):
        pregunta_actual = self.preguntas[self.indice]
        self.respuestas[pregunta_actual] = respuesta
        self.indice += 1

        if self.indice < len(self.preguntas):
            self.lbl_pregunta.setText(self.preguntas[self.indice])
        else:
            QMessageBox.information(self, "Cuestionario Listo", "Respuestas clínicas integradas con éxito.")
            self.accept()


class VentanaPrincipal(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Monitor Clínico de ECG - Paciente: {utils.paciente}")
        self.setGeometry(100, 100, 1000, 650)
        self.t = 0
        self.subtimer = 0
        self.crear_ui()

    def crear_ui(self):
        layout_principal = QVBoxLayout(self)

        # Panel Superior de Selección de Puerto Serial COM
        layout_serial = QHBoxLayout()
        layout_serial.addWidget(QLabel("<b>Seleccionar Puerto Arduino (Nano):</b>"))
        self.combo_puertos = QComboBox()
        self.combo_puertos.addItems([f"COM{i}" for i in range(1, 9)])
        self.combo_puertos.setCurrentText("COM5")
        layout_serial.addWidget(self.combo_puertos)

        self.btn_conectar = QPushButton("Conectar Hardware")
        self.btn_conectar.clicked.connect(self.conectar_arduino)
        self.btn_conectar.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        layout_serial.addWidget(self.btn_conectar)
        layout_principal.addLayout(layout_serial)

        # Monitor de Consola Central
        self.area_texto = QTextEdit()
        self.area_texto.setReadOnly(True)
        self.area_texto.setPlaceholderText("Logs operativos del sistema cardíaco...")
        layout_principal.addWidget(self.area_texto)

        # Lienzo en tiempo real usando PyqtGraph (Copiado de tu script original)
        self.win_grafica = pg.GraphicsLayoutWidget()
        self.plot = self.win_grafica.addPlot(title="Señal Filtrada ECG en Tiempo Real (Hz: 360)")
        self.plot.setYRange(-2, 2)
        self.plot.enableAutoRange(axis='y', enable=False)
        self.curve = self.plot.plot(pen='g')
        
        self.hr_label = pg.TextItem(color='y')
        self.plot.addItem(self.hr_label)
        layout_principal.addWidget(self.win_grafica)

        # Panel de Controles Inferiores (Botones de operaciones y periféricos)
        layout_controles = QHBoxLayout()
        self.btn_cuestionario = QPushButton("Lanzar Cuestionario")
        self.btn_pdf_simple = QPushButton("Exportar PDF ('g')")
        self.btn_pdf_reporte = QPushButton("Exportar Reporte ('r')")
        self.btn_salir = QPushButton("Desconectar y Salir")

        layout_controles.addWidget(self.btn_cuestionario)
        layout_controles.addWidget(self.btn_pdf_simple)
        layout_controles.addWidget(self.btn_pdf_reporte)
        layout_controles.addWidget(self.btn_salir)
        layout_principal.addLayout(layout_controles)

        # Eventos de los Botones
        self.btn_cuestionario.clicked.connect(self.abrir_cuestionario)
        self.btn_pdf_simple.clicked.connect(self.guardar_pdf)
        self.btn_pdf_reporte.clicked.connect(self.guardar_reporte_completo)
        self.btn_salir.clicked.connect(self.close)

        # Configuración del Reloj de Muestreo (Timer QT)
        self.timer_muestreo = QTimer()
        self.timer_muestreo.timeout.connect(self.leer_muestras_serial)

    def conectar_arduino(self):
        puerto = self.combo_puertos.currentText()
        exito, msg = utils.inicializar_serial(puerto)
        if exito:
            self.area_texto.append(f"[HARDWARE] {msg}")
            self.timer_muestreo.start(10) # Comienza la lectura cada 10ms
            self.btn_conectar.setEnabled(False)
        else:
            QMessageBox.critical(self, "Fallo Serial", msg)

    def abrir_cuestionario(self):
        status, res = ejecutar_cuestionario()
        if status == 0:
            global respuestas_cuestionario
            respuestas_cuestionario = res
            
            reporte = [f"=== HISTORIAL CLÍNICO PREVIO: {utils.paciente} ==="]
            for preg, resp in respuestas_cuestionario.items():
                reporte.append(f"• {preg}\n  Respuesta: {resp}")
            reporte.append("=========================================")
            self.area_texto.append("\n".join(reporte))

    def leer_muestras_serial(self):
        """Manejador del ciclo de adquisición síncrona de datos analógicos"""
        if utils.ser is None or not utils.ser.is_open:
            return

        tiempo_subtimer = 3
        control_subtimer = 85 * tiempo_subtimer

        while utils.ser.in_waiting:
            try:
                linea = utils.ser.readline().decode().strip()
                if linea:
                    value = int(linea)
                    utils.ecg_buffer.append(value)
                    utils.time_buffer.append(self.t)
                    self.t += 1 / utils.FS
            except:
                pass

        self.subtimer += 1

        if len(utils.ecg_buffer) > utils.FS:
            signal = utils.normalize(list(utils.ecg_buffer))
            cleaned = utils.filtrar_ECG(signal)
            self.curve.setData(cleaned)

            # Cálculo dinámico de Frecuencia Cardíaca cada ciclo del subtimer
            if len(signal) > utils.hr_size and self.subtimer >= control_subtimer:
                hr = float(utils.compute_hr(signal))
                if hr > 0:
                    self.hr_label.setText(f"HR: {hr:.1f} bpm")
                    self.hr_label.setPos(len(signal)*0.7, np.max(cleaned))
                self.subtimer = 0

    def guardar_pdf(self):
        exito, archivo = utils.export_pdf()
        if exito: self.area_texto.append(f"[SISTEMA] Archivo PDF guardado en: {archivo}")
        else: QMessageBox.warning(self, "Alerta", archivo)

    def guardar_reporte_completo(self):
        exito, archivo = utils.report_pdf()
        if exito: self.area_texto.append(f"[SISTEMA] Reporte Médico PDF guardado en: {archivo}")
        else: QMessageBox.warning(self, "Alerta", archivo)

    def keyPressEvent(self, event):
        """Mantiene los accesos rápidos por teclado que ya usabas"""
        if event.text() == 'g': self.guardar_pdf()
        elif event.text() == 'r': self.guardar_reporte_completo()
        elif event.text() == 'h': utils.reducir_divisor()
        elif event.text() == 'l': utils.incrementar_divisor()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Arranca primero la portada institucional del grupo
    if mostrar_portada() == QDialog.Accepted:
        ventana = VentanaPrincipal()
        ventana.show()
        sys.exit(app.exec_())
    else:
        sys.exit(0)
