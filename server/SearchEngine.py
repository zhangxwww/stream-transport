import socket
import multiprocessing
import os
import json

BUF_SIZE = 2048
# the file format supported
VALID_EXTENSION = ['mp4', 'avi', 'mkv', 'mov', 'mpg', 'Ogg', 'wmv', '3gp', 'flv', 'vob', 'webm']


class SearchEngine:
    """
    Search the videos on the server
    """

    def __init__(self, host, port, workingDir):
        self.host = host
        self.port = port
        # where are the videos
        self.workingDir = workingDir

        # { 'some category' : ['some video', ...] }
        self.category = {}

        self.listenSocket = None

        self.initConnection()
        self.initCategory()
        self.startServer()

    def initConnection(self):
        """
        Init the socket
        """
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket.bind((self.host, self.port))

    def initCategory(self):
        """
        The server will try to find the 'category.json' in the workingDir
        """
        filename = 'category.json'
        filename = os.path.join(self.workingDir, filename)
        try:
            with open(filename, 'r') as f:
                self.category = json.load(f)
        except FileNotFoundError:
            pass

    def startServer(self):
        """
        Start to listen, and handle the connection in a new process
        """
        self.listenSocket.listen(10)
        print('Search Engine listening ...')

        while True:
            conn, _ = self.listenSocket.accept()
            multiprocessing.Process(target=self.handleNewConnection, args=(conn,)).start()

    def handleNewConnection(self, conn):
        """
        Handle the new connection, receive search requests and send the results
        """
        self.listenSocket.close()
        while True:
            try:
                request = conn.recv(BUF_SIZE).decode()
            except ConnectionResetError:
                request = ''
            if not request:
                break
            if not request[:6] == 'SEARCH':
                continue
            res = self.generateResponse(request[7:]).encode()
            conn.send(res)

    def generateResponse(self, parse):
        """
        Search on the workingDir, and parse the results
        """
        # list all the files in the workingDir
        files = os.listdir(self.workingDir)
        # find files with correct extension
        files = filter(lambda x: x.split('.')[-1] in VALID_EXTENSION, files)
        # find the files, the keywords is a part of witch
        res1 = list(filter(lambda x: x.find(parse) != -1, files))
        # find the files in the category
        res2 = self.category.get(parse.lower(), [])
        # union and sort
        files = list(set(res1 + res2))
        files = sorted(files)
        response = '\n'.join(files)
        response = 'FILES\n{}'.format(response)
        return response
