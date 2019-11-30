import threading
import cv2
from io import BytesIO

from server.ServerRtp import ServerRtp
from server.RtpPacket import RtpPacket

BUF_SIZE = 16384

BLUR = 0
HD = 1


class VideoServerRtp(ServerRtp):
    """
    Video RTP stream controller
    """

    def __init__(self, addr, *args, **kwargs):
        super(VideoServerRtp, self).__init__(addr, *args, **kwargs)

        # current frame to send
        self.currentFrame = 0
        # n frames of the video
        self.totalLength = 0
        # the video itself
        self.cap = None

        # current seq number of the packet
        self.currentSeq = 1

        # the video quality, represented by the size of each frame
        self.quality = (480, 270)

        # Semaphore to control each thread
        self.bufferSemaphore = None
        self.sendSemaphore = None
        # the encoded frame
        self.encodeFrame = None

    def sendCondition(self):
        """
        Send until meet the end of the video
        """
        return self.currentFrame < self.totalLength

    def beforeRun(self):
        """
        Init the semaphore, and start the encode thread
        """
        self.bufferSemaphore = threading.Semaphore(value=1)
        self.sendSemaphore = threading.Semaphore(value=0)
        threading.Thread(target=self.encode).start()

    def running(self):
        """
        Start to send data
        """
        self.sendData()

    def encode(self):
        """
        Encode next frame
        """
        while self._stopper.is_set():
            if self.cap is None:
                return
            res, frame = self.cap.read()
            if self.doubleSpeed:
                # discard a frame each time if double speed
                res, frame = self.cap.read()
            if not res:
                # fail to get next frame
                return
            # resize the frame
            frame = cv2.resize(frame, self.quality)
            # encode into .jpg format
            encode = cv2.imencode('.jpg', frame)
            if not encode[0]:
                # fail to encode
                return
            data = encode[1].tobytes()
            self.bufferSemaphore.acquire()
            self.encodeFrame = data
            self.sendSemaphore.release()
            self.currentFrame += 1

    def sendData(self):
        """
        Send the encoded frame to the client
        """
        if self.socket is None:
            return
        self.sendSemaphore.acquire()
        data = self.encodeFrame
        self.bufferSemaphore.release()

        byteStream = BytesIO(data)
        totalBytes = len(data)
        sentBytes = 0

        # divide into packets
        packet = RtpPacket()
        while sentBytes < totalBytes:
            sentBytes += BUF_SIZE
            # if it is the last packet
            marker = 0 if sentBytes < totalBytes else 1
            bytesToSend = byteStream.read(BUF_SIZE)
            packet.encode(2, 0, 0, 0, self.currentSeq, marker, 26, self.ssrc, bytesToSend)
            packet.setTimestamp(self.currentFrame)
            self.currentSeq += 1
            self.socket.sendto(packet.getPacket(), (self.clientAddr, self.clientPort))
        byteStream.close()

    def setCapture(self, cap):
        """
        Set the video to be sent
        """
        self.cap = cap
        # n frames
        self.totalLength = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # frame rate
        fs = cap.get(cv2.CAP_PROP_FPS)
        self.setInterval(1 / fs / 1.5)

    def setPosition(self, pos):
        """
        Set the position to read next frame
        :param pos: .%
        """
        self.currentFrame = int(self.totalLength * pos / 1000)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.currentFrame)

    def setQuality(self, level):
        """
        Set the quality of the video
        :param level: 0 for blur and 1 for HD
        """
        if level == HD:
            self.quality = (480, 270)
        elif level == BLUR:
            self.quality = (320, 180)
