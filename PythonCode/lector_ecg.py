import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1115 import Pin

class LectorECG:
    def __init__(self):
        # I2C a alta velocidad (400kHz)
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
        
        # Inicializar ambos ADS1115
        self.ads_1 = ADS.ADS1115(self.i2c, address=0x48)
        # self.ads_2 = ADS.ADS1115(self.i2c, address=0x49)
        
        # Configurar tasa de muestreo (860 SPS) y ganancia (1 = +/- 4.096V)
        self.ads_1.data_rate = 860  
        self.ads_1.gain = 1
        
        # self.ads_2.data_rate = 860  
        # self.ads_2.gain = 1
        
        # Definir canales diferenciales
        # P0_P1 equivale a MUX 0b100 (AIN0 vs AIN1)
        # P2_P3 equivale a MUX 0b101 (AIN2 vs AIN3)
        self.chan_di = AnalogIn(self.ads_1, Pin.A0, Pin.A1)
        self.chan_dii = AnalogIn(self.ads_1, Pin.A2, Pin.A3)
        
        # self.chan_v1 = AnalogIn(self.ads_2, ADS.P0, ADS.P1)
        # self.chan_v5 = AnalogIn(self.ads_2, ADS.P2, ADS.P3)
        
        # Factor de conversión (Bits a Voltios)
        self.VOLTS_PER_BIT = 4.096 / 32767

    def leer_canales(self):
        """Lee la tensión en voltios de los canales configurados."""
        # Opción A: Usar directamente .voltage (calcula los voltios en base a la ganancia automáticamente)
        v_di = self.chan_di.voltage
        v_dii = self.chan_dii.voltage
        
        # Opción B: Si prefieres aplicar tu constante manual con .value (bits crudos):
        # v_di = self.chan_di.value * self.VOLTS_PER_BIT
        # v_dii = self.chan_dii.value * self.VOLTS_PER_BIT
        
        # v_v1 = self.chan_v1.voltage
        # v_v5 = self.chan_v5.voltage
        
        return v_di, v_dii #, v_v1, v_v5