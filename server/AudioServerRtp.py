from io import BytesIO
import numpy as np
import threading

from server.ServerRtp import ServerRtp
from server.RtpPacket import RtpPacket

BUF_SIZE = 16386

class AudioServerRtp(ServerRtp):
    def __init__(self, addr, port, *args, **kwargs):
        super(AudioServerRtp, self).__init__(addr, port, *args, **kwargs)

        self.audio = None

        self.chunkSize = 0
        self.fs = 0

        self.currentChunk = 0
        self.totalChunks = 0

        self.currentSeq = 1

        self.bufferSemaphore = None
        self.sendSemaphore = None

        self.encodeChunk = None

    def sendCondition(self):
        return self.currentChunk < self.totalChunks

    def beforeRun(self):
        self.bufferSemaphore = threading.Semaphore(value=1)
        self.sendSemaphore = threading.Semaphore(value=0)
        threading.Thread(target=self.encode).start()

    def running(self):
        self.sendData()

    def encode(self):
        while self.sendCondition() and self._stop.is_set():
            chunk = self.getCurrentChunkContent().tobytes()
            self.currentChunk += 1
            self.bufferSemaphore.acquire()
            self.encodeChunk = chunk
            self.sendSemaphore.release()

    def sendData(self):
        if self.socket is None:
            return
        self.sendSemaphore.acquire()
        chunk = self.encodeChunk
        self.bufferSemaphore.release()

        byteStream = BytesIO(chunk)
        totalBytes = len(chunk)
        sendBytes = 0

        packet = RtpPacket()
        while sendBytes < totalBytes:
            sendBytes += BUF_SIZE
            marker = 0 if sendBytes < totalBytes else 1
            bytesToSend = byteStream.read(BUF_SIZE)
            packet.encode(2, 0, 0, 0, self.currentSeq, marker, 35, self.ssrc, bytesToSend)
            self.currentSeq += 1
            self.socket.sendto(packet.getPacket(), (self.clientAddr, self.clientPort))
        byteStream.close()

    def setAudio(self, audio, audioLength):
        # audioLength: seconds
        self.setInterval(0.04)
        self.audio = audio
        self.fs = audio.fps
        self.chunkSize = int(self.fs * self.interval)
        self.totalChunks = int(audioLength / self.interval)

    def getCurrentChunkContent(self):
        chunk = np.zeros((self.chunkSize, 2), dtype=np.float32)
        start = self.chunkSize * self.currentChunk / self.fs  # Unit: seconds
        subClip = self.audio.subclip(start, start + self.interval)
        for index, f in enumerate(subClip.iter_frames()):
            if index >= self.chunkSize:
                break
            chunk[index] = f
        return chunk

    def setPosition(self, pos):
        # pos: .%
        self.currentChunk = int(self.totalChunks * pos / 1000)