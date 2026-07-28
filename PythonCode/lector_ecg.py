import board
import busio
import adafruit_ads1x15.ads1115 as ADS

class LectorECG:
    def __init__(self):
        # I2C a alta velocidad (400kHz)
        self.i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
        
        # Inicializar ambos ADS1115
        self.ads_1 = ADS.ADS1115(self.i2c, address=0x48)
        #self.ads_2 = ADS.ADS1115(self.i2c, address=0x49)
        
        # Modo continuo y velocidad máxima de 860 SPS
        self.ads_1.mode = 0  
        #self.ads_2.mode = 0  
        self.ads_1.data_rate = 860  
        #self.ads_2.data_rate = 860  
        
        # Ganancia fija (Modificar según la salida de tu front-end)
        self.ads_1.gain = 1
        #self.ads_2.gain = 1
        
        # Constantes de multiplexación diferencial
        self.MUX_DI  = 0b100  # AIN0 vs AIN1
        self.MUX_DII = 0b101  # AIN2 vs AIN3
        #self.MUX_V1  = 0b100  # AIN0 vs AIN1
        #self.MUX_V5  = 0b101  # AIN2 vs AIN3
        
        # Factor de conversión (Bits a Voltios)
        self.VOLTS_PER_BIT = 4.096 / 32767

    def leer_canales(self):
        """Lee de inmediato el registro de hardware de ambos chips"""
        # Lectura ADS 1
        self.ads_1.mux = self.MUX_DI
        v_di = self.ads_1.get_last_reading() * self.VOLTS_PER_BIT
        
        self.ads_1.mux = self.MUX_DII
        v_dii = self.ads_1.get_last_reading() * self.VOLTS_PER_BIT
        
        # Lectura ADS 2
        #self.ads_2.mux = self.MUX_V1
        #v_v1 = self.ads_2.get_last_reading() * self.VOLTS_PER_BIT
        
        #self.ads_2.mux = self.MUX_V5
        #v_v5 = self.ads_2.get_last_reading() * self.VOLTS_PER_BIT
        
        return v_di, v_dii #, v_v1, v_v5