import asyncio
import cv2
import numpy as np
import av
from aiortc import MediaStreamTrack

class BallStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self.x, self.y = 160, 120
        self.dx, self.dy = 2, 2
        self.width, self.height = 320, 240

    async def recv(self):
        # pts, time_base = await self.next_timestamp()

        # Create a blank image
        image = np.zeros((self.height, self.width, 3), np.uint8)

        # Bounce the ball around the frame
        self.x += self.dx
        self.y += self.dy
        if self.x <= 0 or self.x >= self.width:
            self.dx *= -1
        if self.y <= 0 or self.y >= self.height:
            self.dy *= -1

        # Draw the ball
        cv2.circle(image, (self.x, self.y), 10, (0, 0, 255), -1)
        frame = av.VideoFrame.from_ndarray(image, format="bgr24")
        # frame.pts, frame.time_base = pts, time_base

        return frame
async def display_frames():
    track = BallStreamTrack()

    while True:
        frame = await track.recv()
        img = frame.to_ndarray(format="bgr24")

        cv2.imshow("Test Frame", img)
        if cv2.waitKey(1) & 0xFF == ord('e'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(display_frames())


#  make a python program that runs from the command line python3 server.py and python3 client.py. Use aiortc built-in TcpSocketSignaling(refer to this link https://github.com/aiortc/aiortc/blob/9f14474c0953b90139c8697a216e4c2cd8ee5504/src/aiortc/contrib/signaling.py#L76), the server should create an aiortc offer and send to client, the client should receive the offer and create an aiortc answer. Specifically, the server should generate a continuous 2d image/frames of a ball bouncing across the screen, and transmit these images to the client via aiortc using frame transport (extend aiortc.MediaStreamTrack). The client should display the received images using opencv, and start a new multiprocessing.Process(process_a). The client should then send the received frame to this process_a using a multiprocessing.Queue. The process_a should parse the image and determine the current location of the ball as x y coordinates, and store the computed coordinate as a multiprocessing.Value. The client should open an aiortc data channel to the server and send each x y coordinate to the server, so that these coordinates are from process_a but sent to server from client main thread.

