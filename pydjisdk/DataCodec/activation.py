import logging
import struct

LOGGER_NAME = 'app.codec'

########################################
ACQUIRE_API_VERSION_FMT = '<B'


def encode_acquire_api_version(**kwargs):
    buf = struct.pack(ACQUIRE_API_VERSION_FMT, 1)
    return buf


def decode_acquire_api_version(s):
    assert False, 'Construction in progress.'

########################################
ACQUIRE_API_VER_ACK_FMT = '<HI'


def encode_acquire_api_version_ack(s):
    assert False, 'Construction in progress.'


def decode_acquire_api_version_ack(s):
    rst = struct.unpack(ACQUIRE_API_VER_ACK_FMT, s[:6])
    logging.getLogger(LOGGER_NAME).info('API Version: {} with Return Code[0x{:X}]'.format(
        s[6:], rst[0]))


########################################
ACTIVE_API_FMT = '<II32s'


def encode_active_api(**kwargs):
    buf = struct.pack(ACTIVE_API_FMT,
                      kwargs['app_id'],
                      kwargs['app_ver'],
                      kwargs['bundle_id'],
                      )
    return buf


def decode_active_api(s):
    rst = struct.unpack(ACTIVE_API_FMT, s)
    app_id = rst[0]
    api_level = rst[1]
    app_ver = rst[2]
    bundle_id = rst[3]
    logging.getLogger(LOGGER_NAME).info('AppID:{} Level:{} Version:{} bundle:{}'.format(
        app_id, api_level, app_ver, bundle_id))

########################################
ACTIVE_API_ACK_FMT = '<H'
ACTIVE_API_ACK_DICT = dict(zip(
    range(0, 9),
    ('Success',
     'Invalid parameters',
     'Cannot recognize the encrypted package',
     'New APP ID, activation in progress',
     'No response from DJI GO APP',
     'No Internet from DJI GO APP',
     'Server rejected',
     'Authorization level insufficient',
     'Wrong SDK version',
     )))


def encode_active_api_ack(s):
    assert False, 'Construction in progress.'


def decode_active_api_ack(s):
    data = struct.unpack('<H', s)[0]
    print("data=", data)
    logging.getLogger(LOGGER_NAME).info('Activation result: {}'.format(
        ACTIVE_API_ACK_DICT[data]))

########################################


def encode_transparent_transmission(s):
    assert False, 'Construction in progress.'


def decode_transparent_transmission(s):
    assert False, 'Construction in progress.'
