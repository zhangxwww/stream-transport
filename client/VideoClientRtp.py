import threading
from PIL import Image, ImageTk
from io import BytesIO

from client.ClientRtp import ClientRtp
from client.RtpPacket import RtpPacket

class VideoClientRtp(ClientRtp):
    def __init__(self, addr, port, *args, **kwargs):
        super(VideoClientRtp, self).__init__(addr, port, *args, **kwargs)

        self.frameNum = 0

        self.bufferSemaphore = None
        self.displaySemaphore = None

        self.decodeFrame = None

        self.displayCallback = None

    def beforeRun(self):
        self.bufferSemaphore = threading.Semaphore(value=1)
        self.displaySemaphore = threading.Semaphore(value=0)
        threading.Thread(target=self.display).start()

    def running(self):
        self.recvRtp()

    def recvRtp(self):
        try:
            data = self.socket.recv(20480)
            if data:
                rtpPacket = RtpPacket()
                rtpPacket.decode(data)

                currentFrameNbr = rtpPacket.seqNum()
                print('Current Seq Num: {}'.format(currentFrameNbr))

                if currentFrameNbr > self.frameNum:
                    self.frameNum = currentFrameNbr
                    frame = self.decode(rtpPacket)
                    self.bufferSemaphore.acquire()
                    self.decodeFrame = frame
                    self.displaySemaphore.release()
        except IOError:
            pass

    @staticmethod
    def decode(rtpPacket):
        frame = Image.open(BytesIO(rtpPacket.getPayload()))
        frame = ImageTk.PhotoImage(frame)
        return frame

    def setDisplay(self, displayCallback):
        self.displayCallback = displayCallback

    def display(self):
        while self._stop.is_set():
            self.displaySemaphore.acquire()
            frame = self.decodeFrame
            self.bufferSemaphore.release()
            self.displayCallback(frame)
