import base64
import threading


def bytesToBinStr(s):
    return ' '.join(['{:08b}'.format(x) for x in bytearray(s)])


def bytesToHexStr(s):
    return base64.b16encode(s)


def LOG(s):
    print(s)


def WARN(s):
    print(s)


class StoppableThread(threading.Thread):

    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()
        self._stop.clear()
        self.setDaemon(True)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
