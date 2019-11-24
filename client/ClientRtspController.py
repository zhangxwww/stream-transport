import socket
import threading

from client.VideoClientRtp import VideoClientRtp

class ClientRtspController:
    INIT = 0
    PREPARE = 1
    READY = 2
    PLAYING = 3
    state = INIT

    DESCRIBE = 0
    SETUP = 1
    PLAY = 2
    PAUSE = 3
    TEARDOWN = 4

    def __init__(self, serveraddr, serverport, rtpport, updateVideoCallback, filename):
        self.serverAddr = serveraddr
        self.serverPort = serverport

        self.videoRtpPort = rtpport

        self.updateVideo = updateVideoCallback

        self.rtspSeq = 0
        self.sessionid = 0
        self.requestSent = -1
        self.teardownAcked = False

        self.rtspSocket = None

        self.videoRtp = None
        self.videoLength = 0
        self.videoFrameRate = 0

        self.filename = filename

        self.warningBox = None

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
            print('connected')
        except IOError:
            self.warningBox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)

    def describe(self):
        if self.state == self.INIT:
            self.sendRtspRequest(self.DESCRIBE)

    def setup(self):
        if self.state == self.PREPARE:
            self.sendRtspRequest(self.SETUP)

    def play(self):
        if self.state == self.READY:
            if self.videoRtp is None:
                self.openRtpPort()
            self.videoRtp.setDisplay(self.updateVideo)
            self.videoRtp.setInterval(1 / self.videoFrameRate / 2)
            self.videoRtp.start()
            self.sendRtspRequest(self.PLAY)

    def pause(self):
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def teardown(self):
        self.sendRtspRequest(self.TEARDOWN)

    def sendRtspRequest(self, requestCode):
        """Send RTSP request to the server."""

        # Describe request
        if requestCode == self.DESCRIBE and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq += 1

            # Write the RTSP request to be sent.
            request = 'DESCRIBE ' + self.filename + ' RTSP/1.0\nCSeq: ' + str( self.rtspSeq)

            # Keep track of the sent request.
            self.requestSent = self.DESCRIBE

        # Setup request
        elif requestCode == self.SETUP and self.state == self.PREPARE:
            # Update RTSP sequence number.
            self.rtspSeq += 1

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
        else:
            return

        # Send the RTSP request using rtspSocket.
        self.rtspSocket.send(request.encode())

        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(4096)
            print('\nreply')
            print(reply.decode('utf-8'))

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                if self.videoRtp is not None:
                    self.videoRtp.stop()
                    self.videoRtp = None
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        """Parse the RTSP reply from the server."""
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
                        # TODO parse audio info
                    elif self.requestSent == self.SETUP:
                        # Update RTSP state.
                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        self.videoRtp.stop()
                        self.videoRtp = None
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT
                        self.teardownAcked = True

    def openRtpPort(self):
        """Open RTP socket binded to a specified port."""
        try:
            self.videoRtp = VideoClientRtp('', self.videoRtpPort)
        except OSError:
            self.warningBox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.videoRtpPort)

    def setWarningBox(self, box):
        self.warningBox = box
