"""
config.py
------------------------------------------------
Global configuration for the ECG acquisition system.
"""

# ============================================================
# ADS1115 CONFIGURATION
# ============================================================

# I2C Addresses
ADS1_ADDRESS = 0x48
ADS2_ADDRESS = 0x49

# Maximum ADS1115 sampling rate
ADS_DATA_RATE = 860

# Gain = ±6.144 V
ADS_GAIN = 2 / 3

# ============================================================
# ECG SAMPLING
# ============================================================

# Three channels are sampled sequentially per ADS1115.
# Effective rate per channel:
CHANNEL_FS = ADS_DATA_RATE / 3      # ≈286.67 Hz

BUFFER_SECONDS = 6

BUFFER_SIZE = int(CHANNEL_FS * BUFFER_SECONDS)

# ============================================================
# ANALOG FRONT END
# ============================================================

# ECG output range
ANALOG_MIN = 0.5        # Volts
ANALOG_MAX = 4.5        # Volts

# Virtual ground
REFERENCE_VOLTAGE = 2.5

# ============================================================
# DISPLAY
# ============================================================

GUI_REFRESH_RATE = 30       # FPS

PLOT_SECONDS = 6

# ============================================================
# FILTERS
# ============================================================

LOWCUT = 0.5

HIGHCUT = 100.0

NOTCH_FREQ = 60.0

NOTCH_Q = 30

FILTER_ORDER = 4

# ============================================================
# LEADS
# ============================================================

MEASURED_LEADS = (
    "DI",
    "DII",
    "DIII",
    "V3",
    "V5",
    "REF"
)

DISPLAY_LEADS = (
    "DI",
    "DII",
    "DIII",
    "V3",
    "V5",
    "aVR",
    "aVL",
    "aVF",
)

# ============================================================
# WINDOW
# ============================================================

WINDOW_TITLE = "ECG Acquisition"

WINDOW_WIDTH = 1200

WINDOW_HEIGHT = 800

# ============================================================
# COLORS
# ============================================================

BACKGROUND_COLOR = "k"

LEAD_II_COLOR = "g"

SECOND_LEAD_COLOR = "y"

GRID_ALPHA = 0.3