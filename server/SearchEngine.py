import socket
import multiprocessing
import os
import json

BUF_SIZE = 2048
VALID_EXTENSION = ['.mp4']

class SearchEngine:
    def __init__(self, host, port, workingDir):
        self.host = host
        self.port = port
        self.workingDir = workingDir

        self.category = {}

        self.listenSocket = None

        self.initConnection()
        self.initCategory()
        self.startServer()

    def initConnection(self):
        self.listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listenSocket.bind((self.host, self.port))

    def initCategory(self):
        filename = 'category.json'
        filename = os.path.join(self.workingDir, filename)
        try:
            with open(filename, 'r') as f:
                self.category = json.load(f)
        except FileNotFoundError:
            pass

    def startServer(self):
        self.listenSocket.listen(10)
        print('Search Engine listening ...')

        while True:
            conn, _ = self.listenSocket.accept()
            multiprocessing.Process(target=self.handleNewConnection, args=(conn,)).start()

    def handleNewConnection(self, conn):
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
        files = os.listdir(self.workingDir)
        files = filter(lambda x: x[-4:] in VALID_EXTENSION, files)
        res1 = list(filter(lambda x: x.find(parse) != -1, files))
        res2 = self.category.get(parse.lower(), [])
        files = list(set(res1 + res2))
        files = sorted(files)
        response = '\n'.join(files)
        response = 'FILES\n{}'.format(response)
        return response

