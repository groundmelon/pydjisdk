from SerialPort import SerialPort
from Sessions import Session, SessionManager, SessionType
from Protocol import ProtocolParser, ProtocolHeader, ProtocolData
from utils import StoppableThread
import EncryptCodec
import Queue
import struct
import logging
import logging.config
import yaml

import DataCodec.activation as DataCodecActivation
import DataCodec.control as DataCodecControl
import DataCodec.monitor as DataCodecMonitor

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


class SDKApplication(StoppableThread):

    '''
    SDKApplication class for main entrance for api.

    Usage:
    >>> app = SDKApplication(app_id, aes256_key, port)
    >>> app.get_api_version()
    ...
    >>> app.active_api()
    ...
    >>> app.acquire_control()
    ...
    >>> app.release_control()
    ...
    >>> app.close()

    The following are the parameters supplied to the constructor.

    app_id -- your app id

    aes256_key -- your enc key

    port -- your serial port path

    '''

    def __init__(self, **kwargs):
        super(SDKApplication, self).__init__()

        with open('logconfig.yaml', 'r') as f:
            logging.config.dictConfig(yaml.load(f.read(), Loader=yaml.Loader))

        self.applogger = logging.getLogger('app')

        self.port_rx_stream_queue = Queue.Queue()
        self.parsed_message_queue = Queue.Queue()

        self.active_info = dict(
            [(k, kwargs.get(k, v)) for (k, v) in [
                ('app_id', None),
                ('app_ver', 0x03010A00),
                ('bundle_id', '12345678901234567890123456789012'),
            ]]
        )
        if not self.active_info.get('app_id'):
            raise TypeError(
                '{}.__init__() must pass argument "app_id"!'.format(__class__))

        encrypt_param = dict(
            [(k, kwargs.get(k, v)) for (k, v) in [
                ('crc16_init', 0x3AA3),
                ('crc16_poly', 0x18005),
                ('crc32_init', 0x3AA3),
                ('crc32_poly', 0x104C11DB7),
                ('aes256_key', None),
            ]]
        )
        if not encrypt_param.get('aes256_key'):
            raise TypeError(
                '{}.__init__() must pass argument "aes256_key"!'.format(__class__))

        EncryptCodec.initEncryptCodec(encrypt_param)

        port_param = dict(
            [(k, kwargs.get(k, v)) for (k, v) in [
                ('port', '/dev/ttyUSB0'),
                ('baudrate', 230400),
                ('read_bytes', 12),
                ('buffer_queue', self.port_rx_stream_queue),
            ]]
        )
        self.port = SerialPort(**port_param)

        self.parser = ProtocolParser(
            self.port_rx_stream_queue, self.parsed_message_queue)

        self.sm = SessionManager(self.port.write)

        self.register_data_handle()
        self.port.open()
        self.parser.start()

    def register_data_handle(self):
        self.recv_data_handler_table = CMD_SET_R

    def launch(self):
        self.start()

    def close(self):
        self.sm.close_all_sessions()
        self.port.close()
        self.stop()

    def run(self):
        while (not self.stopped()):
            try:
                (header, data_buf) = self.parsed_message_queue.get(
                    block=True, timeout=3.0)
                assert isinstance(header, ProtocolHeader) and isinstance(
                    data_buf, bytes)

                if header.ack:
                    self.sm.feed_ack(header.session, header.seq, data_buf)
                else:
                    d = ProtocolData()
                    cmd_set, cmd_id, content = d.parse(data_buf)
                    self.recv_data_handler_table[cmd_set][cmd_id](content)
                    # LOG('Data received.')
            except Queue.Empty, e:
                pass

    # def pack_command_data_buf(self, cmd_set, cmd_id, raw_data_buf, is_enc):
    #     if is_enc:
    #         enc_data_buf = EncryptCodec.encodeAES(raw_data_buf)
    #     else:
    #         enc_data_buf = raw_data_buf

    #     crcval = EncryptCodec.calcCrc32(enc_data_buf)
    #     pad = len(enc_data_buf) - len(raw_data_buf)
    #     crc_data_buf = struct.pack('<sI', enc_data_buf, crcval)
    #     return (pad, crc_data_buf)

    def get_api_version(self):
        is_enc = False
        raw_data_buf = DataCodecActivation.encode_acquire_api_version()
        pad, data_buf = ProtocolData().render(
            0x00, 0x00, raw_data_buf, is_enc)
        self.sm.add_session(SessionType.RequiredAck,
                            enc=is_enc, pad=pad, data_buf=data_buf,
                            ack_callback=self.api_version_ack_callback)

    def api_version_ack_callback(self, buf):
        if buf is None:
            self.applogger.warning('Get api version failed.')
        else:
            DataCodecActivation.decode_acquire_api_version_ack(buf)

    def active_api(self):
        is_enc = False
        raw_data_buf = DataCodecActivation.encode_active_api(
            **self.active_info)
        pad, data_buf = ProtocolData().render(
            0x00, 0x01, raw_data_buf, is_enc)
        self.sm.add_session(SessionType.RequiredAck,
                            enc=is_enc, pad=pad, data_buf=data_buf,
                            ack_callback=self.active_api_ack_callback)

    def active_api_ack_callback(self, buf):
        if buf is None:
            self.applogger.warning('Get active api failed.')
        else:
            DataCodecActivation.decode_active_api_ack(buf)

    def acquire_control(self):
        is_enc = True
        raw_data_buf = DataCodecControl.encode_acquire_control(ctrl=True)
        pad, data_buf = ProtocolData().render(
            0x01, 0x00, raw_data_buf, is_enc)
        self.sm.add_session(SessionType.RequiredAck,
                            enc=is_enc, pad=pad, data_buf=data_buf,
                            ack_callback=self.control_ack_callback)

    def release_control(self):
        is_enc = True
        raw_data_buf = DataCodecControl.encode_acquire_control(ctrl=False)
        pad, data_buf = ProtocolData().render(
            0x01, 0x00, raw_data_buf, is_enc)
        self.sm.add_session(SessionType.RequiredAck,
                            enc=is_enc, pad=pad, data_buf=data_buf,
                            ack_callback=self.control_ack_callback)

    def control_ack_callback(self, buf):
        if buf is None:
            self.applogger.warning('Acquire/Release control failed.')
        else:
            DataCodecControl.decode_acquire_control_ack(buf)
