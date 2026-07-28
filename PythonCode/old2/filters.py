"""
filters.py
------------------------------------------------
Digital ECG Filters
"""

import numpy as np
from scipy.signal import butter, sosfiltfilt, iirnotch, filtfilt


# ============================================================
# Bandpass
# ============================================================

def bandpass(signal, fs, lowcut=0.5, highcut=40.0, order=4):
    """
    ECG bandpass filter.

    Parameters
    ----------
    signal : ndarray
    fs : float
        Sampling frequency (Hz)
    lowcut : float
    highcut : float
    order : int

    Returns
    -------
    ndarray
    """

    sos = butter(
        order,
        [lowcut, highcut],
        btype="bandpass",
        fs=fs,
        output="sos"
    )

    return sosfiltfilt(sos, signal)


# ============================================================
# Notch
# ============================================================

def notch(signal, fs, freq=60.0, q=30):
    """
    60 Hz notch filter.
    """

    b, a = iirnotch(freq, q, fs)

    return filtfilt(b, a, signal)


# ============================================================
# Complete ECG filter
# ============================================================

def ecg_filter(signal, fs):
    """
    Complete ECG filtering.
    """

    signal = bandpass(
        signal,
        fs,
        lowcut=0.5,
        highcut=40
    )

    signal = notch(
        signal,
        fs,
        freq=60
    )

    return signal