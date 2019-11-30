import socket
import threading
import time
from client.VideoClientRtp import VideoClientRtp
from client.AudioClientRtp import AudioClientRtp


class ClientRtspController:
    """
    Controls the RTSP connection, and the RTP streams
    """

    # State
    INIT = 0
    PREPARE = 1
    READY = 2
    PLAYING = 3
    state = INIT

    # RTSP command
    DESCRIBE = 0
    SETUP = 1
    PLAY = 2
    PAUSE = 3
    TEARDOWN = 4
    SET_PARAMETER = 5

    # Video quality
    BLUR = 0
    HD = 1

    def __init__(self, serveraddr, serverport):
        self.serverAddr = serveraddr
        self.serverPort = serverport

        self.videoRtpPort = 0
        self.audioRtpPort = 0

        # Callback function to update the video
        self.updateVideo = None

        self.rtspSeq = 0
        self.sessionid = 0
        self.requestSent = -1
        self.teardownAcked = False

        self.rtspSocket = None

        # Video RTP stream
        self.videoRtp = None
        self.videoLength = 0
        self.videoFrameRate = 0

        # Audio RTP stream
        self.audioRtp = None
        self.audioFrameRate = 0

        self.filename = ''

        self.warningBox = None
        self.recvCallback = None

        # Record the position of each file
        self.memory = {}

    def connectToServer(self):
        """
        Connect to the Server. Start a new RTSP/TCP session.
        """
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print('connected')
        except IOError:
            self.warningBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def setRecvCallback(self, callback):
        self.recvCallback = callback

    def setUpdateVideoCallback(self, callback):
        self.updateVideo = callback

    def describe(self, filename):
        """
        Send DESCRIBE request
        :param filename: the file to describe
        """
        if self.state == self.INIT:
            self.filename = filename
            self.sendRtspRequest(self.DESCRIBE)

    def setup(self):
        """
        Send SETUP request
        """
        if self.state == self.PREPARE:
            self.sendRtspRequest(self.SETUP)

    def play(self, pos=None):
        """
        Send PLAY request
        :param pos: the start position, None means from 0
        """
        if self.state == self.READY:
            # Stop and restart the RTP streams
            self.stopRtp()
            self.openRtpPort()

            self.videoRtp.setDisplay(self.updateVideo)
            self.videoRtp.setInterval(1 / self.videoFrameRate)
            self.videoRtp.setDaemon(True)
            self.videoRtp.start()

            self.audioRtp.setFrameRate(self.audioFrameRate)
            self.audioRtp.setDaemon(True)
            self.audioRtp.start()
            if pos is None:
                if self.filename not in self.memory.keys():
                    self.sendRtspRequest(self.PLAY)
                else:
                    self.sendRtspRequest(self.PLAY, pos=self.memory[self.filename])
            else:
                self.sendRtspRequest(self.PLAY, pos=pos)

    def pause(self):
        """
        Send PAUSE request
        """
        if self.state == self.PLAYING:
            # Record the position of current file
            self.memory[self.filename] = self.getCurrentPosition()
            self.sendRtspRequest(self.PAUSE)

    def teardown(self):
        """
        Send TEARDOWN request
        """
        self.sendRtspRequest(self.TEARDOWN)

    def stop(self):
        """
        Stop current video
        """
        self.pause()
        self.state = self.INIT

    def audioTrackAlign(self, seconds):
        """
        Advance / delay the audio track
        :param seconds: positive for advance, and negative for delay
        """
        self.sendRtspRequest(self.SET_PARAMETER, align=seconds)
        self.audioRtp.clearBuffer()

    def quality(self, level):
        """
        Change video quality
        :param level: 0 for BLUR and 1 for HD
        """
        self.sendRtspRequest(self.SET_PARAMETER, level=level)

    def mute(self):
        """
        Mute the audio
        """
        self.audioRtp.mute()

    def forward(self, seconds):
        """
        Forward the video, negative seconds for backward
        """
        current = self.getCurrentTime()
        aim = current + seconds
        pos = int(aim / self.getTotalTime() * 1000)
        pos = max(0, pos)
        pos = min(1000, pos)
        self.pause()
        time.sleep(0.2)
        self.play(pos)

    def speed(self, level):
        """
        Change the speed
        :param level: 1 or 2
        """
        self.sendRtspRequest(self.SET_PARAMETER, speed=level)
        self.audioRtp.clearBuffer()

    def setScreenSize(self, size):
        """
        Set screen size, related to full screen mode
        :param size: (width, height), -1 is allowed
        """
        self.videoRtp.clearBuffer()
        self.videoRtp.setScreenSize(size)

    def sendRtspRequest(self, requestCode, **kwargs):
        """
        Send RTSP request to the server.
        """

        # Describe request
        if requestCode == self.DESCRIBE and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply, daemon=True).start()
            # Update RTSP sequence number.
            self.rtspSeq += 1

            # Write the RTSP request to be sent.
            request = 'DESCRIBE ' + self.filename + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq)

            # Keep track of the sent request.
            self.requestSent = self.DESCRIBE

        # Setup request
        elif requestCode == self.SETUP and self.state == self.PREPARE:
            # Update RTSP sequence number.
            self.rtspSeq += 1

            self.openRtpPort()
            # Write the RTSP request to be sent.
            request = 'SETUP ' + self.filename + ' RTSP/1.0\nCSeq: ' + str(
                self.rtspSeq) + '\nTransport: RTP/UDP; client_port= ' + str(self.videoRtpPort)

            # Keep track of the sent request.
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            self.rtspSeq += 1
            request = 'PLAY ' + self.filename + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionid)
            if 'pos' in kwargs.keys():
                request = request + '\nRange: npt={}'.format(kwargs['pos'])
            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1
            request = 'PAUSE ' + self.filename + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionid)
            self.requestSent = self.PAUSE

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'TEARDOWN ' + self.filename + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionid)
            self.requestSent = self.TEARDOWN

        elif requestCode == self.SET_PARAMETER:
            self.rtspSeq += 1
            request = 'SET_PARAMETER ' + self.filename + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionid)
            if 'align' in kwargs.keys():
                request = request + '\nalign: ' + str(kwargs['align'])
            elif 'level' in kwargs.keys():
                request = request + '\nlevel: ' + str(kwargs['level'])
            elif 'speed' in kwargs.keys():
                request = request + '\nspeed: ' + str(kwargs['speed'])
            else:
                return
        else:
            return

        # Send the RTSP request using rtspSocket.
        self.rtspSocket.send(request.encode())

        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """
        Receive RTSP reply from the server.
        """
        while True:
            try:
                reply = self.rtspSocket.recv(4096)
            except OSError:
                break
            print('\nreply')
            print(reply.decode('utf-8'))

            if not reply:
                break
            self.parseRtspReply(reply.decode("utf-8"))
            self.recvCallback()
            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.stopRtp()
                try:
                    self.rtspSocket.shutdown(socket.SHUT_RDWR)
                    self.rtspSocket.close()
                except OSError:
                    pass
                break

    def parseRtspReply(self, data):
        """
        Parse the RTSP reply from the server.
        """
        lines = str(data).split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionid == 0:
                self.sessionid = session

            # Process only if the session ID is the same
            if self.sessionid == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.DESCRIBE:
                        self.state = self.PREPARE
                        infolines = lines[3:]
                        self.videoLength = int(infolines[2].split(':')[-1])
                        self.videoFrameRate = int(infolines[3].split(':')[-1])
                        self.audioFrameRate = int(infolines[6].split(':')[-1])
                    elif self.requestSent == self.SETUP:
                        # Update RTSP state.
                        self.state = self.READY
                        # Open RTP port.
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        self.stopRtp()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        self.teardownAcked = True

    def openRtpPort(self):
        """
        Open RTP socket binded to a specified port.
        """
        if self.videoRtp is None:
            try:
                self.videoRtp = VideoClientRtp('')
                self.videoRtpPort = self.videoRtp.getPort()
            except OSError:
                self.warningBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.videoRtpPort)
        if self.audioRtp is None:
            try:
                self.audioRtp = AudioClientRtp('')
                self.audioRtpPort = self.audioRtp.getPort()
            except OSError:
                self.warningBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.audioRtpPort)

    def stopRtp(self):
        """
        Stop the RTP
        """
        if self.videoRtp is not None:
            self.videoRtp.stop()
            self.videoRtp = None
        if self.audioRtp is not None:
            self.audioRtp.stop()
            self.audioRtp = None

    def setWarningBox(self, box):
        self.warningBox = box

    def getCurrentPosition(self):
        """
        Current Position
        :return: position ( .%)
        """
        return int(self.videoRtp.getPosition() / self.videoLength * 1000)

    def getCurrentTime(self):
        """
        Current time
        :return: secs
        """
        return int(self.videoRtp.getPosition() / self.videoFrameRate)

    def getTotalTime(self):
        """
        Total time
        :return: secs
        """
        return int(self.videoLength / self.videoFrameRate)
