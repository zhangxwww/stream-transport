import threading
from PIL import Image, ImageTk
from io import BytesIO

from client.ClientRtp import ClientRtp
from client.RtpPacket import RtpPacket
from client.Buffer import BufferQueue

BUF_SIZE = 20480


class VideoClientRtp(ClientRtp):
    """
    RTP video stream controller
    """

    def __init__(self, addr, *args, **kwargs):
        super(VideoClientRtp, self).__init__(addr, *args, **kwargs)

        # index of last received frame
        self.lastFrameNbr = 0

        # buffer of the frames
        self.buffer = BufferQueue()

        # callback function to update the label
        self.displayCallback = None

        self.screenSize = (480, 270)

    def beforeRun(self):
        """
        Start to receive from server RTP
        """
        threading.Thread(target=self.recvRtp, daemon=True).start()

    def afterRun(self):
        pass

    def running(self):
        """
        Display for every 'interval' time
        """
        self.display()

    def recvRtp(self):
        """
        Receive RTP packet from server, combine into frames, and save them in the buffer
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
                    # put payloads in buffer, it's more robust when the packets are out of order
                    packetBuffer.put(currentSeqNbr, byte)

                    # marker == 1 means it's the last packet of the frame
                    if marker == 1:
                        while True:
                            seq, byte = packetBuffer.get()
                            if byte is None:
                                break
                            byteStream.write(byte)
                        break
                except IOError:
                    continue
                except AttributeError:
                    break
            # get the frame from the bytes stream
            frame = self.decode(byteStream)
            byteStream.close()
            if lastFrameNbr == -1:
                continue
            self.buffer.put(lastFrameNbr, frame)

    def decode(self, byteStream):
        """
        Decode from the byte stream
        :param byteStream: raw byte stream of the frame
        :return: ImageTk.PhotoImage
        """
        try:
            frame = Image.open(byteStream)
            # resize to the screen size
            if frame.size[1] != self.screenSize[1]:
                frame = frame.resize(self.screenSize)
            frame = ImageTk.PhotoImage(frame)
        except OSError:
            frame = None
        return frame

    def setDisplay(self, displayCallback):
        self.displayCallback = displayCallback

    def display(self):
        """
        Get next frame in the buffer and display it
        """
        seq, frame = self.buffer.get()
        if frame is not None:
            self.lastFrameNbr = seq
            self.displayCallback(frame)

    def getPosition(self):
        """
        Current position
        :return: frame number
        """
        return self.lastFrameNbr

    def setScreenSize(self, size):
        if size[0] == -1:
            self.screenSize = (int(size[1] * 16 / 9), int(size[1]))
        elif size[1] == -1:
            self.screenSize = (int(size[0]), int(size[0] * 9 / 16))
        else:
            self.screenSize = (int(size[0]), int(size[1]))

    def clearBuffer(self):
        """
        Clear the buffer
        """
        self.buffer.clear()
