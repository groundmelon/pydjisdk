import ctypes
from ctypes import c_uint8, c_uint16, c_uint32, c_double, c_float, c_int16, c_int32
import collections
import base64
import crcmod
import collections
import struct
import AESCodec
import DataCodec.activation as DataCodecActivation
import DataCodec.control as DataCodecControl
import DataCodec.monitor as DataCodecMonitor

from utils import *

DEFAULT_KEY = 'e7666379497e235364d54c3ecdf1370cbfa009f72e15f6a64451f38e1e5b83ba'


header_field_table = (
    'sof', 'length', 'ver', 'session', 'ack', 'res0',
    'pad', 'enc', 'res1', 'seq', 'crc16')
header_type_table = (c_uint32, c_uint32, c_uint32, c_uint32,
                     c_uint32, c_uint32, c_uint32, c_uint32, c_uint32, c_uint32, c_uint32)
header_bitfield_table = (8, 10, 6, 5, 1, 2, 5, 3, 24, 16, 16)
header_struct_table = zip(
    header_field_table, header_type_table, header_bitfield_table)


class ProtocolHeaderStruct(ctypes.LittleEndianStructure):
    _fields_ = header_struct_table


class ProtocolHeaderUnion(ctypes.Union):
    _fields_ = [('buf', ctypes.ARRAY(c_uint8, 12)),
                ('data', ProtocolHeaderStruct)]

CHANGED = True
UNCHANGED = False
SOF = '\xAA'
VER = 0
HEADER_LEN = 12
ACK_FRAME = 1
DATA_FRAME = 0


class ProtocolHeader(object):

    def __init__(self, crc):
        self.u = ProtocolHeaderUnion()
        self.crc = crc

    def __getattr__(self, key):
        if key in header_field_table:
            return self.u.data.__getattribute__(key)
        else:
            return self.__getattribute__()

    def __repr__(self):
        s = ', '.join(['%s:%s' % (key, self.__getattr__(key))
                       for key in header_field_table])
        # s += '\n'
        # s += ' '.join(['{:08b}'.format(x) for x in self.u.buf])
        return s

    def is_valid(self):
        conditions = (self.u.data.sof == ord(SOF),
                      self.u.data.ver == VER,
                      self.u.data.res0 == 0,
                      self.u.data.res1 == 0,
                      self.crc_check_passed,
                      )
        # print conditions, self.d['RES0']
        return all(conditions)

    def parse(self, buf):
        for i in range(HEADER_LEN):
            self.u.buf[i] = ord(buf[i])

        self.crc.crcValue = self.crc.initCrc
        self.crc.update(buf[:10])
        self.crc_check_passed = (self.crc.crcValue == self.u.data.crc16)

    def render(self, **kwargs):
        pass

ACTIVATION_SET = dict((
    (0x00, DataCodecActivation.decode_acquire_api_version),
    (0x01, DataCodecActivation.decode_active_api)
))

CONTROL_SET = dict((
    (0x00, DataCodecControl.decode_acquire_control),
    (0x01, DataCodecControl.decode_task_control),
    (0x02, DataCodecControl.decode_task_inquire),
    (0x03, DataCodecControl.decode_atti_control),
))

MONITOR_SET = dict((
))

CMD_SET_S = dict((
    (0x00, ACTIVATION_SET),
    (0x01, CONTROL_SET),
    (0x02, MONITOR_SET),
))

ACTIVATION_SET = dict((
    (0x00, DataCodecActivation.decode_acquire_api_version_ack),
    (0x01, DataCodecActivation.decode_active_api_ack),
))

CONTROL_SET = dict((
    (0x00, DataCodecControl.decode_acquire_control_ack),
    (0x01, DataCodecControl.decode_task_control_ack),
    (0x02, DataCodecControl.decode_task_inquire_ack),
))

MONITOR_SET = dict((
    (0x00, DataCodecMonitor.decode_message),
))

CMD_SET_R = dict((
    (0x00, ACTIVATION_SET),
    (0x01, CONTROL_SET),
    (0x02, MONITOR_SET),
))

CMD_SET = CMD_SET_S
CMD_SET = CMD_SET_R


class ProtocolData(object):

    def __init__(self):
        self.buf = ''

    def parse(self, buf, is_ack):
        # print 'data:{}'.format(base64.b16encode(buf))
        self.buf = buf
        self.is_ack = is_ack
        if not self.is_ack:
            rst = struct.unpack('<BB', buf[:2])
            self.cmd_set = rst[0]
            self.cmd_id = rst[1]
        else:
            self.ack_data = struct.unpack('<H', buf[:2])[0]
        # print('command_set[%d] command_id[%d]' % (self.cmd_set, self.cmd_id))

        if not self.is_ack:
            CMD_SET[self.cmd_set][self.cmd_id](self.buf[2:])
        else:
            CMD_SET[0][1](self.ack_data, self.buf[2:])
            CMD_SET[1][0](self.ack_data, self.buf[2:])

    def render(self, **kwargs):
        pass


class ProtocolParser(object):

    def __init__(self):
        self.buf = collections.deque(maxlen=1000)
        self.state = 'IDLE'
        self.crc16 = crcmod.Crc(0x18005, 0x3AA3)
        self.crc32 = crcmod.Crc(0x104C11DB7, 0x3AA3)
        self.aes = AESCodec.AESCodec(DEFAULT_KEY)
        self.header = None
        self.parsed_size = 0

    def clear_randuant(self, idx):
        assert isinstance(idx, int) or isinstance(
            idx, long), "type(idx) should be {}, but is {}".format('int/long', str(type(idx)))
        for i in range(idx):
            self.buf.popleft()

    def process(self):
        if self.state == 'IDLE':
            header_parsed, header_addr = self.parse_header()
            if header_parsed:
                self.clear_randuant(header_addr)
                self.state = 'HEADER_PARSED'
                return CHANGED
            else:
                return UNCHANGED
        elif self.state == "HEADER_PARSED":
            data_collected = self.is_data_collected()
            if data_collected:
                self.state = 'DATA_COLLECTED'
                return CHANGED
            else:
                return UNCHANGED
        elif self.state == "DATA_COLLECTED":
            data_parsed, data_end_addr = self.parse_data()
            if data_parsed:
                self.clear_randuant(data_end_addr)
                self.state = 'IDLE'
                self.parsed_size += data_end_addr
                return CHANGED
            else:
                self.clear_randuant(data_end_addr)
                self.state = 'IDLE'
                return CHANGED

    def feed(self, s):
        self.buf.extend(s)
        while True:
            if self.process() == UNCHANGED:
                break

    def parse_header(self):
        self.header = None
        buflen = len(self.buf)
        for i, d in enumerate(self.buf):
            if (d == SOF) and ((i + HEADER_LEN) <= buflen):
                header = ProtocolHeader(self.crc16)
                header.parse(
                    ''.join([self.buf[x] for x in range(i, i + HEADER_LEN)]))
                if header.is_valid():
                    self.header = header
                    return (True, i)
                else:
                    pass
        return (False, -1)

    def is_data_collected(self):
        return len(self.buf) >= self.header.length

    def parse_data(self):
        rtnval = None
        buf = ''.join([self.buf[x]
                       for x in range(0, self.header.length)])
        self.crc32.crcValue = self.crc32.initCrc
        self.crc32.update(buf[: -4])
        rst = struct.unpack('<I', bytearray(buf[-4:]))
        if (self.crc32.crcValue != rst[0]):
            WARN('Data field CRC32 failed !!!!!!!!')
            rtnval = (False, HEADER_LEN + 1)
        else:
            # print 'CRC32[{}] {}'.format(base64.b16encode(buf[-4:]),
            # str(self.crc32.crcValue == rst[0]))
            raw_buf = buf[HEADER_LEN: self.header.length - 4]

            if self.header.enc:
                raw_buf = self.aes.decode(raw_buf)[: -self.header.pad]

            if self.header.ack:
                print(self.header)
            d = ProtocolData()
            d.parse(raw_buf, self.header.ack)
            rtnval = (True, self.header.length)
        print '-------------------------------'
        return rtnval


def main():
    with open('log/djiserialr.txt', 'rb') as f:
        buf = f.read()
        p = ProtocolParser()
        for b in buf:
            p.feed(b)
        print('{}\nTotal {} bytes, parsed {} bytes. State is {}'.format(
            '-' * 80, len(buf), p.parsed_size, p.state))
