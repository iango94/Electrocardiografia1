const int ecgPin = A0;
const int loPlus = 10;
const int loMinus = 11;

volatile bool sampleReady = false;

// interrupción Timer1
ISR(TIMER1_COMPA_vect) {
  sampleReady = true;
}

void setup() {
  analogReference(EXTERNAL);

  Serial.begin(115200);

  pinMode(loPlus, INPUT);
  pinMode(loMinus, INPUT);

  // configuración Timer1
  cli();

  TCCR1A = 0;
  TCCR1B = 0;
  TCNT1 = 0;

  // modo CTC
  TCCR1B |= (1 << WGM12);

  // prescaler 64
  TCCR1B |= (1 << CS11) | (1 << CS10);

  // 16MHz / 64 / 360Hz ≈ 694
  OCR1A = 694;

  // habilitar interrupción
  TIMSK1 |= (1 << OCIE1A);

  sei();
}

void loop() {

  if (sampleReady) {

    sampleReady = false;

    if (digitalRead(loPlus) || digitalRead(loMinus)) {
      Serial.println(0);
    }
    else {
      int ecg = analogRead(ecgPin);
      Serial.println(ecg);
    }

  }
}