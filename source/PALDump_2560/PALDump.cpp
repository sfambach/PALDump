#include "PALDump.h"

PALDump::PALDump(PALType type, uint8_t maxTries) {
  if(maxTries > 4) maxTries = 4;
  if(maxTries < 1) maxTries = 1;
  maxRedundantReads = maxTries;
  currentPALType = type;
  currentCombination = 0;
  p3Shadow = 0;
  initPorts();
  for(uint8_t pin = 0; pin<8; pin++) {
    palPinConfig[pin] = Unknown;
  }
  palInputMask = 0;
  activeInputs = 0;
  activeOutputs = 0;
  IOMask = DIR_PAL16L8;
  switch(currentPALType) {
    case PAL16L8:
      maxCombinations = 65536;
      maxInputs = 16;
      break;
    case PAL20L8:
      maxCombinations = 1048576;
      maxInputs = 20;
      break;
  }
}

/*
void PALDump::getCombinatorialOutputAsText(uint32_t combination, char *buffer) {
  
}
void PALDump::getCombinatorialOutputAsText(char *buffer) {
  
}

uint16_t PALDump::getCombinatorialOutput(uint32_t combination) {
  switch(currentPALType) {
    case PAL16L8:
      break;
    case PAL20L8:
      break;
  }
}
*/
char PALDump::readPALPin(uint32_t combination, uint8_t bit) {
  char res = '-';
  posMask = 1<<(bit-1);
  negMask = posMask ^ 255;
  switch(currentPALType) {
    case PAL16L8:
      p1Write(BYTE1(combination));
      p2Write(BYTE2(combination) & 0b00000011);
      p3Shadow = BYTE2(combination)>>1;
      break;
    case PAL20L8:
      uint16_t ccopy;
      LO8(ccopy) = BYTE2(combination);
      HI8(ccopy) = BYTE3(combination);
      ccopy <<= 3;
      p1Write(BYTE1(combination));
      p2Write(BYTE2(combination));
      p3Shadow = HI8(ccopy);
      break;
  }
  p3Write(p3Shadow & IOMask & negMask);
  p3Ddr(IOMask & negMask);
  
  DDR(PROBEPORT) |= 1<<PROBEPIN;
  PROBEPORT |= 1<<PROBEPIN;
  if((p3Read()&posMask) == 0) res = '0';
  PROBEPORT &= (1<<PROBEPIN)^255;
  if((p3Read()&posMask) != 0) res = '1';
  DDR(PROBEPORT) &= (1<<PROBEPIN) ^ 255;
  p3Ddr(0);
  p3Write(0);
  return res;
}
/*
uint16_t PALDump::getCombinatorialOutput() {
  return getCombinatorialOutput(sequentialCombination());
}
void PALDump::setCombination(uint32_t combination) {
  currentCombination = combination;
}
uint32_t PALDump::sequentialCombination() {
  uint32_t o = currentCombination++;
  currentCombination &= (maxCombinations-1);
}
*/
void PALDump::assumeSimple14i8o() {
Serial.println("# Assumed 14 In / 8 Out configuration, no OE");
  activeOutputs = 8;
  activeInputs = 14;
  for(uint8_t i = 0; i<8; i++) {
    palPinConfig[i] = Output;
  }
  palInputMask = 0x00003fff;
  
}

bool PALDump::analyzePAL() {
  Serial.println("# Please wait. Analyzing PAL...");
  return analyzeInputs() && analyzeOutputs();
}
bool PALDump::analyzeOutputs() {
  Serial.println("# Analyzing outputs...");
  uint32_t a, b, c, a2, b2, c2;
  uint8_t success;
  a = 0; b = 0; c = 0; a2 = 0; b2 = 0; c2 = 0; success = 0;
  char pinState;
  for(uint8_t curPin = 8; curPin>0; curPin--) {
Serial.print("# Output "); Serial.print(curPin, DEC); Serial.print(" ");
    for(uint8_t t = 0; t<6; t++) {
      for(uint32_t comb = 0; comb<maxCombinations; comb++) {
        pinState = readPALPin(comb, curPin);
        switch(pinState) {
          case '-':
            a++;
            break;
          case '0':
            b++;
            break;
          case '1':
            c++;
            break;
        }
      }
      if(t>0) {
        if((a==a2)&&(b==b2)&&(c==c2)) success++;
        else success = 0;
      }
      else success++;
      a2 = a;
      b2 = b;
      c2 = c;
      a = 0; b = 0; c = 0;
      if(success>=maxRedundantReads) break;
    }
    if(success>=maxRedundantReads) {
      palPinConfig[curPin-1] = convertSumToPinType(a2);
      Serial.println(pinType(convertSumToPinType(a2)));
      switch(palPinConfig[curPin-1]) {
        case Output:
          activeOutputs++;
          break;
        case Buffered:
          activeOutputs += 2;
          break;
      }
    }
    else {
      Serial.print("Successful reads: "); Serial.println(success, DEC);
      return false;
    }
    success = 0;
  }
  return true;
}
bool PALDump::inputIsSignificant(uint8_t in) {
  uint32_t c, c2, pm, nm;
  uint16_t outs[2];
  uint8_t bit0, bitn;
  pm = (uint32_t)1<<in;
  nm = (pm ^ 0xffffffff) & 0xfffffffe;
//  Serial.print(" /"); Serial.print(pm, BIN); Serial.print("/"); Serial.print(nm, BIN); Serial.print("/");
  for(c = 0; c<maxCombinations; c++) {
      bit0 = c&1;
      if(in>0) {
        if((c&pm) != 0) bitn = 1; else bitn = 0;
        c2 = c & nm;
        c2 |= bitn;
        if(bit0 == 1) c2 |= pm;
      }
      else {
        c2 = c;
      }
      outs[bit0] = 0;
    outs[bit0] = getPort(c2).port;
    if(bit0 == 1) {
      if(outs[0] != outs[1]) {
//        Serial.print(" ("); Serial.print(c, BIN); Serial.print(","); Serial.print(c2, BIN); Serial.print(") ");
//        Serial.print(" ("); Serial.print(c2, DEC); Serial.print(") ");
        return true;
      }
    }
  }
  return false;
}
uint32_t PALDump::getPALInputMask() {
  if(palInputMask == 0) {
      analyzeInputs();
  }
  return palInputMask;
}
bool PALDump::analyzeInputs() {
  Serial.println("# Analyzing inputs...");
  palInputMask = 0;
  uint32_t checker = 1;
  activeInputs = 0;
  for(uint8_t i = 0; i < maxInputs; i++) {
    Serial.print("# Input "); Serial.print(i+1, DEC);
    if(inputIsSignificant(i)) {
      Serial.println(" OK");
      palInputMask |= checker;
      activeInputs++;
    }
    else {
      Serial.println(" doesn't matter");
    }
    checker = (uint32_t)checker << 1;
  }

  uint8_t tmp = palInputMask>>(maxInputs-7);
  IOMask &= (tmp | 0b10000001);
  if(palInputMask != 0) return true; else return false;
}
uint8_t PALDump::getActiveOutputs() {
  return activeOutputs;
}
uint8_t PALDump::getActiveInputs() {
  return activeInputs;
}
uint8_t PALDump::getMaxInputs() {
  return maxInputs;
}
uint32_t PALDump::shortToLongCombination(uint32_t combination) {
  volatile uint32_t res = 0;
  volatile uint32_t inputList = palInputMask;
  volatile uint32_t mask = 1;
  for(uint8_t i = 0; i<activeInputs; i++) {

    while((inputList & 1) == 0) {
      inputList >>= 1;
      res |= mask;
      mask <<= 1;
    }
    if((combination & 1) == 1) res |= mask;
    combination >>= 1;
    mask <<= 1;
    inputList >>= 1;
  }

  return res;
}
PALDump::PALWord PALDump::getPort(uint32_t combination) {
  volatile uint8_t p3Template;
  PALWord res;
  res.port = 0xffff;
  switch(currentPALType) {
    case PAL16L8:
      p1Write(LO8(combination));
      p2Write(HI8(combination));
      p3Template = (HI8(combination)>>1) & DIR_PAL16L8;
      break;
    case PAL20L8:
      uint16_t ccopy;
      LO8(ccopy) = BYTE2(combination);
      HI8(ccopy) = BYTE3(combination);
      ccopy <<= 3;
      p1Write(BYTE1(combination));
      p2Write(BYTE2(combination));
      p3Template = HI8(ccopy);
      break;
  }

  DDR(PROBEPORT) |= 1<<PROBEPIN;

  /* Intentionally made with no loops for better performance! */
  // bit 7
  p3Write(0b01111111 & p3Template);
  p3Ddr(0b01111111 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b10000000) == 0) res.oe8 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b10000000) != 0) res.output8 = 0;

  // bit 6
  p3Write(0b10111111 & p3Template);
  p3Ddr(0b10111111 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b01000000) == 0) res.oe7 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b01000000) != 0) res.output7 = 0;

  // bit 5
  p3Write(0b11011111 & p3Template);
  p3Ddr(0b11011111 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b00100000) == 0) res.oe6 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b00100000) != 0) res.output6 = 0;

  // bit 4
  p3Write(0b11101111 & p3Template);
  p3Ddr(0b11101111 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b00010000) == 0) res.oe5 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b00010000) != 0) res.output5 = 0;

  // bit 3
  p3Write(0b11110111 & p3Template);
  p3Ddr(0b11110111 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b00001000) == 0) res.oe4 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b00001000) != 0) res.output4 = 0;

  // bit 2
  p3Write(0b11111011 & p3Template);
  p3Ddr(0b11111011 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b00000100) == 0) res.oe3 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b00000100) != 0) res.output3 = 0;

  // bit 1
  p3Write(0b11111101 & p3Template);
  p3Ddr(0b11111101 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b00000010) == 0) res.oe2 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b00000010) != 0) res.output2 = 0;

  // bit 0
  p3Write(0b11111110 & p3Template);
  p3Ddr(0b11111110 & DIR_PAL16L8);
  PROBEPORT |= 1<<PROBEPIN;
  NOP;
  if((p3Read()&0b00000001) == 0) res.oe1 = 0;
  PROBEPORT &= (1<<PROBEPIN)^255;
  NOP;
  if((p3Read()&0b00000001) != 0) res.output1 = 0;

  DDR(PROBEPORT) &= (1<<PROBEPIN) ^ 255;
  p3Ddr(0);
  p3Write(0);

  return res;
}
PALDump::palPinType PALDump::convertSumToPinType(uint32_t sum) {
  switch(currentPALType) {
    case PAL16L8:
      switch(sum) {
        case 0:
          return Output;
        case 65536:
          return Input;
        default:
          return Buffered;
      }
      break;
    case PAL20L8:
      switch(sum) {
        case 0:
          return Output;
        case 1048576:
          return Input;
        default:
          return Buffered;
      }
      break;
    
  }
}
PALDump::palPinType *PALDump::getPALConfig() {
  for(uint8_t pin = 0; pin<8; pin++) {
    palPinConfigCopy[pin] = palPinConfig[pin];
  }
  return (palPinType *)palPinConfigCopy;
}
const char *PALDump::pinType(PALDump::palPinType t) {
  const char * names[4] = {"Output", "Tri-state Output", "Input", "Unknown"};
  return names[(uint8_t)t];
}

/*
 * Port layer (added for the PALDump shield by Stefan Fambach, see README "Shield").
 * The analysis works on three virtual 8-bit ports: P1 and P2 drive PAL inputs, P3 holds the eight pins that can be
 * outputs. On the original wiring they are PORTA, PORTC and PORTK one to one. The shield has a single 24-pin ZIF
 * socket and a 20-pin PAL sits flush with pin 1, so for PAL16L8 the pins above 10 move up by four contacts:
 *
 *   PAL16L8 on the shield:  P1 -> PORTA,  P2.0 -> PC0 (pin 9),  P2.1 -> PK0 (pin 11),
 *                           P3.0..6 -> PK1..PK7 (pins 12-18),  P3.7 -> PC4 (pin 19)
 *   PAL20L8 on the shield:  P1 -> PORTA,  P2.0..5 -> PC0..PC5,  P3 -> PORTK  (same as the original wiring)
 */
void PALDump::initPorts() {
  DDRA = 0xff;
  if(shieldLayout && currentPALType == PAL16L8) {
    DDRC = 0b00000001; PORTC = 0;  // PC1-PC3, PC5: contacts 10/11/13/14 have no 20-pin PAL pin
    DDRK = 0b00000001; PORTK = 0;  // PK0 = pin 11 (input I10)
  }
  else {
    DDRC = shieldLayout ? 0b00111111 : 0xff;
    DDRK = 0;
  }
}
