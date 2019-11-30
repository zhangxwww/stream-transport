import threading
import sounddevice as sd
from io import BytesIO
import numpy as np

from client.RtpPacket import RtpPacket
from client.ClientRtp import ClientRtp
from client.Buffer import BufferQueue

BUF_SIZE = 20480


class AudioClientRtp(ClientRtp):
    """
    RTP audio stream controller
    """

    def __init__(self, addr, *args, **kwargs):
        super(AudioClientRtp, self).__init__(addr, *args, **kwargs)

        # frame rate
        self.fs = None
        # buffer of frames
        self.buffer = BufferQueue()
        # current volume
        self.volume = 1
        # output device
        self.out = None

    def beforeRun(self):
        """
        Start the sound device, and start to receive RTP packet from server
        """
        self.out = sd.RawOutputStream(samplerate=self.fs, channels=2, dtype='float32', blocksize=1)
        self.out.start()
        self.setInterval(0)
        threading.Thread(target=self.recvRtp, daemon=True).start()

    def afterRun(self):
        """
        Close the sound device
        """
        self.out.close()

    def running(self):
        """
        Periodically output sound stream
        """
        self.display()

    def recvRtp(self):
        """
        Receive RTP packet from server
        """
        while self._stopper.is_set():
            rtpPacket = RtpPacket()
            byteStream = BytesIO(b'')
            lastFrameNbr = -1
            packetBuffer = BufferQueue()
            while True:
                try:
                    data = self.socket.recv(BUF_SIZE)
                    if not data:
                        break
                    rtpPacket.decode(data)
                    marker = rtpPacket.marker()
                    currentSeqNbr = rtpPacket.seqNum()

                    lastFrameNbr = rtpPacket.timestamp()
                    byte = rtpPacket.getPayload()
                    # put into buffer
                    packetBuffer.put(currentSeqNbr, byte)

                    if marker == 1:
                        while True:
                            seq, byte = packetBuffer.get()
                            if byte is None:
                                break
                            # combine the bytes
                            byteStream.write(byte)
                        break
                except IOError:
                    continue
                except AttributeError:
                    break
            chunk = np.frombuffer(byteStream.getbuffer())
            if lastFrameNbr == -1:
                continue
            # put the chunk into buffer
            self.buffer.put(lastFrameNbr, chunk)

    def display(self):
        """
        Display the sound
        """
        seq, chunk = self.buffer.get()
        if chunk is not None:
            chunk = chunk * self.volume
            self.out.write(chunk.tobytes())

    def setFrameRate(self, fs):
        self.fs = fs

    def clearBuffer(self):
        self.buffer.clear()

    def mute(self):
        if self.volume == 1:
            self.volume = 0
        else:
            self.volume = 1
