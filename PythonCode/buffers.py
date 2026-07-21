"""
buffers.py
-----------------------------------------
Shared ECG Circular Buffer
"""

import numpy as np
from threading import Lock


class ECGBuffer:

    def __init__(self, fs, seconds):

        self.fs = fs
        self.seconds = seconds
        self.size = int(fs * seconds)

        self.lock = Lock()

        # Circular write position
        self.index = 0

        # Buffers
        self.data = {
            "DI":   np.zeros(self.size, dtype=np.float32),
            "DII":  np.zeros(self.size, dtype=np.float32),
            "DIII": np.zeros(self.size, dtype=np.float32),
            "V3":   np.zeros(self.size, dtype=np.float32),
            "V5":   np.zeros(self.size, dtype=np.float32),
            "REF":  np.zeros(self.size, dtype=np.float32),
        }

    # --------------------------------------------------
    # Add one complete sample
    # --------------------------------------------------

    def append(self, di, dii, diii, v3, v5, ref):

        with self.lock:

            i = self.index

            self.data["DI"][i] = di
            self.data["DII"][i] = dii
            self.data["DIII"][i] = diii
            self.data["V3"][i] = v3
            self.data["V5"][i] = v5
            self.data["REF"][i] = ref

            self.index += 1

            if self.index >= self.size:
                self.index = 0

    # --------------------------------------------------
    # Return one lead ordered from oldest → newest
    # --------------------------------------------------

    def get_lead(self, lead):

        with self.lock:

            i = self.index

            return np.concatenate((
                self.data[lead][i:],
                self.data[lead][:i]
            ))

    # --------------------------------------------------
    # Return all measured leads
    # --------------------------------------------------

    def get_all(self):

        with self.lock:

            i = self.index

            output = {}

            for lead in self.data:

                output[lead] = np.concatenate((
                    self.data[lead][i:],
                    self.data[lead][:i]
                ))

            return output

    # --------------------------------------------------
    # Computed Leads
    # --------------------------------------------------

    def get_avr(self):

        di = self.get_lead("DI")
        dii = self.get_lead("DII")

        return -(di + dii) / 2

    def get_avl(self):

        di = self.get_lead("DI")
        dii = self.get_lead("DII")

        return di - (dii / 2)

    def get_avf(self):

        di = self.get_lead("DI")
        dii = self.get_lead("DII")

        return dii - (di / 2)