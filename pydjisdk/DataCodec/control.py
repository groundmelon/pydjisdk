import logging
from ..utils import *
import struct

LOGGER_NAME = 'app.codec'

########################################
ACQUIRE_CONTROL_FMT = '<?'


def encode_acquire_control(**kwargs):
    buf = struct.pack(ACQUIRE_CONTROL_FMT, kwargs['ctrl'])
    return buf


def decode_acquire_control(s):
    rst = struct.unpack(ACQUIRE_CONTROL_FMT, s)
    logging.getLogger(LOGGER_NAME).info('data:{} {}'.format(
        rst[0], 'acquire' if rst[0] else 'release'))

#########################################
ACQUIRE_CONTROL_ACK_FMT = '<H'
ACQUIRE_CONTROL_ACK_DICT = dict((
    (0x00, 'Need RC in Mode F'),
    (0x01, 'Successfully released control authorization'),
    (0x02, 'Successfully obtained control authorization'),
    (0x03, 'Obtain in progress'),
    (0x04, 'Release in progress'),
    (0x00C9, 'IOC'),
))


def encode_acquire_control_ack(**kwargs):
    assert False, 'Construction in progress.'


def decode_acquire_control_ack(s):
    rst = struct.unpack(ACQUIRE_CONTROL_ACK_FMT, s)
    ack = rst[0]
    logging.getLogger(LOGGER_NAME).info(
        'Control acquire result: {}'.format(GetPromptSafely(ack, ACQUIRE_CONTROL_ACK_DICT)))

#########################################
TASK_CONTROL_DICT = dict((
    ('home', 0x01),
    ('takeoff', 0x04),
    ('land', 0x06),
))
TASK_CONTROL_FMT = '<BB'


def encode_task_control(**kwargs):
    buf = struct.pack(TASK_CONTROL_FMT,
                      kwargs['seq'],
                      TASK_CONTROL_DICT[kwargs['task']],
                      )
    return buf


def decode_task_control(s):
    rst = struct.unpack(TASK_CONTROL_FMT, s)
    logging.getLogger(LOGGER_NAME).info('Task {} seq {}'.format(rst[1], rst[0]))


#########################################
TASK_CONTROL_ACK_DICT = dict((
    (0x01, 'task refused'),
    (0x02, 'task accepted'),
))
TASK_CONTROL_FMT = '<B'


def encode_task_control_ack(**kwargs):
    assert False, 'Construction in progress.'


def decode_task_control_ack(s):
    rst = struct.unpack(TASK_CONTROL_FMT, s)
    ack = rst[0]
    logging.getLogger(LOGGER_NAME).info(''.format(GetPromptSafely(ack, TASK_CONTROL_ACK_DICT)))

#########################################
TASK_INQUIRE_FMT = '<B'


def encode_task_inquire(**kwargs):
    buf = struct.pack(TASK_INQUIRE_FMT, kwargs['seq'])
    return buf


def decode_task_inquire(s):
    rst = struct.unpack(TASK_INQUIRE_FMT, s)
    logging.getLogger(LOGGER_NAME).info('Task inquire #{}'.format(rst[0]))


#########################################
TASK_INQUIRE_ACK_FMT = '<BB'
TASK_INQUIRE_ACK_DICT = dict((
    (0x01, 'Wrong CMD Sequence Number',),
    (0x03, 'Switching in progress',),
    (0x04, 'Switching failed',),
    (0x05, 'Switching succeed',),
))


def encode_task_inquire_ack(**kwargs):
    assert False, 'Construction in progress.'


def decode_task_inquire_ack(s):
    rst = struct.unpack(TASK_INQUIRE_ACK_FMT, s)
    seq = rst[0]
    ack = rst[1]
    logging.getLogger(LOGGER_NAME).info(
        'Task inquire #{} rst: {}'.format(seq, GetPromptSafely(ack, TASK_INQUIRE_ACK_DICT)))

#########################################
ATT_CONTROL_FMT = '<B4f'


def encode_atti_control(**kwargs):
    buf = struct.pack(ATT_CONTROL_FMT,
                      kwargs['flag'],
                      kwargs['roll_or_x'],
                      kwargs['pitch_or_y'],
                      kwargs['yaw'],
                      kwargs['throttle_or_z'],
                      )
    return buf


def decode_atti_control(s):
    rst = struct.unpack(ATT_CONTROL_FMT, s)
    logging.getLogger(LOGGER_NAME).info('atti ctrl {:08b} <{},{},{},{}>'.format(*rst))

#########################################
CTRL_AUTH_CHANGE_FMT = '<B'


def encode_ctrl_auth_change(**kwargs):
    assert False, 'Construction in progress.'


def decode_ctrl_auth_change(s):
    rst = struct.unpack(CTRL_AUTH_CHANGE_FMT, s)
    logging.getLogger(LOGGER_NAME).info('Authority overtoken by Ncore [0x{:02X}]'.format(rst[0]))
