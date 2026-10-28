// Simulates a PAL in the socket and checks that the shield pin map gives the same dump as the original wiring.
// Build: see run.sh. Socket wiring and the test PAL functions are described in README.md (this folder).
#include "Arduino.h"
#include <map>

uint8_t simRegs[256];
SimSerial Serial;
int simType = 16;  // 16 = PAL16L8, 20 = PAL20L8

struct Line { char port; uint8_t bit; bool probed; };
static std::map<int, Line> wiring() {  // PAL pin -> MCU line
  std::map<int, Line> w;
  for(int p = 1; p <= 8; p++) w[p] = {'A', (uint8_t)(p - 1), false};
  if(simType == 16) {
#if PALDUMP_SHIELD
    w[9] = {'C', 0, false};
    w[11] = {'K', 0, false};
    for(int p = 12; p <= 18; p++) w[p] = {'K', (uint8_t)(p - 11), true};
    w[19] = {'C', 4, true};
#else
    w[9] = {'C', 0, false};
    w[11] = {'C', 1, false};
    for(int p = 12; p <= 19; p++) w[p] = {'K', (uint8_t)(p - 12), true};
#endif
  }
  else {
    int c[6] = {9, 10, 11, 14, 23, 13};
    for(int i = 0; i < 6; i++) w[c[i]] = {'C', (uint8_t)i, PALDUMP_SHIELD && c[i] == 23};
    for(int p = 15; p <= 22; p++) w[p] = {'K', (uint8_t)(p - 15), true};
  }
  return w;
}

static uint8_t &ddr(char p) { return p == 'A' ? DDRA : p == 'C' ? DDRC : p == 'K' ? DDRK : DDRG; }
static uint8_t &port(char p) { return p == 'A' ? PORTA : p == 'C' ? PORTC : p == 'K' ? PORTK : PORTG; }

// level the MCU side puts on a line: own output, else the probe through 1k, else 0
static int drive(const Line &l) {
  if(ddr(l.port) >> l.bit & 1) return port(l.port) >> l.bit & 1;
  if(l.probed && (DDRG & 4)) return (PORTG >> 2) & 1;
  return 0;
}

struct Out { int en, val; };
static std::map<int, Out> pal(std::map<int, int> &in) {
  std::map<int, Out> o;
  if(simType == 16) {
    o[12] = {1, !(in[1] & in[2])};
    o[13] = {in[3], in[4] ^ in[11]};
    o[14] = {1, in[5] | in[15]};
    o[19] = {1, (in[6] & !in[7]) | (in[16] & in[9])};
  }
  else {
    o[15] = {1, in[1] & in[23]};
    o[16] = {in[2], in[13] ^ in[14]};
    o[17] = {1, in[18] | in[10]};
    o[22] = {1, !(in[11] & in[19])};
  }
  return o;
}

uint8_t simPin(char p) {
  if(p == 'G') return (simType == 20) ? 0b10 : 0;  // 20/24 switch
  static std::map<int, Line> w = wiring();
  std::map<int, int> in;
  for(auto &e : w) in[e.first] = drive(e.second);
  std::map<int, Out> o = pal(in);
  uint8_t v = 0;
  for(int b = 0; b < 8; b++) {
    int level = 0;
    bool found = false;
    for(auto &e : w) {
      if(e.second.port != p || e.second.bit != b) continue;
      found = true;
      auto it = o.find(e.first);
      if(ddr(p) >> b & 1) level = port(p) >> b & 1;
      else if(it != o.end() && it->second.en) level = it->second.val;
      else level = drive(e.second);
    }
    if(!found) level = (ddr(p) >> b & 1) ? (port(p) >> b & 1) : 0;
    v |= level << b;
  }
  return v;
}

void setup();
int main() {
  setup();
  return 0;
}
