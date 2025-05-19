// Librerías a implementar
#include <Wire.h>                             // Libreria para comunicación I2C
#include <Adafruit_INA219.h>                  // Librería para control del sensor de corriente
#include <Adafruit_MLX90614.h>                // Librería para control del sensor de temperatura
#include "PWM.h"                              // Librería para configuración del PWM
#include "VernierSensor.h"                    // Librería para control del sensor de fuerza
#include <ArduinoJson.h>                      // Librería para manejar JSON

// Constantes del programa
const uint8_t PWM_D10_PIN = D10;              // La señal de PWM se asigna al Pin 10
const uint8_t relayPin = 11;                  // La señal del relevador se asigna al Pin 11
const int NUM_SAMPLES = 20;                   // Numero de muestras a promediar
const unsigned long INTERVAL_MS = 100;        // Intervalo de muestreo en milisegundos
enum State { IDLE, RUNNING, DEBUG };          // Estados del programa
State currentState = IDLE;                    // Estado actual

// Instancias
VernierSensor Vernier;                        // Instancia de la librería de Vernier
Adafruit_INA219 ina219_SMA(0x41);             // Sensor de corriente SMA
Adafruit_INA219 ina219_ref(0x44);             // Sensor de tensión de referencia
Adafruit_MLX90614 mlx = Adafruit_MLX90614();  // Sensor de temperatura
PwmOut objPWMD10(PWM_D10_PIN);                // Instancia de la salida PWM

// Variables del programa
unsigned long lastMillis = 0;                 // Variable para monitoreo del tiempo entre lecturas
unsigned long experimentStartTime = 0;        // Tiempo de inicio del experimento
unsigned long experimentDuration = 0;         // Duración total del experimento (activo + reposo)
unsigned long activeTime = 0;                 // Tiempo activo en milisegundos
unsigned long restTime = 0;                   // Tiempo en reposo en milisegundos
bool experimentRunning = false;               // Flag para indicar si el experimento está en curso
bool isRelayActive = false;                   // Estado del relé
String inputBuffer = "";                      // Buffer para recibir datos por Serial
bool commandComplete = false;                 // Flag para indicar que un comando está completo

// Configuración del ARDUINO
void setup() {
  // Comunicación Serial
  Serial.begin(115200);                       // Inicializa la comunicación serial
  while (!Serial) {                           // Espera a que inicie la comunicación
      delay(1);                          
  }

  // Configuración PINOUT
  pinMode(relayPin, OUTPUT);                  // Configura el pin del relevador como salida
  digitalWrite(relayPin, LOW);                // Inicializa el relevador como apagado  

  // Configuración PWM para control del ventilador
  pinMode(PWM_D10_PIN, OUTPUT);               // Configura el pin de PWM como salida
  objPWMD10.begin(25000.0f, 0.0f);            // Inicializa el PWM con 0 y frecuencia de 25 kHz  

  // Inicialización de los modulos
  // Identificación del sensor de fuerza
  Vernier.autoID();
  
  // Sensor de corriente del SMA
  if (! ina219_SMA.begin()) {
    Serial.println("{\"error\":\"Failed to find SMA current chip\"}");
  }
  
  // Sensor de corriente para referencia
  if (! ina219_ref.begin()) {
    Serial.println("{\"error\":\"Failed to find current reference chip\"}");
  }
  
  // Sensor de temperatura MOSFET
  if (!mlx.begin()) {
    Serial.println("{\"error\":\"Error connecting to MLX sensor. Check wiring.\"}");
  } 

}

void loop() {
  // Espera un comando por serial
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    handleCommand(command);
  }

  unsigned long currentMillis = millis();

  // Envía o actualiza cada INTERVAL_MS
  if (currentMillis - lastMillis >= INTERVAL_MS) {
    lastMillis = currentMillis;
    sendSensorData();  // ejecuta siempre, pero filtra internamente
  }

  // Lógica del experimento
  if (currentState == RUNNING) {
    unsigned long elapsed = currentMillis - experimentStartTime;

    if (elapsed < activeTime) {
      setRelay(true);
    }
    else if (elapsed < activeTime + restTime) {
      setRelay(false);
    }
    else {
      currentState = IDLE;
      setRelay(false);
      Serial.println("TERMINATED");
    }
  }
}

// Procesamiento de los comandos
void handleCommand(String command) {
  // Valida la comunicación serial
  if (command == "VALIDATE") {
    // Retorna el mensaje "VALIDATED"
    Serial.println("VALIDATED");
  }
  // Comienza el experimento
  else if (command.startsWith("START")) {
    if (currentState == IDLE){
      int firstSpace = command.indexOf(' ');
      int secondSpace = command.indexOf(' ', firstSpace + 1);

      if (firstSpace > 0 && secondSpace > firstSpace) {
        activeTime = command.substring(firstSpace + 1, secondSpace).toInt();
        restTime = command.substring(secondSpace + 1).toInt();
        experimentStartTime = millis();
        lastMillis = experimentStartTime;
        currentState = RUNNING;
      }
    }
  }
  else if (command == "STOP") {
    if (currentState == RUNNING){
      currentState = IDLE;
      setRelay(false);
    }
  }
  else if (command == "DEBUG") {
    if (currentState == IDLE){
      currentState = DEBUG;
      lastMillis = millis();
    }
  }
  else if (currentState == DEBUG) {
    if (command == "RELAY_ON") {
      setRelay(true);
      Serial.print("DEBUG STATUS: RELAY ");
      Serial.println(isRelayActive ? "ON" : "OFF");
    }
    else if (command == "RELAY_OFF") {
      setRelay(false);
      Serial.print("DEBUG STATUS: RELAY ");
      Serial.println(isRelayActive ? "ON" : "OFF");
    }
    else if (command == "DEBUGEND") {
      currentState = IDLE;
      setRelay(false);
      Serial.print("DEBUG ENDED...\nSTATUS: RELAY ");
      Serial.println(isRelayActive ? "ON" : "OFF");
    }
  }
}

// Modifica el estado del relevador
void setRelay(bool state) {
  isRelayActive = state;
  digitalWrite(relayPin, state ? HIGH : LOW);
}

// Envía datos de los sensores en formato JSON
void sendSensorData() {
  // Inicialización de las variables a leer
  float sumCurrent_SMA = 0;     
  float sumBusVoltage_SMA = 0; 
  float sumBusVoltage_ref = 0;  
  float sumMosfetTemp = 0;     
  long fanOut = 0;              
  
  // Obtención de lecturas
  for (int i = 0; i < NUM_SAMPLES; i++) {
    sumCurrent_SMA += ina219_SMA.getCurrent_mA();  
    sumBusVoltage_SMA += ina219_SMA.getBusVoltage_V();
    sumBusVoltage_ref += ina219_ref.getBusVoltage_V();
    sumMosfetTemp += mlx.readObjectTempC();    
    delay(1);
  }

  // Promedio de las mediciones
  float avgCurrent_SMA = ((sumCurrent_SMA * 10) / NUM_SAMPLES);
  float avgBusVoltage_SMA = sumBusVoltage_SMA / NUM_SAMPLES;
  if (!isRelayActive){
    avgCurrent_SMA = 0.0;
    avgBusVoltage_SMA = 0.0;
  }
  float avgBusVoltage_ref = sumBusVoltage_ref / NUM_SAMPLES;
  float avgMosfetTemp = sumMosfetTemp / NUM_SAMPLES;
  float avgForce = Vernier.readSensor();
  float avgMosfetTemp_aux = constrain(avgMosfetTemp, 20, 70);

  // Actualiza el PWM del ventilador para enfriar el MOSFET
  fanOut = map(avgMosfetTemp_aux, 20, 70, 0, 100);
  objPWMD10.pulse_perc(fanOut);

  // Solo imprimir si estamos en DEBUG o RUNNING
  if (currentState == DEBUG || currentState == RUNNING) {
    Serial.print("{");
    Serial.print("\"current_mA\":"); Serial.print(avgCurrent_SMA, 3); Serial.print(",");
    Serial.print("\"force_N\":"); Serial.print(avgForce, 3); Serial.print(",");
    Serial.print("\"busVoltage_SMA_V\":"); Serial.print(avgBusVoltage_SMA, 3); Serial.print(",");
    Serial.print("\"busVoltage_ref_V\":"); Serial.print(avgBusVoltage_ref, 3); Serial.print(",");
    Serial.print("\"relay_state\":"); Serial.print(isRelayActive);
    Serial.println("}");
  }
}
