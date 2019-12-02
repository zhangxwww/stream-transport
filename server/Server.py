import socket
import multiprocessing
import sys; sys.path.append('..')

from server.ServerRtspController import ServerRtspController
from server.SearchEngine import SearchEngine


class Server:
    """
    The RTSP server, listening for connection
    """

    def __init__(self, addr, rtspPort, videoDir):
        # host, RTSP port and the RTP port
        self.addr = addr
        self.rtspPort = rtspPort

        # where are the videos
        self.videoDir = videoDir

        # the socket used to listen
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
            # create new process for new connection
            multiprocessing.Process(target=self.handleNewConnection, args=(rtspSocket, clientAddr)).start()

    def handleNewConnection(self, rtspSocket, clientAddr):
        # release the source
        self.listenRtspSocket.close()
        ServerRtspController(rtspSocket, self.addr, clientAddr, self.videoDir).start()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='0.0.0.0')
    parser.add_argument('--port', type=int, default=554)
    parser.add_argument('--dir', type=str, default='../../movies/')

    args = vars(parser.parse_args())

    # the search engine
    multiprocessing.Process(target=SearchEngine, args=(args['host'], 20000, args['dir'])).start()
    # the server
    Server(args['host'], args['port'], args['dir'])
