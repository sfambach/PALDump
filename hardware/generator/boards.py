# Netlist and placement of the PALDump shield for the Arduino Mega 2560.
# Pin map as in the firmware (source/PALDump_2560/PALDump.cpp, class PALPorts):
#   ZIF 1-8 = PA0-PA7 (D22-D29), ZIF 9/10/11/14/23/13 = PC0-PC5 (D37-D32), ZIF 15-22 = PK0-PK7 (A8-A15),
#   probe = PG2 (D39), 20/24 switch = PG1 (D40), RUN LED = PG0 (D41).
# A 20-pin PAL sits flush with pin 1 of the 24-pin ZIF socket, so VCC is contact 24 for both sizes; contact 10 is GND for
# a 20-pin PAL and an input for a 24-pin PAL, switched by S2.
NC = None
POWER = {'+5V', 'GND', 'VCC'}

RPACK = 'Package_DIP:DIP-16_W7.62mm_Socket'
SIP10 = 'Resistor_THT:R_Array_SIP10'
ZIF = 'Socket:DIP_Socket-24_W4.3_W5.08_W7.62_W10.16_W10.9_3M_224-5248-00-0602J'
DPDT = 'Button_Switch_THT:SW_CK_JS202011CQN_DPDT_Straight'
R = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'
LED = 'LED_THT:LED_D3.0mm'
C100N = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
C10U = 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm'

UNO_PINS = ['3V3', '5V1', '5V2', 'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'AREF', 'D0', 'D1', 'D10', 'D11', 'D12', 'D13', 'D2', 'D3',
            'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'GND1', 'GND2', 'GND3', 'GND4', 'IORF', 'MISO', 'MOSI', 'RST1', 'RST2', 'SCK',
            'SCL', 'SDA', 'VIN']
MEGA_PINS = UNO_PINS + ['5V3', '5V4', 'A6', 'A7', 'A8', 'A9', 'A10', 'A11', 'A12', 'A13', 'A14', 'A15', 'GND5', 'GND6'] + \
    ['D%d' % i for i in range(14, 54)]

# ZIF contact -> port line; the series resistor sits between the two.
LINES = {**{s: 'PA%d' % (s - 1) for s in range(1, 9)},
         9: 'PC0', 10: 'PC1', 11: 'PC2', 14: 'PC3', 23: 'PC4', 13: 'PC5',
         **{s: 'PK%d' % (s - 15) for s in range(15, 23)}}
PROBED = ['PK%d' % i for i in range(8)] + ['PC4']  # lines that can carry a PAL output

mega = {'5V1': '+5V', '5V3': '+5V', '5V4': '+5V', 'GND1': 'GND', 'GND2': 'GND', 'GND3': 'GND', 'GND5': 'GND',
        'GND6': 'GND', 'RST1': 'RESET', 'D39': 'PROBE', 'D40': 'MODE', 'D41': 'RUN'}
for i in range(8):
    mega['D%d' % (22 + i)] = 'PA%d' % i
    mega['D%d' % (37 - i)] = 'PC%d' % i if i < 6 else NC
    mega['A%d' % (8 + i)] = 'PK%d' % i


def zif_net(s):
    return 'ZIF10_IO' if s == 10 else 'ZIF%d' % s


def rpack(pairs):
    """R_Pack08: resistor k between pin k (port side) and pin 17-k (socket side); pairs = 8 x (port, socket) or None."""
    conn = {}
    for k, pr in enumerate(pairs, 1):
        conn[str(k)], conn[str(17 - k)] = pr if pr else (NC, NC)
    return conn


zif = {'12': 'GND', '24': 'VCC', **{str(s): 'ZIF%d' % s for s in LINES}}
rn1 = rpack([('PA%d' % i, 'ZIF%d' % (i + 1)) for i in range(8)])
rn2 = rpack([('PK%d' % i, 'ZIF%d' % (15 + i)) for i in range(8)])
by_port = {v: k for k, v in LINES.items()}
rn3 = rpack([None, None] + [('PC%d' % i, zif_net(by_port['PC%d' % i])) for i in (5, 4, 3, 2, 1, 0)])
rn4 = {'1': 'PROBE', **{str(k + 2): 'PK%d' % (7 - k) for k in range(8)}, '10': 'PC4'}

# Schematic: (lib_id, value, footprint, (x, y), pin -> net)
PARTS = {
    'A1': ('arduino-library:Arduino_Mega2560_R3_Shield', 'Arduino Mega 2560 R3', 'arduino-library:Arduino_Mega2560_R3_Shield',
           (88.9, 152.4), {n: mega.get(n) for n in MEGA_PINS}),
    'RN1': ('Device:R_Pack08', '270', RPACK, (152.4, 138.43), rn1),
    'RN3': ('Device:R_Pack08', '270', RPACK, (170.18, 163.83), rn3),
    'U1': ('paldump:ZIF24_PAL', 'ZIF 24 narrow', ZIF, (198.12, 142.24), zif),
    'RN2': ('Device:R_Pack08', '270', RPACK, (233.68, 140.97), rn2),
    'RN4': ('Device:R_Network09', '1k', SIP10, (264.16, 143.51), rn4),
    'S2': ('Switch:SW_DPDT_x2', '20/24 pin', DPDT, (175.26, 190.5),
           {'1': 'GND', '2': 'ZIF10', '3': 'ZIF10_IO', '4': 'GND', '5': 'MODE', '6': NC}),
    'S1': ('Switch:SW_DPDT_x2', 'PAL power', DPDT, (35.56, 228.6),
           {'1': '+5V', '2': 'VCC', '3': 'GND', '4': NC, '5': 'RESET', '6': 'GND'}),
    'R1': ('Device:R', '1k', R, (215.9, 205.74), {'1': 'VCC', '2': 'LED_VCC'}),
    'D1': ('Device:LED', 'red', LED, (226.06, 215.9), {'1': 'GND', '2': 'LED_VCC'}),
    'R2': ('Device:R', '1k', R, (241.3, 205.74), {'1': 'RUN', '2': 'LED_RUN'}),
    'D2': ('Device:LED', 'green', LED, (251.46, 215.9), {'1': 'GND', '2': 'LED_RUN'}),
    'C1': ('Device:C', '100n', C100N, (266.7, 210.82), {'1': 'VCC', '2': 'GND'}),
    'C2': ('Device:C_Polarized', '10u', C10U, (279.4, 210.82), {'1': 'VCC', '2': 'GND'}),
}
SCH = dict(
    rot={'RN1': 270, 'RN3': 270, 'RN2': 90, 'RN4': 270, 'D1': 90, 'D2': 90},
    units={'S2': [(175.26, 190.5), (175.26, 210.82)], 'S1': [(35.56, 228.6), (35.56, 248.92)]},
    order=['RUN', 'MODE', 'RESET', 'PROBE', 'ZIF10', 'ZIF10_IO'],
)

X0, Y0 = 100, 153.34  # origin of the shield footprint = lower left corner of the Arduino

SHIELD = dict(
    name='paldump-shield',
    title='PALDump shield for Arduino Mega 2560',
    note='PAL dumper shield (PALDump by Dmitry Shtatnov, github.com/rpocc/PALDump). One 24-pin ZIF socket:\n'
         '20-pin PALs (PAL10L8, PAL16L8) flush with pin 1, S2 on "20"; 24-pin PALs (PAL20L8) S2 on "24".\n'
         'S1 off = PAL unpowered and Arduino held in reset; S1 on = dump starts. Every contact has a 270R series resistor,\n'
         'contacts 15-23 can carry PAL outputs and get a 1k to the probe line (tri-state detection).\n'
         'github.com/sfambach/PALDump - fambach.net - hardware CERN-OHL-S-2.0',
    power=['+5V', 'GND', 'VCC'],
    board=(X0, Y0 - 53.34, X0 + 101.6, Y0),
    parts=PARTS, sch=SCH,
    # The Mega's ICSP header pokes through the shield (pads stay, unconnected); keep its area free.
    place={
        'A1': ('origin', (X0, Y0), 0),
        'U1': ('at', (127.0, 120.0), 90),
        'RN1': ('at', (119.38, 134.62), 90),
        'RN3': ('at', (142.24, 134.62), 90),
        'RN2': ('at', (177.8, 124.46), 180),
        'RN4': ('at', (186.69, 106.68), 270),
        'S1': ('at', (119.38, 140.97), 0),
        'S2': ('at', (130.81, 140.97), 0),
        'D1': ('pads', (141.605, 143.51), (141.605, 140.97)),
        'D2': ('pads', (146.685, 143.51), (146.685, 140.97)),
        'R1': ('pads', (151.13, 139.7), (158.75, 139.7)),
        'R2': ('pads', (151.13, 144.78), (158.75, 144.78)),
        'C1': ('pads', (170.18, 137.16), (175.18, 137.16)),
        'C2': ('pads', (180.34, 137.16), (182.34, 137.16)),
    },
    texts=[('PALDump shield v0.1', 150.0, 105.6, 1.2)],
    btexts=[('PALDump shield v0.1 - fambach.net', 150, 125, 1.0), ('github.com/sfambach/PALDump', 150, 127.5, 0.8),
            ('CERN-OHL-S-2.0', 150, 129.6, 0.8)],
)

BOARDS = {'shield': SHIELD}
