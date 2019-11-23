import threading
import cv2

from Rtp import Rtp
from RtpPacket import RtpPacket

class VideoRtp(Rtp):
    def __init__(self, addr, port, *args, **kwargs):
        super(VideoRtp, self).__init__(addr, port, *args, **kwargs)

        self.currentSeq = 0
        self.totalLength = 0
        self.cap = None

        self.bufferSemaphore = None
        self.sendSemaphore = None
        self.encodeFrame = None

    def sendCondition(self):
        return self.currentSeq < self.totalLength

    def beforeRun(self):
        self.bufferSemaphore = threading.Semaphore(value=1)
        self.sendSemaphore = threading.Semaphore(value=0)
        threading.Thread(target=self.sendData).start()

    def running(self):
        self.encode()

    def encode(self):
        res, frame = self.cap.read()
        if not res:
            return
        encode = cv2.imencode('.jpg', frame)
        if not encode[0]:
            return
        data = encode[1].tobytes()
        self.bufferSemaphore.acquire()
        self.encodeFrame = data
        self.sendSemaphore.release()

    def sendData(self):
        while self._stop.is_set():
            self.sendSemaphore.acquire()
            data = self.encodeFrame
            self.currentSeq += 1
            self.bufferSemaphore.release()

            packet = RtpPacket()
            marker = 0 if self.currentSeq < self.totalLength else 1
            packet.encode(2, 0, 0, 0, self.currentSeq - 1, marker, 26, self.ssrc, data)
            self.socket.sendto(packet.getPacket(), (self.clientAddr, self.clientPort))


    def setCapture(self, cap):
        self.cap = cap
        self.totalLength = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fs = cap.get(cv2.CAP_PROP_FPS)
        self.setInterval(1 / fs)

    def setPosition(self, pos):
        self.currentSeq = pos
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

