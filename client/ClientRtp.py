import socket
import threading


class ClientRtp(threading.Thread):
    def __init__(self, addr, *args, **kwargs):
        super(ClientRtp, self).__init__(*args, **kwargs)

        self.addr = addr
        # self.port = port

        self.socket = None
        self.initSocket()

        self._stopper = threading.Event()
        self._stopper.set()
        self._display_interval = threading.Event()

        self.interval = 0.04

    def initSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.socket.settimeout(0.5)
        # self.socket.bind((self.addr, self.port))
        port = 44444
        while True:
            try:
                self.socket.bind((self.addr, port))
                break
            except OSError:
                port += 2

    def closeSocket(self):
        self.socket.close()
        self.socket = None

    def setInterval(self, interval):
        self.interval = interval / 1.5

    def getPort(self):
        return self.socket.getsockname()[1]

    def run(self):
        self.beforeRun()
        while self._stopper.is_set():
            self.running()
            self._display_interval.wait(self.interval)
        self.closeSocket()
        self.afterRun()

    def stop(self):
        self._stopper.clear()

    def beforeRun(self):
        raise NotImplementedError

    def afterRun(self):
        raise NotImplementedError

    def running(self):
        raise NotImplementedError
