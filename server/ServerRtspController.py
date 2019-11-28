import math
import random
import os
import cv2
import socket
from moviepy.editor import AudioFileClip

from server.VideoServerRtp import VideoServerRtp
from server.AudioServerRtp import AudioServerRtp


class ServerRtspController:
    def __init__(self, rtspSocket, addr, port, clientAddr, videoDir):
        self.rtspSocket = rtspSocket
        self.addr = addr
        self.rtpPort = port

        self.clientAddr = clientAddr[0]
        self.clientRtspPort = clientAddr[1]

        self.clientVideoRtpPort = 0

        self.filename = ''
        self.info = None

        self.ssrc = 0
        self.sessionid = 0

        self.cap = None
        self.audioClip = None

        self.videoDir = videoDir

        self.videoRtp = None
        self.audioRtp = None

        self.init()

    def init(self):
        self.ssrc = random.randint(1, 99999)
        self.sessionid = random.randint(1, 99999)

    def start(self):
        while self.rtspSocket is not None:
            request = self.recvRtspRequest()
            print('\nRequest:')
            print(request)
            if not request:
                break
            self.handleRequest(request)
        self.teardown()

    def recvRtspRequest(self):
        try:
            request = self.rtspSocket.recv(2048).decode('utf-8')
        except ConnectionResetError:
            request = ''
        return request

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
            self.clientVideoRtpPort = int(lines[2].split('=')[-1])
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
        response = 'RTSP/1.0 200 OK\nCSeq: {seq}\nSession: {session}'.format(**{
            'seq': seq,
            'session': self.sessionid
        })
        if 'video' in info.keys():
            videoInfo = '\nm=video 0\na=control:streamid=0\na=length:{length}\na=framerate:{fs}'.format(**{
                'length': info['video']['length'],
                'fs': info['video']['framerate']
            })
            response = response + videoInfo
        if 'audio' in info.keys():
            audioInfo = '\nm=audio 0\na=control:streamid=1\na=framerate:{fs}'.format(**{
                'fs': info['audio']['framerate']
            })
            response = response + audioInfo
        self.rtspSocket.send(response.encode())

    def sendSetupResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(
            **{
                'seqNum': seq,
                'session': self.sessionid
            })
        self.rtspSocket.send(response.encode())

    def sendPlayResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def sendPauseResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def sendTearDownResponse(self, seq):
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def getInfo(self, filename):
        self.info = {
            'video': self.getVideoInfo(filename),
            'audio': self.getAudioInfo(filename)
        }
        return self.info

    def getVideoInfo(self, filename):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.cap = cv2.VideoCapture(os.path.join(self.videoDir, filename))
        framerate = math.floor(self.cap.get(cv2.CAP_PROP_FPS))
        length = math.floor(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return {
            'length': length,  # n frames
            'framerate': framerate
        }

    def getAudioInfo(self, filename):
        self.audioClip = AudioFileClip(os.path.join(self.videoDir, filename))
        framerate = math.floor(self.audioClip.fps)
        return {
            'framerate': framerate
        }

    def setup(self):
        self.videoRtp = VideoServerRtp(self.addr, self.rtpPort)
        self.videoRtp.setClientInfo(self.clientAddr, self.clientVideoRtpPort)
        self.videoRtp.setSsrc(self.ssrc)
        self.videoRtp.setCapture(self.cap)

        fs = self.info['video']['framerate']
        self.audioRtp = AudioServerRtp(self.addr, self.rtpPort + 2)
        self.audioRtp.setClientInfo(self.clientAddr, self.clientVideoRtpPort + 2)
        self.audioRtp.setSsrc(self.ssrc)
        self.audioRtp.setAudio(self.audioClip, self.info['video']['length'] / fs, fs)

    def play(self, pos):
        if pos is not None:
            # pos: .%
            self.videoRtp.pause()
            self.videoRtp.setPosition(pos)
            self.videoRtp.resume()
            self.audioRtp.pause()
            self.audioRtp.setPosition(pos)
            self.audioRtp.resume()
        elif self.videoRtp.is_start:
            self.videoRtp.resume()
            self.audioRtp.resume()
        else:
            self.videoRtp.start()
            self.audioRtp.start()

    def pause(self):
        self.videoRtp.pause()
        self.audioRtp.pause()

    def teardown(self):
        if self.videoRtp is not None:
            self.videoRtp.stop()
            self.videoRtp = None
        if self.audioRtp is not None:
            self.audioRtp.stop()
            self.audioRtp = None
        if self.rtspSocket is not None:
            self.rtspSocket.shutdown(socket.SHUT_RDWR)
            self.rtspSocket.close()
            self.rtspSocket = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
