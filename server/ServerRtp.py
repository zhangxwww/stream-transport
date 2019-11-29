import socket
import threading


class ServerRtp(threading.Thread):
    def __init__(self, addr, port, *args, **kwargs):
        super(ServerRtp, self).__init__(*args, **kwargs)

        self.addr = addr
        # TODO check it later
        self.port = port

        self.socket = None
        self.initSocket()

        self._pause = threading.Event()
        self._pause.set()
        self._stopper = threading.Event()
        self._stopper.set()
        self._send_interval = threading.Event()

        self.interval = 0.04
        self.ssrc = 0

        self.clientAddr = None
        self.clientPort = None

        self.is_start = False

        self.doubleSpeed = False

    def initSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def closeSocket(self):
        self.socket.close()
        self.socket = None

    def setInterval(self, interval):
        self.interval = interval

    def setClientInfo(self, addr, port):
        self.clientAddr = addr
        self.clientPort = port

    def setSsrc(self, ssrc):
        self.ssrc = ssrc

    def run(self):
        self.is_start = True
        self.beforeRun()
        while self.sendCondition() and self._stopper.is_set():
            self._pause.wait()
            self.running()
            self._send_interval.wait(self.interval)
        self.closeSocket()

    def pause(self):
        self._pause.clear()

    def resume(self):
        self._pause.set()

    def stop(self):
        self._pause.set()
        self._stopper.clear()

    def sendCondition(self):
        raise NotImplementedError

    def running(self):
        raise NotImplementedError

    def beforeRun(self):
        raise NotImplementedError

    def speed(self, speed):
        if speed == 1:
            self.doubleSpeed = False
        elif speed == 2:
            self.doubleSpeed = True
