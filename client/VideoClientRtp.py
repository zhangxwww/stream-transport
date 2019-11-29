import threading
from PIL import Image, ImageTk
from io import BytesIO

from client.ClientRtp import ClientRtp
from client.RtpPacket import RtpPacket
from client.Buffer import BufferQueue

BUF_SIZE = 20480


class VideoClientRtp(ClientRtp):
    def __init__(self, addr, *args, **kwargs):
        super(VideoClientRtp, self).__init__(addr, *args, **kwargs)

        self.seqNum = 0
        self.lastFrameNbr = 0
        self.buffer = BufferQueue()
        self.displayCallback = None

    def beforeRun(self):
        threading.Thread(target=self.recvRtp, daemon=True).start()

    def afterRun(self):
        pass

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
                    # print('Current Seq Num: {}'.format(currentSeqNbr))

                    if currentSeqNbr > self.seqNum:
                        # TODO assume in order
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
            frame = self.decode(byteStream)
            byteStream.close()
            self.buffer.put(lastFrameNbr, frame)

    @staticmethod
    def decode(byteStream):
        try:
            frame = Image.open(byteStream)
            if frame.size[1] != 270:
                frame = frame.resize((480, 270))
            frame = ImageTk.PhotoImage(frame)
        except OSError:
            frame = None
        return frame

    def setDisplay(self, displayCallback):
        self.displayCallback = displayCallback

    def display(self):
        seq, frame = self.buffer.get()
        if frame is None:
            #self._display_interval.wait(self.interval)
            pass
        else:
            self.lastFrameNbr = seq
            self.displayCallback(frame)

    def getPosition(self):
        # frame number
        return self.lastFrameNbr
