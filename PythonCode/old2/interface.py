"""
interface.py
------------------------------------------------
ECG Real-Time Interface

Top plot:
    Lead II (always visible)

Bottom plot:
    User selectable lead
"""

import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
)

from config import *
from filters import ecg_filter


class MainWindow(QMainWindow):

    def __init__(self, buffer):

        super().__init__()

        self.buffer = buffer

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # -----------------------------------------
        # Central Widget
        # -----------------------------------------

        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout()
        central.setLayout(layout)

        # -----------------------------------------
        # Lead selector
        # -----------------------------------------

        selector_layout = QHBoxLayout()

        label = QLabel("Second Lead:")

        self.lead_selector = QComboBox()

        for lead in DISPLAY_LEADS:
            self.lead_selector.addItem(lead)

        # Default to V3
        self.lead_selector.setCurrentText("V3")

        selector_layout.addWidget(label)
        selector_layout.addWidget(self.lead_selector)
        selector_layout.addStretch()

        layout.addLayout(selector_layout)

        # -----------------------------------------
        # Graphics widget
        # -----------------------------------------

        pg.setConfigOptions(
            antialias=True,
            background='k',
            foreground='w'
        )

        self.graphics = pg.GraphicsLayoutWidget()

        layout.addWidget(self.graphics)

        # -----------------------------------------
        # Lead II plot
        # -----------------------------------------

        self.plot_top = self.graphics.addPlot()

        self.plot_top.setTitle("Lead II")

        self.plot_top.showGrid(
            x=True,
            y=True,
            alpha=GRID_ALPHA
        )

        self.plot_top.setLabel(
            'left',
            'Voltage',
            units='V'
        )

        self.plot_top.setLabel(
            'bottom',
            'Time',
            units='s'
        )

        self.curve_top = self.plot_top.plot(
            pen=LEAD_II_COLOR,
            width=2
        )

        # -----------------------------------------
        # Second plot
        # -----------------------------------------

        self.graphics.nextRow()

        self.plot_bottom = self.graphics.addPlot()

        self.plot_bottom.showGrid(
            x=True,
            y=True,
            alpha=GRID_ALPHA
        )

        self.plot_bottom.setLabel(
            'left',
            'Voltage',
            units='V'
        )

        self.plot_bottom.setLabel(
            'bottom',
            'Time',
            units='s'
        )

        self.curve_bottom = self.plot_bottom.plot(
            pen=SECOND_LEAD_COLOR,
            width=2
        )

        # -----------------------------------------
        # X-axis (6 seconds)
        # -----------------------------------------

        self.x = np.linspace(
            -PLOT_SECONDS,
            0,
            BUFFER_SIZE
        )

        self.plot_top.setXRange(
            -PLOT_SECONDS,
            0
        )

        self.plot_bottom.setXRange(
            -PLOT_SECONDS,
            0
        )

        # -----------------------------------------
        # Refresh timer
        # -----------------------------------------

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.update_plots
        )

        self.timer.start(
            int(1000 / GUI_REFRESH_RATE)
        )

    # =====================================================
    # Update plots
    # =====================================================

    def update_plots(self):

        # -----------------------------------------
        # Lead II (always displayed)
        # -----------------------------------------

        lead2 = self.buffer.get_lead("DII")

        # Uncomment later to enable filtering
        # lead2 = ecg_filter(lead2, self.buffer.fs)

        self.curve_top.setData(
            self.x,
            lead2
        )

        # -----------------------------------------
        # Selected lead
        # -----------------------------------------

        selected = self.lead_selector.currentText()

        if selected == "aVR":
            lead = self.buffer.get_avr()

        elif selected == "aVL":
            lead = self.buffer.get_avl()

        elif selected == "aVF":
            lead = self.buffer.get_avf()

        else:
            lead = self.buffer.get_lead(selected)

        # Uncomment later
        # lead = ecg_filter(lead, self.buffer.fs)

        self.curve_bottom.setData(
            self.x,
            lead
        )

        self.plot_bottom.setTitle(selected)

        # -----------------------------------------
        # Fixed Y-axis
        # -----------------------------------------

        self.plot_top.setYRange(
            0,
            5,
            padding=0
        )

        self.plot_bottom.setYRange(
            0,
            5,
            padding=0
        )

    # =====================================================
    # Close Event
    # =====================================================

    def closeEvent(self, event):

        self.timer.stop()

        event.accept()