from Crypto.Cipher import AES
import base64
import crcmod
from utils import LOG


class AESCodec(object):

    def __init__(self, keystr):
        # the block size for the cipher object; must be 16, 24, or 32 for AES
        self.BLOCK_SIZE = 16

        key = base64.b16decode(keystr, True)

        # the character used for padding--with a block cipher such as AES, the value
        # you encrypt must be a multiple of BLOCK_SIZE in length.  This character is
        # used to ensure that your value is always a multiple of BLOCK_SIZE
        self.PADDING = '\x00'
        self.cipher = AES.new(key, AES.MODE_ECB)

    def pad(self, s):
        # one-liner to sufficiently pad the text to be encrypted
        return s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * self.PADDING

    def encode(self, s):
        return self.cipher.encrypt(self.pad(s))

    def decode(self, s):
        return self.cipher.decrypt(s)


class CRC(object):

    def __init__(self, poly, initval):
        self.crc = crcmod.Crc(poly, initval)
        LOG('Init CRC with poly=0x{:X} initval=0x{:X}'.format(poly, initval))

    def calc(self, buf):
        crc = self.crc.new(buf)
        return crc.crcValue

_crc16 = None
_crc32 = None
_aes = None


def initEncryptCodec(encrypt_param):
    global _crc16
    global _crc32
    global _aes

    _crc16 = CRC(encrypt_param['crc16_poly'], encrypt_param['crc16_init'])
    _crc32 = CRC(encrypt_param['crc32_poly'], encrypt_param['crc32_init'])
    _aes = AESCodec(encrypt_param['aes256_key'])


def calcCrc16(buf):
    global _crc16
    return _crc16.calc(buf)


def calcCrc32(buf):
    global _crc32
    return _crc32.calc(buf)


def encodeAES(buf):
    global _aes
    return _aes.encode(buf)


def decodeAES(buf):
    global _aes
    return _aes.decode(buf)
