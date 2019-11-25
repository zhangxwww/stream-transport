import threading
import sounddevice as sd
from io import BytesIO
import numpy as np

from client.RtpPacket import RtpPacket
from client.ClientRtp import ClientRtp

BUF_SIZE = 20480


class AudioClientRtp(ClientRtp):
    def __init__(self, addr, port, *args, **kwargs):
        super(AudioClientRtp, self).__init__(addr, port, *args, **kwargs)

        self.seqNum = 0

        self.bufferSemaphore = None
        self.displaySemaphore = None

        self.fs = None

        self.decodeChunk = None

        self.out = None

    def beforeRun(self):
        self.out = sd.OutputStream()
        self.out.start()
        self.setInterval(0)
        self.bufferSemaphore = threading.Semaphore(value=1)
        self.displaySemaphore = threading.Semaphore(value=0)
        threading.Thread(target=self.recvRtp, daemon=True).start()

    def afterRun(self):
        self.out.close()

    def running(self):
        self.display()

    def recvRtp(self):
        while self._stopper.is_set():
            rtpPacket = RtpPacket()
            byteStream = BytesIO(b'')
            while True:
                try:
                    data = self.socket.recv(BUF_SIZE)
                    if not data:
                        break
                    rtpPacket.decode(data)
                    marker = rtpPacket.marker()
                    currentSeqNbr = rtpPacket.seqNum()

                    if currentSeqNbr > self.seqNum:
                        # TODO check it later
                        self.seqNum = currentSeqNbr
                        byte = rtpPacket.getPayload()
                        byteStream.write(byte)
                    if marker == 1:
                        break
                except IOError:
                    continue
            chunk = self.decode(byteStream)
            byteStream.close()
            self.bufferSemaphore.acquire()
            self.decodeChunk = chunk
            self.displaySemaphore.release()

    def display(self):
        self.displaySemaphore.acquire()
        chunk = self.decodeChunk
        self.bufferSemaphore.release()
        if chunk is None:
            self._display_interval.wait(self.interval)
        else:
            self.out.write(chunk)

    @staticmethod
    def decode(byteStream):
        try:
            chunk = np.frombuffer(byteStream.getvalue(), dtype=np.float32).reshape(-1, 2)
        except ValueError:
            chunk = None
        return chunk

    def setFrameRate(self, fs):
        self.fs = fs
