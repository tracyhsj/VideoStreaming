import asyncio
import cv2
import numpy as np
import multiprocessing
from aiortc import RTCPeerConnection, RTCIceCandidate
from aiortc.contrib.signaling import TcpSocketSignaling

def find_ball_coordinates(frame):
    """
        Convert to HSV color space to find location of the ball using color detection

        Args:
            frame (multiprocessing.Queue):  frames received by process_a from the client

        Returns:
            int(x), int(y): coordinates of the ball
    """
    # Convert to HSV color space
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Define the first red range in the HSV space and create a mask detecting red pixels
    lower_red = np.array([0, 120, 70])
    upper_red = np.array([10, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red, upper_red)

    # Second range to capture the red shades at the extreme end of the hue spectrum
    lower_red = np.array([170, 120, 70])
    upper_red = np.array([180, 255, 255])
    mask2 = cv2.inRange(hsv, lower_red, upper_red)

    # Combine the masks to cover all possible shades of red
    mask = mask1 + mask2

    # Find contours(continuous lines that bound or cover the full boundary of red areas)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        # If red areas are found, the largest contour is assumed to be the ball
        largest_contour = max(contours, key=cv2.contourArea)
        # finds the smallest enclosing circle of the largest contour, center = ball's coordinates
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        return int(x), int(y)
    return None


def process_a(frame_queue, coordinate_x, coordinate_y):
    """
        Parses the images from multiprocessing.Queue.
        Determine the current location of the ball to be saved in multiprocessing.Value

        Args:
            frame_queue (multiprocessing.Queue):  frames received by process_a from the client
            coordinate_x, coordinate_y (multiprocessing.Value): to update the coordinates of ball

        """
    while True:
        frame = frame_queue.get()
        if frame is None:
            break

        # Process frame to find the ball's coordinates
        ball_loc = find_ball_coordinates(frame)
        if ball_loc:
            x, y = ball_loc
            # Store the ball's locations as multiprocessing.Value(singlt int)
            coordinate_x.value = x
            coordinate_y.value = y



async def run(pc, signaling, frame_queue, coordinate_x, coordinate_y):
    """
           The client displays the received images using opencv
           Sends the received frame from the server to process_a using the multiprocessing.Queue
           Extract ball coordinates from multiprocessing.Value and send back to the server through data channel

           Args:
               pc: RTCPeerConnection
               signaling: TcpSocketSignaling
               frame_queue: multiprocessing.Queue
               coordinate_x, coordinate_y: multiprocessing.Value
    """
    # The client opens an aiortc data channel to the server to send each x y coordinate
    dc = pc.createDataChannel("ball_coordinates")

    @dc.on('open')
    def on_open():
        print("Data channel opened")

    @dc.on('close')
    def on_close():
        print("Data channel closed")

    # the client displays the received images using opencv
    @pc.on("track")
    async def on_track(track):
        while True:
            frame = await track.recv()
            # print("Client: Received Frames from server")
            img = frame.to_ndarray(format="bgr24")
            cv2.imshow("Bouncing Ball", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break

            # The client sends the received frame to process_a using the multiprocessing.Queue "frame_queue"
            frame_queue.put(img)

            # Extract ball coordinates from multiprocessing.Value and send back to the server
            x, y = coordinate_x.value, coordinate_y.value
            if dc.readyState == "open":
                # print(f"Sending coordinates: {x}, {y}, {type(x)}")
                # coordinates are from process_a but sent to server from client main thread.
                dc.send(f"{x},{y}")

    await signaling.connect()

    # Receive offer
    offer = await signaling.receive()
    await pc.setRemoteDescription(offer)

    # Send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await signaling.send(pc.localDescription)

    # Handle signaling messages
    while True:
        message = await signaling.receive()
        if isinstance(message, RTCIceCandidate):
            await pc.addIceCandidate(message)
        elif message is None:
            print("Connection closed")
            break



if __name__ == "__main__":
    signaling = TcpSocketSignaling("127.0.0.1", 8080)
    pc = RTCPeerConnection()

    frame_queue = multiprocessing.Queue() #for sending frame to process_a
    coordinate_x = multiprocessing.Value('i', 0) #for process_a to store coordinates
    coordinate_y = multiprocessing.Value('i', 0)
    # multiprocessing
    process = multiprocessing.Process(target=process_a, args=(frame_queue, coordinate_x, coordinate_y))
    process.start()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(pc, signaling, frame_queue, coordinate_x, coordinate_y))
    except KeyboardInterrupt:
        pass
    finally:
        frame_queue.put(None)  # Signal the process to terminate
        process.join()
        loop.run_until_complete(signaling.close())
        loop.run_until_complete(pc.close())

