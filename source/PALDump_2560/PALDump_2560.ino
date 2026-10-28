#include <stdint.h>
#include "PALDump.h"

/*                                                                              
 PAL Dumper for Arduino MEGA 2560.
 A helper device allowing for dumping a complete truth table of combinatorial
 logic arrays currently including PAL16L8 and PAL20L8, including variations
 with different set of inputs and outputs.

 (See the full description in the README.md)

 Version: 1.4
 Release date: 01.03.2024
 Author: Dmitry Shtatnov (shtatnovda@yandex.ru)
 Date of initial publication: 25.02.2024
 Licence: CC BY-NC-SA 4.0 Deed

 PALDump shield support (one 24-pin ZIF socket, 20/24 switch on D40, RUN LED on D41):
 Stefan Fambach (SteFam), https://www.fambach.net, with Claude (Anthropic AI), 2026.
 Same licence (CC BY-NC-SA 4.0). See README.md, section "Shield".
 */


/* Original wiring (PALDUMP_SHIELD 0 in PALDump.h): uncomment one of the lines according to your needs.
   On the shield the 20/24 switch selects the type and this setting is ignored. */
#ifndef GLOBAL_PAL_TYPE
#define GLOBAL_PAL_TYPE PAL16L8
//#define GLOBAL_PAL_TYPE PAL20L8
#endif

// Ports used (fixed in PALDump.h): PORTA, PORTC, PORTK

// Shield: 20/24 switch on PG1 (D40, LOW = 20-pin), RUN LED on PG0 (D41)
#define MODE_BIT 1
#define RUN_LED_BIT 0

/*
The probe port is defined in PALDump.h.

Default:
#define PROBEPORT PORTG
#define PROBEPIN 2
*/


// Runs before setup(), because the PALDump object below is built with the type.
PALDump::PALType readPALType() {
  if(!shieldLayout) return PALDump::GLOBAL_PAL_TYPE;
  DDRG &= ~(1 << MODE_BIT);
  PORTG |= 1 << MODE_BIT;  // pull-up, the switch pulls to GND in position "20"
  for(volatile uint8_t i = 0; i < 100; i++);
  return (PING & (1 << MODE_BIT)) ? PALDump::PAL20L8 : PALDump::PAL16L8;
}

const PALDump::PALType globalPALType = readPALType();

// A single instance of the PALDump object
PALDump PLA(globalPALType, 1);

uint32_t totalCombinations;
uint8_t totalInputs;
uint8_t totalOutputs;
const uint8_t PAL16L8InPins[16] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 15, 16, 17, 18};
const uint8_t PAL20L8InPins[20] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 23, 13, 16, 17, 18, 19, 20, 21};
PALDump::palPinType *config;
uint32_t inputs;

void print_berkeley_header();
void print_berkeley_line(uint32_t combination, bool shortCombination = true);
void print_full_berkeley();

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  Serial.println("# PAL Reader by Dmitry Shtatnov. Version 1.3");
  if(shieldLayout) {
    DDRG |= 1 << RUN_LED_BIT;
    PORTG |= 1 << RUN_LED_BIT;
    Serial.println(globalPALType == PALDump::PAL16L8 ? "# PALDump shield, switch on 20 pin: PAL16L8 / PAL10L8 mode"
                                                     : "# PALDump shield, switch on 24 pin: PAL20L8 mode");
  }
 
// Full analysis. Time-consuming for PAL20L8
   PLA.analyzePAL();

/* The following line can be used instead of analysis when you're
   confident that all outputs are just plain outputs or the analysis
   result got this simple configuration.
*/
//  PLA.assumeSimple14i8o();

  config = PLA.getPALConfig();
  totalInputs = PLA.getActiveInputs();
  totalOutputs = PLA.getActiveOutputs();
  inputs = PLA.getPALInputMask();

  print_berkeley_header();
  print_full_berkeley();
  if(shieldLayout) PORTG &= ~(1 << RUN_LED_BIT);
  Serial.println("# Done.");
}

//#pragma GCC optimize ("-O0")
//#pragma GCC push_options

void print_berkeley_line(uint32_t combination, bool shortCombination) {
  
  char ptout[2];
  ptout[1] = 0;
  uint32_t l2, startBit;
  l2 = combination;
  uint8_t combinationLength;
  if(shortCombination) combinationLength = totalInputs;
  else combinationLength = PLA.getMaxInputs();
  startBit = (uint32_t)1 << (combinationLength-1);

  for(uint8_t j=0;j<combinationLength;j++) {
    if((uint32_t)((uint32_t)l2&(uint32_t)startBit) == 0) Serial.print("0");
    else Serial.print("1");
    startBit >>= 1;
  }
  Serial.print(" ");

  for(uint8_t j=8;j>0;j--) {
    if(config[j-1] != PALDump::Input) {
      if(shortCombination) ptout[0] = PLA.readPALPin(PLA.shortToLongCombination(combination), j);
      else ptout[0] = PLA.readPALPin(combination, j);
      if(config[j-1] == PALDump::Buffered) {
        if(ptout[0]=='-') Serial.write("10");
        else {
          Serial.write((const char*)&ptout);
          Serial.write("1");
        }
      }
      else Serial.write((const char*)&ptout);
    }
  }
  Serial.println();
  
}
// #pragma GCC pop_options

void print_berkeley_header() {
  Serial.println("# ---------------- BERKELEY OUTPUT ----------------");
  Serial.print(".i "); Serial.println(totalInputs, DEC);
  Serial.print(".o "); Serial.println(totalOutputs, DEC);
  Serial.print(".ilb");
  
  for(uint8_t i = 0; i<PLA.getMaxInputs(); i++) {
    switch(globalPALType) {
      case PALDump::PAL16L8:
        if((inputs & (1 << (15-i))) != 0) {
          Serial.print(" p");
          Serial.print(PAL16L8InPins[15-i], DEC);
        }
        break;
      case PALDump::PAL20L8:
        if((inputs & (1 << (19-i))) != 0) {
          Serial.print(" p");
          Serial.print(PAL20L8InPins[19-i], DEC);
        }
        break;
    }
  }
  Serial.println();
  Serial.print(".ob ");
  uint8_t last_out_pin;
  switch(globalPALType) {
    case PALDump::PAL16L8:
      last_out_pin = 19;
      break;
    case PALDump::PAL20L8:
      last_out_pin = 22;
      break;
  }
      
  for(uint8_t i = 0; i<8; i++) {
    switch(config[7-i]) {
      case PALDump::Output:
        Serial.print("p");
        Serial.print(last_out_pin-i, DEC);
        Serial.print(" ");
        break;
      case PALDump::Buffered:
        Serial.print("p");
        Serial.print(last_out_pin-i, DEC);
        Serial.print(" ");
        Serial.print("p");
        Serial.print(last_out_pin-i, DEC);
        Serial.print("_oe ");
        break;
      default:
        break;
    }
  }
  Serial.println();
  Serial.print(".phase ");
  for(uint8_t i = 0; i<8; i++) {
    switch(config[7-i]) {
      case PALDump::Output:
        Serial.print("0");
        break;
      case PALDump::Buffered:
        Serial.print("01");
        break;
      default:
        break;
    }
  }
  Serial.println();
}

void print_full_berkeley() {
  // Following line assigns nonsense without (uint32_t) cast.
  uint32_t totalCombinations = (uint32_t)1 << totalInputs;
  for(uint32_t l = 0; l<totalCombinations; l++) {
    print_berkeley_line(l, true);
  }
}

void loop() {
  // put your main code here, to run repeatedly:
while(true){}
}
