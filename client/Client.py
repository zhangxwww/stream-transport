import threading
from tkinter import *
import tkinter.messagebox

from client.ClientRtspController import ClientRtspController
from client.FileExplorer import FileExplorer


class Client:
    def __init__(self, serveraddr, serverport, rtpport, filename):
        self.rtspController = None
        self.fileExplorer = None

        self.master = None
        self.describe = None
        self.setup = None
        self.start = None
        self.pause = None
        self.teardown = None
        self.displayLabel = None
        self.scale = None
        self.currentTimeLabel = None
        self.totalTimeLabel = None
        self.currentTimeLabelStringVar = None
        self.totalTimeLabelStringVar = None
        self.searchVar = None
        self.searchEntry = None
        self.fileListBox = None

        self.videoTime = 0

        self.recvRtspCallback = {}
        self.init(serveraddr, serverport, rtpport, filename)

        self.master.mainloop()

    def init(self, serveraddr, serverport, rtpport, filename):
        self.rtspController = ClientRtspController(serveraddr, serverport, rtpport, self.updateVideo, filename)
        self.rtspController.setWarningBox(tkinter.messagebox)
        self.rtspController.connectToServer()
        self.createWidgets()
        self.getRtspRecvCallbackOfEachState()
        self.rtspController.setRecvCallback(self.rtspRecvCallback)
        threading.Thread(target=self.updateTimeLabelThread, daemon=True).start()
        self.fileExplorer = FileExplorer(serveraddr, 20000, self.updateFileListBoxCallback)
        self.enterEntryHandler(None)

    def createWidgets(self):
        """Build GUI."""
        self.master = tkinter.Tk()
        self.master.protocol('WM_DELETE_WINDOW', self.exitHandler)

        leftFrame = tkinter.Frame(self.master, width=30, height=30, bg='pink')
        leftFrame.grid(row=0, column=0, padx=2, pady=2)

        rightFrame = tkinter.Frame(self.master, width=30, height=30, bg='black')
        rightFrame.grid(row=0, column=1, padx=2, pady=2)

        displayArea = tkinter.Frame(leftFrame, width=26, height=21, bg='yellow')
        displayArea.grid(row=0, column=0, padx=1, pady=1)

        scaleArea = tkinter.Frame(leftFrame, width=26, height=5, bg='blue')
        scaleArea.grid(row=1, column=0, padx=1, pady=1)

        buttonArea = tkinter.Frame(leftFrame, width=26, height=5, bg='red')
        buttonArea.grid(row=2, column=0, padx=1, pady=1)

        # Create Describe button
        self.describe = Button(buttonArea, width=20, padx=3, pady=3)
        self.describe["text"] = "Describe"
        self.describe["command"] = self.rtspController.describe
        self.describe.grid(row=1, column=0, padx=2, pady=2)

        # Create Setup button
        self.setup = Button(buttonArea, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.rtspController.setup
        self.setup.grid(row=1, column=1, padx=2, pady=2)

        # Create Play button
        self.start = Button(buttonArea, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.rtspController.play
        self.start.grid(row=1, column=2, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(buttonArea, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.rtspController.pause
        self.pause.grid(row=2, column=0, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(buttonArea, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exit
        self.teardown.grid(row=2, column=1, padx=2, pady=2)

        self.scale = tkinter.Scale(
            scaleArea, from_=0, to=1000,
            showvalue=False, orient='horizontal',
            length=480
        )
        self.scale.grid(row=0, column=0, columnspan=2, padx=2, pady=2)
        self.scale.bind('<Button-1>', self.clickScaleHandler)
        self.scale.bind('<ButtonRelease-1>', self.releaseScaleHandler)

        self.currentTimeLabelStringVar = tkinter.StringVar()
        self.currentTimeLabel = tkinter.Label(
            scaleArea,
            textvariable=self.currentTimeLabelStringVar,
            font=('Arial', 10), anchor=tkinter.NW
        )
        self.currentTimeLabel.grid(
            row=1, column=0, padx=2, pady=2,
            sticky=tkinter.NW
        )
        self.currentTimeLabelStringVar.set('0:00:00')

        self.totalTimeLabelStringVar = tkinter.StringVar()
        self.totalTimeLabel = tkinter.Label(
            scaleArea,
            textvariable=self.totalTimeLabelStringVar,
            font=('Arial', 10), anchor=tkinter.NE
        )
        self.totalTimeLabel.grid(
            row=1, column=1, padx=2, pady=2,
            sticky=tkinter.NE
        )
        self.totalTimeLabelStringVar.set('0:00:00')

        # Create a label to display the movie
        self.displayLabel = Label(displayArea, height=19)
        self.displayLabel.grid(
            row=0, column=0, columnspan=4,
            sticky=W + E + N + S, padx=5, pady=5
        )

        self.searchVar = tkinter.StringVar()
        self.searchEntry = tkinter.Entry(rightFrame, textvariable=self.searchVar)
        self.searchEntry.grid(row=0, column=0, padx=2, pady=2)
        self.searchEntry.bind('<Key-KP_Enter>', self.enterEntryHandler)
        self.searchEntry.bind('<Key-Return>', self.enterEntryHandler)

        listFrame = tkinter.Frame(rightFrame, width=30, height=30, bg='pink')
        listFrame.grid(row=1, column=0, padx=2, pady=2)

        fileListScroll = tkinter.Scrollbar(listFrame)
        self.fileListBox = tkinter.Listbox(listFrame, yscrollcommand=fileListScroll.set)
        fileListScroll.config(command=self.fileListBox.yview)
        fileListScroll.pack(side='right', fill='y')
        self.fileListBox.pack(side='left', fill='both')
        self.fileListBox.bind('<Double-Button-1>', self.doubleClickFileListBoxHandler)

    def exit(self):
        self.rtspController.teardown()
        self.fileExplorer.close()
        self.master.destroy()

    def updateVideo(self, frame):
        self.displayLabel.configure(image=frame, height=270)
        self.displayLabel.image = frame

    def updateTimeLabelThread(self):
        wait = threading.Event()
        while True:
            try:
                pos = self.updateCurrentTimeLabel() / self.videoTime * 1000
                self.scale.set(pos)
            except AttributeError:
                pass
            wait.wait(1)

    def exitHandler(self):
        self.rtspController.pause()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exit()
        else:  # When the user presses cancel, resume playing.
            self.rtspController.play()

    def clickScaleHandler(self, _):
        self.rtspController.pause()

    def releaseScaleHandler(self, _):
        pos = self.scale.get()
        self.rtspController.play(pos=pos)

    def enterEntryHandler(self, _):
        info = self.searchVar.get()
        threading.Thread(target=self.fileExplorer.search, args=(info,), daemon=True).start()

    def doubleClickFileListBoxHandler(self, _):
        print(self.fileListBox.curselection()[0])
        # TODO

    def updateCurrentTimeLabel(self):
        currentTime = self.rtspController.getCurrentTime()
        self.setTimeLabel(
            self.currentTimeLabelStringVar,
            currentTime
        )
        return currentTime

    def updateTotalTimeLabel(self):
        totalTime = self.rtspController.getTotalTime()
        self.setTimeLabel(
            self.totalTimeLabelStringVar,
            totalTime
        )
        self.videoTime = totalTime
        return totalTime

    def updateFileListBoxCallback(self, li):
        self.fileListBox.delete(0, 'end')
        for l in li:
            self.fileListBox.insert('end', l.strip())

    def rtspRecvCallback(self):
        self.recvRtspCallback[self.rtspController.requestSent]()

    def getRtspRecvCallbackOfEachState(self):
        def describe():
            pass

        def setup():
            self.updateCurrentTimeLabel()
            self.updateTotalTimeLabel()

        def play():
            self.updateCurrentTimeLabel()

        def pause():
            pass

        def teardown():
            pass

        self.recvRtspCallback = {
            self.rtspController.DESCRIBE: describe,
            self.rtspController.SETUP: setup,
            self.rtspController.PLAY: play,
            self.rtspController.PAUSE: pause,
            self.rtspController.TEARDOWN: teardown
        }

    def setTimeLabel(self, stringVar, t):
        t = self.getHourMinuteSecond(t)
        timeString = '{hour}:{minute}:{second}'.format(**{
            'hour': t[0],
            'minute': t[1],
            'second': t[2]
        })
        stringVar.set(timeString)

    @staticmethod
    def getHourMinuteSecond(t):
        hour = t // 3600
        minute = (t // 60) % 60
        second = t % 60
        return hour, minute, second


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=554)
    parser.add_argument('--rtpport', type=int, default=44444)
    parser.add_argument('--filename', type=str, default='linker.mp4')

    args = vars(parser.parse_args())

    Client(args['host'], args['port'], args['rtpport'], args['filename'])
