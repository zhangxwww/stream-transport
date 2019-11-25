from tkinter import *
import tkinter.messagebox

from client.ClientRtspController import ClientRtspController


class Client:
    def __init__(self, serveraddr, serverport, rtpport, filename):
        self.rtspController = None

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

        self.init(serveraddr, serverport, rtpport, filename)
        self.createWidgets()
        self.rtspController.connectToServer()

        self.master.mainloop()

    def init(self, serveraddr, serverport, rtpport, filename):
        self.rtspController = ClientRtspController(serveraddr, serverport, rtpport, self.updateVideo, filename)
        self.rtspController.setWarningBox(tkinter.messagebox)

    def createWidgets(self):
        """Build GUI."""
        self.master = tkinter.Tk()
        self.master.protocol('WM_DELETE_WINDOW', self.exitHandler)

        leftFrame = tkinter.Frame(self.master, width=30, height=30, bg='pink')
        leftFrame.grid(row=0, column=0, padx=2, pady=2)

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

        self.scale = tkinter.Scale(scaleArea, from_=0, to=1000, showvalue=False, orient='horizontal', length=480)
        self.scale.grid(row=0, column=0, columnspan=2, padx=2, pady=2)
        self.scale.bind('<Button-1>', self.clickScaleHandler)
        self.scale.bind('<ButtonRelease-1>', self.releaseScaleHandler)

        self.currentTimeLabel = tkinter.Label(scaleArea, text='0:00:00', font=('Arial', 10), anchor=tkinter.NW)
        self.currentTimeLabel.grid(row=1, column=0, padx=2, pady=2, sticky=tkinter.NW)

        self.totalTimeLabel = tkinter.Label(scaleArea, text='0:00:00', font=('Arial', 10), anchor=tkinter.NE)
        self.totalTimeLabel.grid(row=1, column=1, padx=2, pady=2, sticky=tkinter.NE)

        # Create a label to display the movie
        self.displayLabel = Label(displayArea, height=19)
        self.displayLabel.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    def exit(self):
        self.rtspController.teardown()
        self.master.destroy()

    def updateVideo(self, frame):
        self.displayLabel.configure(image=frame, height=270)
        self.displayLabel.image = frame

    def exitHandler(self):
        self.rtspController.pause()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exit()
        else:  # When the user presses cancel, resume playing.
            self.rtspController.play()

    def clickScaleHandler(self, event):
        print('click')

    def releaseScaleHandler(self, event):
        print('release')
        print(self.scale.get())


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=554)
    parser.add_argument('--rtpport', type=int, default=44444)
    parser.add_argument('--filename', type=str, default='a.mp4')

    args = vars(parser.parse_args())

    Client(args['host'], args['port'], args['rtpport'], args['filename'])
