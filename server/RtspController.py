import random
import os
import cv2
import socket

from VideoRtp import VideoRtp

class RtspController:
    def __init__(self, rtspSocket, addr, port, clientAddr, videoDir):
        self.rtspSocket = rtspSocket
        self.addr = addr
        self.rtpPort = port

        self.clientAddr = clientAddr[0]
        self.clientRtspPort = clientAddr[1]

        self.clientRtpPort = 0

        self.filename = ''

        self.ssrc = 0
        self.sessionid = 0

        self.cap = None

        self.videoDir = videoDir

        self.videoRtp = None

        self.init()

    def init(self):
        self.ssrc = random.randint(1, 99999)
        self.sessionid = random.randint(1, 99999)

    def start(self):
        while self.rtspSocket is not None:
            request = self.recvRtspRequest()
            self.handleRequest(request)

    def recvRtspRequest(self):
        return self.rtspSocket.recv(2048).decode('utf-8')

    def handleRequest(self, request):
        if not request:
            return
        lines = str(request).split('\n')
        seq = int(lines[1].split(' ')[1])
        command, filename = lines[0].split(' ')[:2]
        if command == 'DESCRIBE':
            info = self.getInfo(filename)
            self.sendDescribeResponse(seq, info)
        elif command == 'SETUP':
            self.clientRtpPort = int(lines[2].split('=')[-1])
            self.setup()
            self.sendSetupResponse(seq)
        elif command == 'PLAY':
            self.sendPlayResponse(seq)
            pos = None
            if len(lines) > 3:
                pos = int(lines[3].split(' ')[-1][4:])
            self.play(pos)
        elif command == 'PAUSE':
            self.pause()
            self.sendPauseResponse(seq)
        elif command == 'TEARDOWN':
            self.pause()
            self.sendTearDownResponse(seq)
            self.teardown()
        else:
            return

    def sendDescribeResponse(self, seq, info):
        response = 'RTSP/1.0 200 OK\nCSeq: {seq}\nSession: {session}\n'.format(**{
            'seq': seq,
            'session': self.sessionid
        })
        if 'video' in info.keys():
            videoInfo = 'm=video 0\na=control:streamid=0\na=length:{length}\na=framerate:{fs}'.format(**{
                'length': info['video']['length'],
                'fs': info['video']['framerate']
            })
            response = response + videoInfo
        # TODO audio info
        self.rtspSocket.running(response.encode())

    def sendSetupResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(
            **{
                'seqNum': seq,
                'session': self.sessionid
            })
        self.rtspSocket.running(response.encode())

    def sendPlayResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.running(response.encode())

    def sendPauseResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.running(response.encode())

    def sendTearDownResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.running(response.encode())

    def getInfo(self, filename):
        return {
            'video': self.getVideoInfo(filename)
        }

    def getVideoInfo(self, filename):
        self.cap = cv2.VideoCapture(os.path.join(self.videoDir, filename))
        framerate = self.cap.get(cv2.CAP_PROP_FPS)
        length = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        return {
            'length': length,
            'framerate': framerate
        }

    def getAudioInfo(self, filename):
        pass

    def setup(self):
        self.videoRtp = VideoRtp(self.addr, self.rtpPort)
        self.videoRtp.setClientInfo(self.clientAddr, self.clientRtpPort)
        self.videoRtp.setSsrc(self.ssrc)
        self.videoRtp.setCapture(self.cap)

    def play(self, pos):
        if pos is not None:
            self.videoRtp.pause()
            self.videoRtp.setPosition(pos)
            self.videoRtp.resume()
        elif self.videoRtp.is_start:
            self.videoRtp.resume()
        else:
            self.videoRtp.start()

    def pause(self):
        self.videoRtp.pause()

    def teardown(self):
        self.videoRtp.stop()
        if self.rtspSocket is not None:
            self.rtspSocket.shutdown(socket.SHUT_RDWR)
            self.rtspSocket.close()
            self.rtspSocket = None
        self.cap.release()
        self.cap = None
