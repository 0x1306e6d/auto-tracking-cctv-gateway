import enum
import struct


class Opcode(enum.Enum):
    SETUP = 0x01
    RECORD = 0x10
    PAUSE = 0x11
    FRAME = 0x12
    MOVE_REQUEST = 0x20
    MOVE_RESPONSE = 0x21


def encode_packet(opcode, body=None):
    if not body:
        body = bytes()

    opcode = struct.pack('!H', opcode.value)

    opcode_size = len(opcode)
    body_size = len(body)

    packet_size = opcode_size + body_size
    packet_size = struct.pack('!L', packet_size)
    packet = packet_size + opcode + body

    return packet


def decode_packet(packet):
    opcode_size = struct.calcsize('!H')

    opcode = packet[:opcode_size]
    opcode = struct.unpack('!H', opcode)[0]
    opcode = Opcode(opcode)
    body = packet[opcode_size:]

    return opcode, body
