import threading
import sounddevice as sd
from io import BytesIO
import numpy as np

from client.RtpPacket import RtpPacket
from client.ClientRtp import ClientRtp
from client.Buffer import BufferQueue

BUF_SIZE = 20480


class AudioClientRtp(ClientRtp):
    def __init__(self, addr, *args, **kwargs):
        super(AudioClientRtp, self).__init__(addr, *args, **kwargs)

        self.seqNum = 0
        self.fs = None
        self.lastFrameNbr = 0
        self.buffer = BufferQueue()
        self.volume = 1
        self.out = None

    def beforeRun(self):
        self.out = sd.RawOutputStream(samplerate=self.fs, channels=2, dtype='float32', blocksize=1)
        self.out.start()
        self.setInterval(0)
        threading.Thread(target=self.recvRtp, daemon=True).start()

    def afterRun(self):
        self.out.close()

    def running(self):
        self.display()

    def recvRtp(self):
        while self._stopper.is_set():
            rtpPacket = RtpPacket()
            byteStream = BytesIO(b'')
            lastFrameNbr = -1
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
                        lastFrameNbr = rtpPacket.timestamp()
                        byte = rtpPacket.getPayload()
                        byteStream.write(byte)
                    if marker == 1:
                        break
                except IOError:
                    continue
                except AttributeError:
                    break
            chunk = np.frombuffer(byteStream.getbuffer())
            if lastFrameNbr == -1:
                continue
            self.buffer.put(lastFrameNbr, chunk)

    def display(self):
        seq, chunk = self.buffer.get()
        if chunk is not None:
            chunk = chunk * self.volume
            self.out.write(chunk.tobytes())
            self.lastFrameNbr = seq

    def setFrameRate(self, fs):
        self.fs = fs

    def clearBuffer(self):
        self.buffer.clear()

    def mute(self):
        if self.volume == 1:
            self.volume = 0
        else:
            self.volume = 1

