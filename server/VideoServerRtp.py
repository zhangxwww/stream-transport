import threading
import cv2
from io import BytesIO

from server.ServerRtp import ServerRtp
from server.RtpPacket import RtpPacket

BUF_SIZE = 16384

class VideoServerRtp(ServerRtp):
    def __init__(self, addr, port, *args, **kwargs):
        super(VideoServerRtp, self).__init__(addr, port, *args, **kwargs)

        self.currentFrame = 0
        self.totalLength = 0
        self.cap = None

        self.currentSeq = 1

        self.bufferSemaphore = None
        self.sendSemaphore = None
        self.encodeFrame = None

    def sendCondition(self):
        return self.currentFrame < self.totalLength

    def beforeRun(self):
        self.bufferSemaphore = threading.Semaphore(value=1)
        self.sendSemaphore = threading.Semaphore(value=0)
        threading.Thread(target=self.sendData).start()

    def running(self):
        self.encode()

    def encode(self):
        if self.cap is None:
            return
        res, frame = self.cap.read()
        frame = cv2.resize(frame, (480, 270))
        if not res:
            return
        encode = cv2.imencode('.jpg', frame)
        if not encode[0]:
            return
        data = encode[1].tobytes()
        self.bufferSemaphore.acquire()
        self.encodeFrame = data
        self.sendSemaphore.release()
        self.currentFrame += 1

    def sendData(self):
        while self._stop.is_set():
            self.sendSemaphore.acquire()
            data = self.encodeFrame
            self.currentFrame += 1
            self.bufferSemaphore.release()

            byteStream = BytesIO(data)
            totalBytes = len(data)
            sentBytes = 0

            packet = RtpPacket()
            while sentBytes < totalBytes:
                sentBytes += BUF_SIZE
                marker = 0 if sentBytes < totalBytes else 1
                bytesToSend = byteStream.read(BUF_SIZE)
                packet.encode(2, 0, 0, 0, self.currentSeq, marker, 26, self.ssrc, bytesToSend)
                self.currentSeq += 1
                self.socket.sendto(packet.getPacket(), (self.clientAddr, self.clientPort))
            byteStream.close()


    def setCapture(self, cap):
        self.cap = cap
        self.totalLength = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fs = cap.get(cv2.CAP_PROP_FPS)
        self.setInterval(1 / fs / 2)

    def setPosition(self, pos):
        self.currentFrame = pos
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
