# from improvedbitstruct import unpack as bitunpack
from bitstruct import unpack as bitunpack
import collections
import base64
import crcmod
import collections


# def unpack_head(s, crc):
#     buf = base64.b16decode(s.upper(), False)
#     rst = bitunpack(
#         'u8u10u6u5u1u2u5u3u24u16u16', bytearray(buf), inverse_endian=True)

#     expl = list(rst)
#     if rst[4] == 0:
#         expl[4] = 'data-frame'
#     else:
#         expl[4] = 'ack-frame'

#     if rst[7] == 1:
#         expl[7] = 'enc'
#     else:
#         expl[7] = 'no-enc'

#     expl[9] = base64.b16encode(buf[8:10])

#     d = collections.OrderedDict()
#     d['SOF'] = rst[0]
#     d['LEN'] = rst[1]
#     d['VER'] = rst[2]
#     d['SESSION'] = rst[3]
#     d['A'] = expl[4]
#     d['RES0'] = rst[5]
#     d['PADDING'] = rst[6]
#     d['ENC'] = expl[7]
#     d['RES1'] = rst[8]
#     d['SEQ'] = rst[9]
#     d['CRC'] = rst[10]

#     data_len_from_buf = len(buf) - 12
#     data_len_from_head = d['LEN'] - 12

#     crc.crcValue = crc.initCrc
#     crc.update(buf[:10])

#     print("LEN[%3d] SESSION[%2d] SEQ[%d] CRC[%s]" %
#           (d['LEN'], d['SESSION'], d['SEQ'], str(crc.crcValue == d['CRC'])))


CHANGED = True
UNCHANGED = False
SOF = '\xAA'
VER = 0
HEADER_LEN = 12
ACK_FRAME = 1
DATA_FRAME = 0


class ProtocolHeader(object):

    def __init__(self, buf, crc):
        rst = bitunpack(
            'u8u10u6u5u1u2u5u3u24u16u16', bytearray(buf), inverse_endian=True)

        print(''.join(['{:08b}'.format(x) for x in bytearray(buf)]))

        self.d = collections.OrderedDict()
        self.d['SOF'] = rst[0]
        self.d['LEN'] = rst[1]
        self.d['VER'] = rst[2]
        self.d['SESSION'] = rst[3]
        self.d['A'] = rst[4]
        self.d['RES0'] = rst[5]
        self.d['PADDING'] = rst[6]
        self.d['ENC'] = rst[7]
        self.d['RES1'] = rst[8]
        self.d['SEQ'] = rst[9]
        self.d['CRC'] = rst[10]

        crc.crcValue = crc.initCrc
        crc.update(buf[:10])
        self.crc_check_passed = (crc.crcValue == self.d['CRC'])

        d = self.d
        print("LEN[%3d] SESSION[%2d] SEQ[%d] CRC[%s] ENC[%d] ACK[%d]" %
              (d['LEN'],
               d['SESSION'],
               d['SEQ'],
               str(crc.crcValue == d['CRC']),
               self.d['ENC'],
               self.d['A']
               )
              )

    def __repr__(self):
        return str(self.d)

    def is_valid(self):
        conditions = (self.d['SOF'] == ord(SOF),
                      self.d['VER'] == VER,
                      # self.d['RES0'] == 0,
                      self.d['RES1'] == 0,
                      self.crc_check_passed,
                      )
        # print conditions, self.d['RES0']
        return all(conditions)


class ProtocolParser(object):

    def __init__(self):
        self.buf = collections.deque(maxlen=1000)
        self.state = 'IDLE'
        self.crc16 = crcmod.Crc(0x18005, 0x3AA3)
        self.crc32 = crcmod.Crc(0x104C11DB7, 0x3AA3)
        self.header = None

    def clear_randuant(self, idx):
        assert isinstance(idx, int)
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
                header = self.extract_header(
                    ''.join([self.buf[x] for x in range(i, i + HEADER_LEN)]))
                print(header.is_valid())
                if header.is_valid():
                    self.header = header
                    return (True, i)
                else:
                    pass
        return (False, -1)

    def extract_header(self, buf):
        return ProtocolHeader(buf, self.crc16)

    def is_data_collected(self):
        return len(self.buf) >= self.header.d['LEN']

    def parse_data(self):
        buf = ''.join([self.buf[x]
                       for x in range(0, self.header.d['LEN'])])
        self.crc32.crcValue = self.crc32.initCrc
        self.crc32.update(buf[:-4])
        rst = bitunpack('u32', bytearray(buf[-4:]), inverse_endian=True)
        print 'CRC32:{}'.format(str(self.crc32.crcValue == rst[0]))
        print 'data:{}'.format(base64.b16encode(buf[HEADER_LEN:self.header.d['LEN']]))
        print '-------------------------------'
        return (True, self.header.d['LEN'])
        # return (False, HEADER_LEN+1)


buflistr = [
]

buflists = [
    '''aa3e 0002 0000 0000 0000 c12f 0001 9256
0f00 0200 0000 0100 0000 3132 3334 3536
3738 3930 3132 3334 3536 3738 3930 3132
3334 3536 3738 3930 3132 9311 b274 ''',
    '''aa20
0001 2d00 0000 0100 7462 f0fe 9c00 2116
e7b2 b048 a498 3135 4f49 2ac1 ba63 ''',
    '''aa20
0001 2d00 0000 0200 7492 6225 f5a0 560d
fbea 2789 1e04 97dc 6926 bcfb 5119 ''',
    '''aa20
0001 2d00 0000 0300 7502 399d 8de4 5392
72b3 ad00 d8a6 0691 8320 fd8a 5271 ''',
    '''aa20
0001 2d00 0000 0400 7732 4103 9991 53e7
5412 6fb4 3be6 1b94 07c7 75ad 5ce0 ''',
    '''aa20
0001 2d00 0000 0500 76a2 c1c2 066d 8c6d
fe17 86d1 0c62 7f4b 00a7 d5c9 5ef2 ''',
    '''aa20
0001 2d00 0000 0600 7652 72fd 624e d4''',
    '''aa
5f38 cd83 157d cc4b f315 3715 d2be ''',
    '''aa20
0001 2d00 0000 0700 77c2 6db4 ff26 13c4
b4a5 c024 5018 43c1 fc10 b3c1 d720 ''',
    '''aa20
0001 2d00 0000 0800 7232 780f 3f60 5c12
3305 bfb9 56e8 4144 29fc 13a4 e441 ''',
    '''aa20
0001 2d00 0000 0900 73a2 1cda 36cd 1e01
0df5 a61e 0944 77b1 b751 997a 1601 ''',
    '''aa20
0001 2d00 0000 0a00 7352 242f 1613 e12b
1415 0458 4803 50bf ccfe e2ce a8f8 ''',
    '''aa20
0001 2d00 0000 0b00 72c2 70bc 1d59 fdbb
b8f3 e37c 512d d781 060a d1a3 6607 ''',
    '''aa20
0001 2d00 0000 0c00 70f2 7707 ff67 0b41
87ae 2f86 46b5 801e 5e06 6abe ac7b ''',
    '''aa20
0001 2d00 0000 0d00 7162 6840 7749 f139
b297 46b1 4699 10de 7535 ee79 cc39 ''',
]

# crc = crcmod.Crc(0x18005, 0x3AA3)
# for buf in buflists:
#     unpack_head("".join(buf.split()), crc)


p = ProtocolParser()
buf = ''.join(buflists)
buf = ''.join(buf.split())
buf = base64.b16decode(buf.upper(), False)
p.feed(buf)
