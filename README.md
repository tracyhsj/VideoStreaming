# Video Streaming with aiortc
 Tracy Hu <br>
 12/29/2023

# Running the program
Run the server program first with the command line 
```
python3 server.py
```

Then run the client program with the command line
```
python3 client.py
```

See screen capture(mp4) for illustrated steps.

Notes:
Press "q" to stop the video frame, control+c to exit.<br>
Received coordiantes, Actual coordinates, and Error are displayed in the console running server.py


## Requirements
```
pip install opencv-python
pip install aiortc
```

## Docker
```
docker build -f Dockerfile.server -t server-image .
docker build -f Dockerfile.client -t client-image .
```
