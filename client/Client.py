import time
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
        self.label = None

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

        # Create Describe button
        self.describe = Button(self.master, width=20, padx=3, pady=3)
        self.describe["text"] = "Describe"
        self.describe["command"] = self.rtspController.describe
        self.describe.grid(row=1, column=0, padx=2, pady=2)

        # Create Setup button
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Setup"
        self.setup["command"] = self.rtspController.setup
        self.setup.grid(row=1, column=1, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.rtspController.play
        self.start.grid(row=1, column=2, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.rtspController.pause
        self.pause.grid(row=2, column=0, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Teardown"
        self.teardown["command"] = self.exit
        self.teardown.grid(row=2, column=1, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    def exit(self):
        self.rtspController.teardown()
        #time.sleep(0.5)
        # TODO teardown callback and destroy
        self.master.destroy()

    def updateVideo(self, frame):
        self.label.configure(image=frame, height=270)
        self.label.image = frame

    def exitHandler(self):
        self.rtspController.pause()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.rtspController.teardown()
            self.master.destroy()
        else:  # When the user presses cancel, resume playing.
            self.rtspController.play()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=554)
    parser.add_argument('--rtpport', type=int, default=44444)
    parser.add_argument('--filename', type=str, default='a.mp4')

    args = vars(parser.parse_args())

    Client(args['host'], args['port'], args['rtpport'], args['filename'])
