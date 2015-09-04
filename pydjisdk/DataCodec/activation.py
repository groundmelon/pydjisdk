from ..utils import *
import struct

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
    LOG('API Version: {} with Return Code[0x{:X}]'.format(
        s[6:], rst[0]))


########################################
ACTIVE_API_FMT = '<III32s'


def encode_active_api(**kwargs):
    buf = struct.pack(ACTIVE_API_FMT,
                      kwargs['app_id'],
                      kwargs['api_level'],
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
    LOG('AppID:{} Level:{} Version:{} bundle:{}'.format(
        app_id, api_level, app_ver, bundle_id))

########################################
ACTIVE_API_ACK_FMT = '<H'
ACTIVE_API_ACK_DICT = zip(
    range(0, 8),
    ('Success',
     'Invalid parameters',
     'Cannot recognize encrypted package',
     'Attempt to activate',
     'DJI Pilot APP no response'
     'DJI Pilot APP no Internet'
     'Server rejected activation attempt'
     'Insufficient authority level'
     ))


def encode_active_api_ack(s):
    assert False, 'Construction in progress.'


def decode_active_api_ack(s):
    data = struct.unpack('<H',s)[0]
    LOG('Activation result: {}'.format(
        ACTIVE_API_ACK_DICT[data]))

########################################


def encode_transparent_transmission(s):
    assert False, 'Construction in progress.'


def decode_transparent_transmission(s):
    assert False, 'Construction in progress.'
