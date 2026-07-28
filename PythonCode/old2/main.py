"""
main.py
-----------------------------------------
ECG Acquisition System

Measured Leads:
    DI
    DII
    DIII
    V3
    V5
    REF

Author: Jaco Gomez
"""

import sys

from PySide6.QtWidgets import QApplication

from buffers import ECGBuffer
from acquisition import AcquisitionThread
from interface import MainWindow


# =====================================================
# CONFIGURATION
# =====================================================

BUFFER_SECONDS = 6
CHANNEL_FS = 286          # ≈860 SPS / 3 channels


# =====================================================
# MAIN
# =====================================================

def main():

    # Create shared ECG buffer
    ecg_buffer = ECGBuffer(
        fs=CHANNEL_FS,
        seconds=BUFFER_SECONDS
    )

    # Start acquisition thread
    acquisition = AcquisitionThread(ecg_buffer)
    acquisition.start()

    # Create GUI
    app = QApplication(sys.argv)

    window = MainWindow(ecg_buffer)
    window.show()

    exit_code = app.exec()

    # Stop acquisition cleanly
    acquisition.stop()
    acquisition.wait()

    sys.exit(exit_code)


# =====================================================

if __name__ == "__main__":
    main()