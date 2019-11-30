import socket
import threading


class ServerRtp(threading.Thread):
    """
    Base class of the RTP stream controller
    """

    def __init__(self, addr, *args, **kwargs):
        super(ServerRtp, self).__init__(*args, **kwargs)

        # addr of the server
        self.addr = addr

        self.socket = None
        self.initSocket()

        # used to control pause, resume, stop etc.
        self._pause = threading.Event()
        self._pause.set()
        self._stopper = threading.Event()
        self._stopper.set()
        self._send_interval = threading.Event()

        # default interval to send
        self.interval = 0.04
        self.ssrc = 0

        self.clientAddr = None
        self.clientPort = None

        # whether has started
        self.is_start = False

        # 2x speed or not
        self.doubleSpeed = False

    def initSocket(self):
        """
        Init the RTP socket on UDP
        """
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
        """
        Start
        """
        self.is_start = True
        self.beforeRun()
        while self.sendCondition() and self._stopper.is_set():
            self._pause.wait()
            self.running()
            self._send_interval.wait(self.interval)
        self.closeSocket()

    def pause(self):
        """
        Pause the thread
        """
        self._pause.clear()

    def resume(self):
        """
        Resume the thread
        """
        self._pause.set()

    def stop(self):
        """
        Stop the thread
        """
        self._pause.set()
        self._stopper.clear()

    def speed(self, speed):
        """
        Change the speed
        :param speed: 1 or 2
        """
        if speed == 1:
            self.doubleSpeed = False
        elif speed == 2:
            self.doubleSpeed = True

    """ Hook functions """

    def sendCondition(self):
        raise NotImplementedError

    def running(self):
        raise NotImplementedError

    def beforeRun(self):
        raise NotImplementedError
