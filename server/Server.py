import socket
import multiprocessing

from server.ServerRtspController import ServerRtspController


class Server:
    def __init__(self, addr, rtspPort, rtpPort, videoDir):
        self.addr = addr
        self.rtspPort = rtspPort
        self.rtpPort = rtpPort

        self.videoDir = videoDir

        self.listenRtspSocket = None

        self.initConnection()
        self.startServer()

    def initConnection(self):
        self.listenRtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenRtspSocket.bind((self.addr, self.rtspPort))

    def startServer(self):
        self.listenRtspSocket.listen(10)
        print('listening ...')

        while True:
            rtspSocket, clientAddr = self.listenRtspSocket.accept()
            print('{} connected'.format(clientAddr))
            multiprocessing.Process(target=self.handleNewConnection, args=(rtspSocket, clientAddr)).start()

    def handleNewConnection(self, rtspSocket, clientAddr):
        self.listenRtspSocket.close()
        ServerRtspController(rtspSocket, self.addr, self.rtpPort, clientAddr, self.videoDir).start()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--rtspport', type=int, default=554)
    parser.add_argument('--rtpport', type=int, default=22222)
    parser.add_argument('--dir', type=str, default='../../movies/')

    args = vars(parser.parse_args())

    Server(args['host'], args['rtspport'], args['rtpport'], args['dir'])
