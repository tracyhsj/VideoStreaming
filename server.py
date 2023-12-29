import asyncio
import cv2
import numpy as np
from aiortc import (RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCIceCandidate)
from aiortc.contrib.signaling import TcpSocketSignaling
import av
# from av import VideoFrame



class BouncingBallStreamTrack(VideoStreamTrack):
    """
        BouncingBallStreamTrack class for the server to generates a continuous 2D frames of a bouncing ball
        Transmit frames to client via aiortc using frame transport
    """
    def __init__(self):
        super().__init__()
        self.width = 640
        self.height = 480
        self.ball_radius = 20
        self.ball_color = (0, 0, 255) # red
        self.position = np.array([self.width // 2, self.height // 2])
        self.velocity = np.array([2, 3])

    def create_ball_frame(self):
        """
        Creat ball frames

        Returns:
             ball frames in ndarray
        """
        frame = np.zeros((self.height, self.width, 3), np.uint8)
        cv2.circle(frame, tuple(self.position), self.ball_radius, self.ball_color, -1)
        return frame

    async def recv(self):
        """
        Generates a continuous 2D frames of a bouncing ball

        Returns:
            Video frame of a bouncing ball
        """
        pts, time_base = await self.next_timestamp()
        self.move_ball()
        frame = self.create_ball_frame()
        video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def move_ball(self):
        self.position += self.velocity
        # Bounce off walls
        if self.position[0] <= self.ball_radius or self.position[0] >= self.width - self.ball_radius:
            self.velocity[0] *= -1
        if self.position[1] <= self.ball_radius or self.position[1] >= self.height - self.ball_radius:
            self.velocity[1] *= -1

    def get_ball_position(self):
        """
        Returns the current position of the ball
        """
        return self.position

async def run(pc, signaling):
    """
       Set up video stream and add to peer connection.
       Display the received coordinates from the client and calculate error

       Args:
           pc : RTCPeerConnection
           signaling : TcpSocketSignaling
    """

    track = BouncingBallStreamTrack()
    pc.addTrack(track)

# Server opens data channel to receive coordinates from the client
    data_channel = pc.createDataChannel("ball_coordinates")

    @data_channel.on("open")
    def on_dc_open():
        print("Server: Data channel opened")
    @data_channel.on("close")
    def on_dc_close():
        print("Server: Data channel closed")


    await signaling.connect()

# Display the received coordinates and calculate error to the actual location of ball
    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        async def on_message(message):
            if message:
                # print(message)
                client_x, client_y = map(int, message.split(','))
                actual_x, actual_y = track.get_ball_position()
                error_x, error_y = actual_x - client_x, actual_y - client_y
                print(f"Received coordinates: ({client_x}, {client_y})")
                print(f"Actual coordinates: ({actual_x}, {actual_y})")
                print(f"Error: ({error_x}, {error_y})")


    # Create and send aiortc offer
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    await signaling.send(pc.localDescription)

    # Handle signaling messages
    while True:
        message = await signaling.receive()
        # print("Received signaling message:", message)
        if isinstance(message, RTCSessionDescription):
            await pc.setRemoteDescription(message)
        elif isinstance(message, RTCIceCandidate):
            await pc.addIceCandidate(message)
        elif message is None:
            print("Connection closed")
            break


if __name__ == "__main__":
    signaling = TcpSocketSignaling("127.0.0.1", 8080)
    pc = RTCPeerConnection()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(pc, signaling))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(pc.close())
