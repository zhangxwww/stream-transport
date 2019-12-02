# Video Stream Transport Server/Client based on RTSP/RTP/RTCP

## Functionalities

- Support DESCRIBE, SETUP, PLAY, PAUSE, TEARDOWN, SET_PARAMETER commands in RTSP, and support RTP encapsulation.
- Repositioning of play point.
- Change of speed.
- Forward and backward.
- Almost all the video formats supported.
- Multiple clients on a single server.
- Delay or advance audio track.
- Show the play list.
- Search on the server by name or category.
- Switch to full screen.
- Video quality specification.
- Buffer mechanism for better user’s experience.
- Mute.

## Dependencies:

Python3.7

numpy 1.16.3

PIL 6.0.0

sounddevice 0.3.14

cv2 4.1.0

moviepy **1.0.0**

(There are some bugs in moviepy=1.0.1, get more information from https://github.com/Zulko/moviepy/issues/938)

## How to run

### Server

Just like `python3 Server.py --host="0.0.0.0" --port=554 --dir="../../movies/"`

You can also put a json file called ‘category.json’ in `dir`, so that the server can search videos by category. ‘category.json’ just likes:

```json
{
	"category1": ["filename1", "filename2", ...],
	"category2": ["filename3", ...],
}
```

By the way, it’s very slow to start the server. Please wait until ‘listening ... ’ and ‘Search engine listening ...’ are **BOTH** printed on the console.

### Client

`python3 Client.py --host="127.0.0.1" --port=554`

The `port` must be the same with the server. Please wait until the video list are shown in the right of the window.