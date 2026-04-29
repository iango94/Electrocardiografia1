Repositorio exposicion sobre electrocardiografia.

Orden que hablamos en clase:

    1: Elecrtoficiologia del corazon.
    
    2: Como funciona 1 electrocardiografo:
        a) se captura la señal por medio de 2 electrodos.
        b) se amplifica la señal (original de aprox 1mV pico-pico) referenciandola entre 0 y 3.3v
        c) se filtra la señal.
            I) filtro pasa altas a 0.5Hz (elimina ruido causado por la respiracion)
            II) filtro pasa.bajas a 50 o 60Hz. (elimina ruido de AC y radiofrecuncias)
            motivo: los datos importantes del ECG (señal) suelen estar en frecuancias entre 0.8Hz y 40Hz
        d) se digitaliza a 360 muestras por segundo y aprox. 10 bit de profundidad.
        e) se envia via puerto serie al PC (muestra a mustra como 1 entrero positivo entre 0 y 1000)
        d) se captura usando software (python) la representacion digital de la señal, y sabiendo que se toman 360 mustras por segundo, se almacena un bufer de 6 seg.
        e) se filtra la señal digitalmente con un pasa-banda entre 0.5 y 50Hz.
        d) Se grafica la señal en el tiempo.  


    3) Demostracion:
        a) conectar electrodos.
        b) correr programa y elegir puerto serie.
        c) hacer el plot en tiempo real hasta que se estabilize la señal.
        d) tomar captura
        e) mostrar ECG en formato "tipico"
