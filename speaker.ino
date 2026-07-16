const int BUZZER_PIN = 8;

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    char incomingByte = Serial.read();

    if (incomingByte == 'B') {
      // Pin, Frequency (1000Hz), Duration (200ms)
      // This fires the PWM timer and instantly moves to the next line
      tone(BUZZER_PIN, 1000, 200);
    }

    if (incomingByte == 'B') {
      // Pin, Frequency (2000Hz), Duration (200ms)
      // This fires the PWM timer and instantly moves to the next line
      tone(BUZZER_PIN, 2000, 200);
    }
  }
}