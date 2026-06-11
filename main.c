#include <Arduino.h>


//-- GPIO Definitions -//
#define LED_D1      6     // LED D1 pin 6
#define LED_RGB     48    // LED RGB pin 48
#define BTN_S1      4     // Bouton S1 pin 4
#define BTN_S2      5     // Bouton S2 pin 5

//--- Variables anti-rebond + detection flancs --//
int lastS1 = HIGH;        // Etat précédent de S1 état HIGH
int lastS2 = HIGH;        // Etat précédent de S2 état  HIGH

unsigned long debounce;   // Anti rebond pour S1 et S2
//-- Variables d'etats --//
bool stateLed = false;    // Etat de la LED D1 à false
int stateRgb = 0;         // Etat de la LED RGB à 0

//-- PROTOTYPES DE FONCTIONS --//
void updateRBG();

//-- INITIALISATION --//
void setup()
{
  Serial.begin(115200);

  // Sélectionne le mode de chaque pin (entrée / sortie)
  pinMode(LED_D1, OUTPUT);
  pinMode(BTN_S1, INPUT_PULLUP);
  pinMode(BTN_S2, INPUT_PULLUP);

  // Mets à jour la LED RGB
  updateRBG();
}

//-- BOUCLE INFINIE --//
void loop() 
{
  int S1 = digitalRead(BTN_S1);
  int S2 = digitalRead(BTN_S2);

  // Si un appui sur S1 a été detecté
  if(lastS1 == HIGH && S1 == LOW)
  {
    // Attends 30ms
    delay(30);

    // Inverse l'état de la LED
    stateLed = !stateLed;
    // Affiche l'état de la LED (Allumée / Eteinte)
    digitalWrite(LED_D1, stateLed);
  }

  // Si un appui sur S2 a été detecté
  if(lastS2 == HIGH && S2 == LOW)
  {
    // Attends 30ms
    delay(30);

    // Compteur ne dépassant pas 2 (machine état -> updateRGB)
    stateRgb = (stateRgb + 1) % 3;
    // Met a jour la LED RGB
    updateRBG();
  }

  // Mets a jour l'état de boutons S1 et S2
  lastS1 = S1;
  lastS2 = S2;

}

//-- FONCTIONS --//
void updateRBG()
{
  //-- Machine d'état
  switch(stateRgb)
  {
    case 0:
      // Allume la couleure rouge avec une faible intensité
      neopixelWrite(LED_RGB, 10, 0, 0);
      break;
    case 1:
      // Allume la couleure verte avec une faible intensité
      neopixelWrite(LED_RGB, 0, 10, 0);
      break;
    case 2:
      // Allume la couleure bleue avec une faible intensité
      neopixelWrite(LED_RGB, 0, 0, 10);
      break;
  }
}
