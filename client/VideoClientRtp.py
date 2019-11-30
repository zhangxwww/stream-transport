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

        self.screenSize = (480, 270)

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
            if lastFrameNbr == -1:
                continue
            self.buffer.put(lastFrameNbr, frame)

    def decode(self, byteStream):
        try:
            frame = Image.open(byteStream)
            if frame.size[1] != self.screenSize[1]:
                frame = frame.resize(self.screenSize)
            frame = ImageTk.PhotoImage(frame)
        except OSError:
            frame = None
        return frame

    def setDisplay(self, displayCallback):
        self.displayCallback = displayCallback

    def display(self):
        seq, frame = self.buffer.get()
        if frame is not None:
            self.lastFrameNbr = seq
            self.displayCallback(frame)

    def getPosition(self):
        # frame number
        return self.lastFrameNbr

    def setScreenSize(self, size):
        if size[0] == -1:
            self.screenSize = (int(size[1] * 16 / 9), int(size[1]))
        elif size[1] == -1:
            self.screenSize = (int(size[0]), int(size[0] * 9 / 16))
        else:
            self.screenSize = (int(size[0]), int(size[1]))
