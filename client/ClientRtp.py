import socket
import threading


class ClientRtp(threading.Thread):
    """
    Base class of RTP stream controller
    """

    def __init__(self, addr, *args, **kwargs):
        super(ClientRtp, self).__init__(*args, **kwargs)

        # Addr of client
        self.addr = addr

        self.socket = None
        self.initSocket()

        # Used to control pause, resume, stop etc.
        self._stopper = threading.Event()
        self._stopper.set()
        self._display_interval = threading.Event()

        # Default interval to display
        self.interval = 0.04

    def initSocket(self):
        """
        Init the RTP socket on UDP, and bind the port
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        """
        Get the port binded
        """
        return self.socket.getsockname()[1]

    def run(self):
        """
        Start
        """
        self.beforeRun()
        self._display_interval.wait(0.1)
        while self._stopper.is_set():
            self.running()
            self._display_interval.wait(self.interval)
        self.closeSocket()
        self.afterRun()

    def stop(self):
        """
        Stop the thread
        """
        self._stopper.clear()

    """ Hook functions """

    def beforeRun(self):
        raise NotImplementedError

    def afterRun(self):
        raise NotImplementedError

    def running(self):
        raise NotImplementedError
