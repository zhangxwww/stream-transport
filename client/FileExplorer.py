import socket


class FileExplorer:
    """
    Show and search videos on server
    """

    def __init__(self, host, port, updateCallback):
        self.socket = None
        self.serverHost = host
        self.serverPort = port
        self.updateCallback = updateCallback

        self.init()
        self.connectToServer()

    def init(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connectToServer(self):
        self.socket.connect((self.serverHost, self.serverPort))

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def search(self, info=''):
        """
        Search videos on server
        :param info: part of the file name, or category. Show all of the videos if info == ''
        """
        try:
            request = 'SEARCH {}'.format(info)
            print(request)
            self.socket.send(request.encode())
            response = self.socket.recv(2048).decode()
            print(response)
            lines = self.parseResponse(response)
            self.updateCallback(lines)
        except ConnectionAbortedError:
            pass

    @staticmethod
    def parseResponse(res):
        lines = res.split('\n')
        return lines[1:]
