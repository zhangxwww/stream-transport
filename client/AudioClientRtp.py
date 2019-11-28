import threading
import sounddevice as sd
from io import BytesIO

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
                        self.lastFrameNbr = rtpPacket.timestamp()
                        byte = rtpPacket.getPayload()
                        byteStream.write(byte)
                    if marker == 1:
                        break
                except IOError:
                    continue
                except AttributeError:
                    break
            chunk = byteStream.getbuffer()
            self.buffer.put(self.lastFrameNbr, chunk)

    def display(self):
        chunk = self.buffer.get()
        if chunk is None:
            self._display_interval.wait(self.interval)
        else:
            self.out.write(chunk)

    def setFrameRate(self, fs):
        self.fs = fs
