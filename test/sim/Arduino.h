// Host stand-in for the Arduino core: registers are plain bytes, PIN reads go through the simulated PAL (sim.cpp).
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define DEC 10
#define BIN 2
extern uint8_t simRegs[256];
uint8_t simPin(char port);
// PINx, DDRx, PORTx at consecutive addresses like on the AVR (PALDump.h uses DDR(x) = *(&x-1))
#define PINA simPin('A')
#define PINC simPin('C')
#define PINK simPin('K')
#define PING simPin('G')
#define DDRA simRegs[1]
#define PORTA simRegs[2]
#define DDRC simRegs[4]
#define PORTC simRegs[5]
#define DDRK simRegs[7]
#define PORTK simRegs[8]
#define DDRG simRegs[10]
#define PORTG simRegs[11]
#define __asm__ (void)
#define __volatile__(x) 0
struct SimSerial {
  void begin(long) {}
  void print(const char *s) { fputs(s, stdout); }
  void print(char c) { putchar(c); }
  void print(unsigned long v, int base = DEC) { if(base == BIN) { char b[40]; int n = 0; do { b[n++] = '0' + (v & 1); v >>= 1; } while(v); while(n) putchar(b[--n]); } else printf("%lu", v); }
  void print(int v, int base = DEC) { print((unsigned long)v, base); }
  void print(unsigned int v, int base = DEC) { print((unsigned long)v, base); }
  void print(long v, int base = DEC) { print((unsigned long)v, base); }
  void print(unsigned char v, int base = DEC) { print((unsigned long)v, base); }
  void println() { putchar('\n'); }
  template<typename T> void println(T v) { print(v); putchar('\n'); }
  template<typename T> void println(T v, int base) { print(v, base); putchar('\n'); }
  void write(const char *s) { fputs(s, stdout); }
};
extern SimSerial Serial;
