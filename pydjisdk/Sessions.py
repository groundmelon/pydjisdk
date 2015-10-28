from Protocol import ProtocolHeader
import time
import itertools
from utils import StoppableThread
from EncryptCodec import calcCrc32
import Queue
import base64
import struct
import logging


class SessionType(object):
    NoAck = 0
    OptionalAck = 1
    RequiredAck = 2
    RequiredRange = (2, 31)


class Session(StoppableThread):

    def __init__(self, session_id, seq, send_func, enc, pad, data_buf,
                 ack_callback=None, timeout=1.0, retry=3, ):
        super(Session, self).__init__()
        # save arguments
        self.session_id = session_id
        self.seq = seq
        self.enc = enc
        self.pad = pad
        self.data_buf = data_buf
        self.send_func = send_func
        self.ack_callback = ack_callback
        self.timeout = timeout
        self.retry = retry

        # init variables
        self.ack_queue = Queue.Queue()
        self.retry_cnt = 0

        if session_id == 0:
            self.session_type = SessionType.NoAck
        elif session_id == 1:
            self.session_type = SessionType.OptionalAck
        elif SessionType.RequiredRange[0] <= session_id <= SessionType.RequiredRange[1]:
            self.session_type = SessionType.RequiredAck
        else:
            assert False, 'Invalid session_id[{}]'.format(
                session_id)

        self.buf = self.pack()

        self.logger = logging.getLogger('app.ssn')

    def __repr__(self):
        return '<SessionThread> session_id[{}] #{}'.format(self.session_id, self.seq)

    def launch(self):
        if self.session_type is SessionType.NoAck:
            assert self.ack_callback is None
            self.running = False
            self.send_buffer()
        else:
            self.send_buffer()
            self.running = True
            self.start()

    def send_buffer(self):
        self.send_func(self.buf)
        self.logger.info('Send [{}]'.format(base64.b16encode(self.buf)))
        self.logger.info(self.header)

    def feed(self, buf):
        self.ack_queue.put(buf, block=True, timeout=self.timeout)

    def run(self):
        self.logger.info('{} will start'.format(self))
        while (not self.stopped()):
            if self.retry_cnt < self.retry:
                try:
                    buf = self.ack_queue.get(block=True, timeout=self.timeout)
                    assert isinstance(buf, bytes) and buf
                    self.ack_callback(buf)
                    break
                except Queue.Empty, e:
                    self.send_buffer()
                    self.retry_cnt += 1
            else:
                self.ack_callback(None)
                self.logger.warning('Receive ack failed. {}'.format(self))
                break
        self.running = False
        self.logger.info('{} will stop.'.format(self))

    def pack(self):
        header = ProtocolHeader()
        self.head_buf = header.render(
            data_length=len(self.data_buf),
            session=self.session_id,
            ack=0,
            pad=self.pad,
            enc=self.enc,
            seq=self.seq,
        )
        self.header = header

        raw_buf = ''.join([self.head_buf, self.data_buf])
        crcval = calcCrc32(raw_buf)
        crc_buf = struct.pack('<I', crcval)

        return raw_buf + crc_buf


class SessionManager(object):

    def __init__(self, send_func):
        self.send_func = send_func

        self.op_ack_sessions = dict()
        self.re_ack_sessions = dict.fromkeys(
            range(SessionType.RequiredRange[0], SessionType.RequiredRange[1] + 1), None)
        self.seq = 0

        self.logger = logging.getLogger('app.smg')

    def close_all_sessions(self):
        for s in self.op_ack_sessions.values():
            if s is not None:
                s.stop()

        for s in self.re_ack_sessions.values():
            if s is not None:
                s.stop()

    def add_session(self, session_type, **kwargs):
        session_id = None
        if session_type == SessionType.NoAck:
            session_id = 0
        elif session_type == SessionType.OptionalAck:
            session_id = 1
        elif session_type == SessionType.RequiredAck:
            l = self.re_ack_sessions.keys()
            l.sort()
            for i in l:
                if self.re_ack_sessions[i] is None:
                    session_id = i
                    break
                elif self.re_ack_sessions[i].running is False:
                    session_id = i
                    break

        if session_id is None:
            self.logger.warning('No empty session!')
            return False

        session = Session(session_id, self.seq, self.send_func, **kwargs)
        self.seq += 1

        if session_id is 0:
            pass
        elif session_id is 1:
            self.op_ack_sessions[self.seq] = session
        else:
            self.re_ack_sessions[session_id] = session

        session.launch()

        # clear finished sessions
        for k in self.op_ack_sessions.keys():
            if not self.op_ack_sessions[k].running:
                self.op_ack_sessions.pop(k)

        for k in self.re_ack_sessions.keys():
            if self.re_ack_sessions[k] is not None:
                if not self.re_ack_sessions[k].running:
                    self.re_ack_sessions.pop(k)

    def feed_ack(self, session_id, seq, buf):
        if session_id is SessionType.OptionalAck:
            session = self.op_ack_sessions.get(seq)
            if session is None:
                self.logger.warning(
                    'Optional Session[{}] Seq[{}] not found!'.format(session_id, seq))
                return
        elif session_id in SessionType.RequiredRange:
            session = self.re_ack_sessions.get(session_id)
            if session is None:
                self.logger.warning(
                    'Required Session[{}] Seq[{}] not found!'.format(session_id, seq))
                return
        else:
            assert False

        assert session.session_id == session_id
        assert session.seq == seq
        session.feed(buf)
