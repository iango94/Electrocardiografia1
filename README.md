Repositorio exposicion sobre electrocardiografia.

Orden que hablamos en clase:

    1. Electroﬁsiología del corazón.

    2. Cómo funciona un electrocardiógrafo:
        a) Se captura la señal por medio de 2 electrodos.
        b) Se amplifica la señal (original de aprox. 1 mV pico a pico), referenciándola entre 0 y 3.3 V.
        c) Se filtra la señal:
            I) Filtro pasaaltas a 0.5 Hz (elimina ruido causado por la respiración).
            II) Filtro pasabajas a 50 o 60 Hz (elimina ruido de AC y radiofrecuencias).
            Motivo: los datos importantes del ECG (señal) suelen estar en frecuencias entre 0.8 Hz y 40 Hz.
        d) Se digitaliza a 360 muestras por segundo y aprox. 10 bits de profundidad.
        e) Se envía vía puerto serie al PC (muestra a muestra como un entero positivo entre 0 y 1000).
        f) Se captura usando software (Python) la representación digital de la señal y, sabiendo que se toman 360 muestras por segundo, se almacena un búfer de 6 s.
        g) Se filtra la señal digitalmente con un pasabanda entre 0.5 y 50 Hz.
        h) Se grafica la señal en el tiempo.

    3. Demostración:
        a) Conectar electrodos.
        b) Correr el programa y elegir el puerto serie.
        c) Hacer el plot en tiempo real hasta que se estabilice la señal.
        d) Tomar captura.
        e) Mostrar el ECG en formato “típico”.
