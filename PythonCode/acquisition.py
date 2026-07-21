"""
acquisition.py
------------------------------------------------
Reads two ADS1115s continuously and stores the
samples in the shared ECGBuffer.
"""

from PySide6.QtCore import QThread

import board
import busio

from adafruit_ads1x15.ads1115 import ADS1115, Pin
from adafruit_ads1x15.analog_in import AnalogIn


class AcquisitionThread(QThread):

    def __init__(self, buffer):

        super().__init__()

        self.buffer = buffer
        self.running = True

        # -----------------------------
        # I2C
        # -----------------------------

        i2c = busio.I2C(board.SCL, board.SDA)

        # ADS #1
        self.ads1 = ADS1115(i2c, address=0x48)

        # ADS #2
        self.ads2 = ADS1115(i2c, address=0x49)

        # Maximum speed
        self.ads1.data_rate = 860
        self.ads2.data_rate = 860

        # ±6.144 V Full Scale
        self.ads1.gain = 2 / 3
        self.ads2.gain = 2 / 3

        # -----------------------------
        # Channels
        # -----------------------------

        self.DI = AnalogIn(self.ads1, Pin.A0)
        self.DII = AnalogIn(self.ads1, Pin.A1)
        self.DIII = AnalogIn(self.ads1, Pin.A2)

        self.V3 = AnalogIn(self.ads2, Pin.A0)
        self.V5 = AnalogIn(self.ads2, Pin.A1)
        self.REF = AnalogIn(self.ads2, Pin.A2)

    # -------------------------------------------------

    def stop(self):

        self.running = False

    # -------------------------------------------------

    def run(self):

        while self.running:

            # ADS #1
            di = self.DI.voltage
            dii = self.DII.voltage
            diii = self.DIII.voltage

            # ADS #2
            v3 = self.V3.voltage
            v5 = self.V5.voltage
            ref = self.REF.voltage

            # Store one complete sample
            self.buffer.append(
                di,
                dii,
                diii,
                v3,
                v5,
                ref
            )