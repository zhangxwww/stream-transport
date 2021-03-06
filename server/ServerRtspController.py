import math
import random
import os
import cv2
import socket
from moviepy.editor import AudioFileClip

from server.VideoServerRtp import VideoServerRtp
from server.AudioServerRtp import AudioServerRtp


class ServerRtspController:
    """
    RTSP controller, and controls RTP stream
    """

    def __init__(self, rtspSocket, addr, clientAddr, videoDir):
        self.rtspSocket = rtspSocket
        self.addr = addr

        self.clientAddr = clientAddr[0]
        self.clientRtspPort = clientAddr[1]

        self.clientVideoRtpPort = 0

        # the selected filename
        self.filename = ''
        # video info
        self.info = None

        self.ssrc = 0
        self.sessionid = 0

        # the video and the audio
        self.cap = None
        self.audioClip = None

        # where are the videos
        self.videoDir = videoDir

        # RTP for the video and audio
        self.videoRtp = None
        self.audioRtp = None

        self.init()

    def init(self):
        """
        Generate random int for ssrc and sessionid
        """
        self.ssrc = random.randint(1, 99999)
        self.sessionid = random.randint(1, 99999)

    def start(self):
        """
        Receive and handle request
        """
        while self.rtspSocket is not None:
            request = self.recvRtspRequest()
            print('\nRequest:')
            print(request)
            if not request:
                break
            self.handleRequest(request)
        self.teardown()

    def recvRtspRequest(self):
        """
        Try to receive request
        """
        try:
            request = self.rtspSocket.recv(2048).decode('utf-8')
        except ConnectionResetError:
            request = ''
        return request

    def handleRequest(self, request):
        """
        Handle different request
        """
        if not request:
            return
        lines = str(request).split('\n')
        seq = int(lines[1].split(' ')[1])
        command, filename = lines[0].split(' ')[:2]
        if command == 'DESCRIBE':
            # get info of the video and audio
            info = self.getInfo(filename)
            self.sendDescribeResponse(seq, info)
        elif command == 'SETUP':
            self.clientVideoRtpPort = int(lines[2].split('=')[-1])
            # setup the RTP server
            self.setup()
            self.sendSetupResponse(seq)
        elif command == 'PLAY':
            self.sendPlayResponse(seq)
            pos = None
            if len(lines) > 3:
                pos = int(lines[3].split(' ')[-1][4:])
            # play the video
            self.play(pos)
        elif command == 'PAUSE':
            self.pause()
            self.sendPauseResponse(seq)
        elif command == 'TEARDOWN':
            # pause and teardown
            self.pause()
            self.sendTearDownResponse(seq)
            self.teardown()
        elif command == 'SET_PARAMETER':
            # get the parameter set
            key, value = lines[3].split(':')
            if key == 'align':
                align = float(value)
                self.audioRtp.align(align)
                self.sendSetParameterResponse(seq)
            elif key == 'level':
                level = int(value)
                self.videoRtp.setQuality(level)
                self.sendSetParameterResponse(seq)
            elif key == 'speed':
                speed = int(value)
                self.videoRtp.speed(speed)
                self.audioRtp.speed(speed)
        else:
            return

    def sendDescribeResponse(self, seq, info):
        """
        Generate response for DESCRIBE request
        """
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
        """
        Generate response for SETUP request
        """
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(
            **{
                'seqNum': seq,
                'session': self.sessionid
            })
        self.rtspSocket.send(response.encode())

    def sendPlayResponse(self, seq):
        """
        Generate response for PLAY request
        """
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def sendPauseResponse(self, seq):
        """
        Generate response for PAUSE request
        """
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def sendTearDownResponse(self, seq):
        """
        Generate response for TEARDOWN request
        """
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def sendSetParameterResponse(self, seq):
        """
        Generate response for SET_PARAMETER request
        """
        response = 'RTSP/1.0 200 OK\nCSeq: {seqNum}\nSession: {session}'.format(**{
            'seqNum': seq,
            'session': self.sessionid
        })
        self.rtspSocket.send(response.encode())

    def getInfo(self, filename):
        """
        Get info of the video and audio corresponding to the filename
        """
        self.info = {
            'video': self.getVideoInfo(filename),
            'audio': self.getAudioInfo(filename)
        }
        return self.info

    def getVideoInfo(self, filename):
        """
        Open the video, get the framerate and the length of the video
        """
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
        """
        Extract the audio from the video, get the framerate of the audio
        """
        self.audioClip = AudioFileClip(os.path.join(self.videoDir, filename))
        framerate = math.floor(self.audioClip.fps)
        return {
            'framerate': framerate
        }

    def setup(self):
        """
        Setup RTP of video and audio respectively, and set some parameters
        """
        self.videoRtp = VideoServerRtp(self.addr)
        self.videoRtp.setClientInfo(self.clientAddr, self.clientVideoRtpPort)
        self.videoRtp.setSsrc(self.ssrc)
        self.videoRtp.setCapture(self.cap)

        fs = self.info['video']['framerate']
        self.audioRtp = AudioServerRtp(self.addr)
        self.audioRtp.setClientInfo(self.clientAddr, self.clientVideoRtpPort + 2)
        self.audioRtp.setSsrc(self.ssrc)
        self.audioRtp.setAudio(self.audioClip, self.info['video']['length'] / fs, fs)

    def play(self, pos):
        """
        Start to send data via RTP connection
        :param pos: .%
        """
        # reposition
        if pos is not None:
            self.videoRtp.pause()
            self.videoRtp.setPosition(pos)
            self.audioRtp.pause()
            self.audioRtp.setPosition(pos)
        self.videoRtp.resume()
        self.audioRtp.resume()
        if not self.videoRtp.is_start:
            self.videoRtp.start()
            self.audioRtp.start()

    def pause(self):
        """
        Pause the transport
        """
        self.videoRtp.pause()
        self.audioRtp.pause()

    def teardown(self):
        """
        Teardown the connection, and release the resource
        """
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
