import serial
import time
from utils import StoppableThread


class Staticstics(object):

    def __init__(self):
        self.tx = 0
        self.rx = 0

    def update_rx(self, n):
        assert isinstance(n, int)
        self.rx += n

    def update_tx(self, n):
        assert isinstance(n, int)
        self.tx += n


class SerialListener(StoppableThread):

    def __init__(self, ser, read_bytes, buffer_queue, statistics):
        super(SerialListener, self).__init__()
        self.ser = ser
        self.read_bytes = read_bytes

        self.buffer_queue = buffer_queue
        self.statistics = statistics

    def run(self):
        print('{}({}) will start.'.format(self.name, self.__class__))
        while not self.stopped():
            buf = self.ser.read(self.read_bytes)
            if buf:
                self.statistics.update_rx(len(buf))
                self.buffer_queue.put(buf, block=True, timeout=10.0)
            else:
                pass
        print('{}({}) will stop.'.format(self.name, self.__class__))

# TODO Send queue is needed?


class SerialPort(object):

    '''
    SerialPort class for operating the serial port.

    Usage:
    >>> port = SerialPort(port, baudrate, read_bytes, buffer_queue)
    >>> port.open()
    ...
    >>> port.write('12345')
    ...
    >>> port.close()

    Call open() for sending and listening.

    Call write(buf) for send data after open() is called.

    Received data are pushed into a buffer_queue which is defined in constructor. 
    Content of the queue is instances of bytes

    The following are the parameters supplied to the constructor.

    port -- port name

    baudrate -- baudrate for port

    read_bytes -- how many bytes a single read() reads for decreasing cpu load.

    buffer_queue -- an output queue of received data 

    timeout -- timeout for serial.Serial.read(timeout)

    '''

    def __init__(self, port, baudrate, read_bytes, buffer_queue, timeout=10.0):
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.timeout = timeout
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE

        self.statistics = Staticstics()

        self.listener = SerialListener(
            ser=self.ser,
            read_bytes=read_bytes,
            buffer_queue=buffer_queue,
            statistics=self.statistics
        )

    def open(self):
        self.ser.open()
        self.listener.start()

    def write(self, buf):
        l = self.ser.write(buf)
        self.statistics.update_tx(l)

    def close(self):
        self.listener.stop()
        self.ser.close()
