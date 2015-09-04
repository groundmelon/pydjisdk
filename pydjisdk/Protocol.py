import ctypes
from ctypes import c_uint8, c_uint16, c_uint32, c_double, c_float, c_int16, c_int32
import collections
import base64
import struct

import Queue

from utils import *
from EncryptCodec import calcCrc16, calcCrc32, encodeAES, decodeAES

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
DATA_CRC_LEN = 4


class ProtocolHeader(object):

    def __init__(self):
        self.u = ProtocolHeaderUnion()

    def __getattr__(self, key):
        if key in header_field_table:
            return self.u.data.__getattribute__(key)
        else:
            return self.__getattribute__(key)

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

        crcval = calcCrc16(buf[:10])
        self.crc_check_passed = (crcval == self.u.data.crc16)

    def render(self, **kwargs):
        self.u.data.sof = ord(SOF)
        self.u.data.length = HEADER_LEN + kwargs.get('data_length') + DATA_CRC_LEN
        self.u.data.ver = VER
        self.u.data.session = kwargs.get('session')
        self.u.data.ack = kwargs.get('ack')
        self.u.data.res0 = 0
        self.u.data.pad = kwargs.get('pad')
        self.u.data.enc = kwargs.get('enc')
        self.u.data.res1 = 0
        self.u.data.seq = kwargs.get('seq')
        self.u.data.crc16 = 0

        buf = ''.join([chr(x) for x in self.u.buf])
        self.u.data.crc16 = calcCrc16(buf[:10])
        return ''.join([chr(x) for x in self.u.buf])


class ProtocolData(object):

    def __init__(self):
        pass

    def parse(self, buf):
        # print 'data:{}'.format(base64.b16encode(buf))
        rst = struct.unpack('<BB', buf[:2])
        cmd_set = rst[0]
        cmd_id = rst[1]
        # print('command_set[%d] command_id[%d]' % (self.cmd_set, self.cmd_id))

        return cmd_set, cmd_id, buf[2:]

    # def parse_ack(self, buf, cmd_set, cmd_id):
    #     # print 'data:{}'.format(base64.b16encode(buf))
    #     self.buf = buf

    #     self.ack_data = struct.unpack('<H', buf[:2])[0]
    #     # print('command_set[%d] command_id[%d]' % (self.cmd_set, self.cmd_id))

    #     self.handle_table[cmd_set][cmd_id](self.ack_data, self.buf[2:])

    def render(self, cmd_set, cmd_id, raw_data_buf, is_enc):
        cmd_buf = struct.pack('<BB', cmd_set, cmd_id)
        data_buf = cmd_buf + raw_data_buf
        if is_enc:
            enc_data_buf = encodeAES(data_buf)
        else:
            enc_data_buf = data_buf

        pad = len(enc_data_buf) - len(data_buf)
        return (pad, enc_data_buf)


from utils import StoppableThread


class ProtocolParser(StoppableThread):

    '''
    Protocol parser class for DJISDK

    This class inherits from threading.thread, so call .run() after construction.

    Usage:
    >>> parser = ProtocolParser(input_buffer_queue, output_msg_queue)
    >>> parser.run()
    ...
    >>> parser.stop()

    The following are the parameters supplied to the constructor.

    input_buffer_queue -- an input queue of instances of bytes(str in python 2) 
    from input device (such as port).

    output_msg_queue -- an output queue of tuple(ProtocolHeader, raw_buf).
    raw_buf is a bytes() which is checked by CRC32 and decoded by AES256

    '''

    def __init__(self, input_buffer_queue, output_msg_queue):
        super(ProtocolParser, self).__init__()
        self.buf = collections.deque(maxlen=2047)
        self.state = 'IDLE'
        self.header = None
        self.parsed_size = 0

        self.input_buffer_queue = input_buffer_queue
        self.output_msg_queue = output_msg_queue

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
        assert(len(self.buf) < 1024)
        while True:
            if self.process() == UNCHANGED:
                break

    def parse_header(self):
        self.header = None
        buflen = len(self.buf)
        for i, d in enumerate(self.buf):
            if (d == SOF) and ((i + HEADER_LEN) <= buflen):
                header = ProtocolHeader()
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
        crcval = calcCrc32(buf[: -4])
        rst = struct.unpack('<I', bytearray(buf[-4:]))
        if (crcval != rst[0]):
            WARN('Data field CRC32 failed. header={}'.format(self.header))
            rtnval = (False, HEADER_LEN)
        else:
            # print 'CRC32[{}] {}'.format(base64.b16encode(buf[-4:]),
            # str(self.crc32.crcValue == rst[0]))
            raw_buf = buf[HEADER_LEN: self.header.length - 4]

            if self.header.enc:
                raw_buf = decodeAES(raw_buf)[: -self.header.pad]

            #### TODO debug ####
            if self.header.ack:
                print(self.header)
            ####################

            self.output_msg_queue.put((self.header, raw_buf), timeout=10.0)
            rtnval = (True, self.header.length)
        return rtnval

    def run(self):
        LOG('{}({}) will start'.format(self.name, self.__class__))
        while not self.stopped():
            try:
                buf = self.input_buffer_queue.get(block=True, timeout=10.0)
                assert isinstance(buf, bytes)
                self.feed(buf)
            except Queue.Empty, e:
                pass
        LOG('{}({}) will stop.'.format(self.name, self.__class__))
