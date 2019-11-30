from io import BytesIO
import numpy as np
import threading

from server.ServerRtp import ServerRtp
from server.RtpPacket import RtpPacket

BUF_SIZE = 16386


class AudioServerRtp(ServerRtp):
    """
    RTP audio stream controller
    """

    def __init__(self, addr, *args, **kwargs):
        super(AudioServerRtp, self).__init__(addr, *args, **kwargs)

        # the audio itself
        self.audio = None

        # size of each chunk
        self.chunkSize = 0  # n frames
        # framerate of the audio
        self.fs = 0
        # length of each chunk
        self.chunkLength = 0  # Seconds

        # index of current chunk to be sent
        self.currentChunk = 0
        # total number of chunks
        self.totalChunks = 0

        # packet seq
        self.currentSeq = 1

        # used to control each threads
        self.bufferSemaphore = None
        self.sendSemaphore = None

        # encoded chunk
        self.encodeChunk = None

    def sendCondition(self):
        """
        Send until meet the end of the audio
        :return:
        """
        return self.currentChunk < self.totalChunks

    def beforeRun(self):
        """
        Init the semaphore, and start the encode thread
        :return:
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
        Encode next chunk
        """
        while self.sendCondition() and self._stopper.is_set():
            # get next chunk and trans into bytes
            chunk = self.getCurrentChunkContent().tobytes()
            # skip 1 chunk if double speed
            self.currentChunk += 1 if not self.doubleSpeed else 2
            self.bufferSemaphore.acquire()
            self.encodeChunk = chunk
            self.sendSemaphore.release()

    def sendData(self):
        """
        Send the encoded chunk to the client
        """
        if self.socket is None:
            return
        self.sendSemaphore.acquire()
        chunk = self.encodeChunk
        self.bufferSemaphore.release()

        byteStream = BytesIO(chunk)
        totalBytes = len(chunk)
        sendBytes = 0

        # divide into packets
        packet = RtpPacket()
        while sendBytes < totalBytes:
            sendBytes += BUF_SIZE
            # whether it is the last packet
            marker = 0 if sendBytes < totalBytes else 1
            bytesToSend = byteStream.read(BUF_SIZE)
            packet.encode(2, 0, 0, 0, self.currentSeq, marker, 35, self.ssrc, bytesToSend)
            packet.setTimestamp(self.currentChunk)
            self.currentSeq += 1
            self.socket.sendto(packet.getPacket(), (self.clientAddr, self.clientPort))
        byteStream.close()

    def setAudio(self, audio, audioLength, fs):
        """
        Set the audio to be sent
        :param audio: audio itself
        :param audioLength: seconds
        :param fs: the framerate of the video
        """
        self.setInterval(1 / fs / 1.5)
        # seconds
        self.chunkLength = 1 / fs
        self.audio = audio
        self.fs = audio.fps
        # n frames
        self.chunkSize = int(self.fs * self.chunkLength)
        self.totalChunks = int(audioLength / self.chunkLength)

    def getCurrentChunkContent(self):
        """
        Get the chunk content
        """
        # allocate space
        chunk = np.zeros((self.chunkSize, 2), dtype=np.float32)
        # start position
        start = self.chunkSize * self.currentChunk / self.fs  # Unit: seconds
        # get the sub clip
        subClip = self.audio.subclip(start, start + self.interval)
        # read each frames in the sub clip
        for index, c in enumerate(subClip.iter_frames()):
            if index >= self.chunkSize:
                break
            chunk[index] = c
        return chunk

    def setPosition(self, pos):
        """
        Set the position to get next chunk
        :param pos: .%
        """
        self.currentChunk = int(self.totalChunks * pos / 1000)

    def align(self, align):
        """
        Align the audio track
        :param align: seconds
        """
        deltaChunk = int(align / self.chunkLength)
        self.currentChunk += deltaChunk
