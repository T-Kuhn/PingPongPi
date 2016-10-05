import io
import time
import threading
import picamera
import picamera.array
from PIL import Image
import numpy as np
import struct

# - - - - - - - - - - - - - - - - - -
# Create a pool of image processors
# - - - - - - - - - - - - - - - - - -
done = False
lock = threading.Lock()
pool = []
camWidth = 96
camHeight = 128

# - - - - - - - - - - - - - - - - - -
# - - - Image Processor Class - - - - 
# - - - - - - - - - - - - - - - - - -
class ImageProcessor(threading.Thread):
    def __init__(self, w, h, spcr):
        super(ImageProcessor, self).__init__()
        self.width = w
        self.height = h
        self.spacer = spcr
        self.streamOffset = 1
        self.threshold = 55
        # stremOffset = 0 --> use red light
        # stremOffset = 1--> use green light
        # stremOffset = 2 --> use blue light
        self.makeGrid()
        print("width: ", self.width)
        print("height: ", self.height)
        print("spacer: ", self.spacer)
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()

    # - - - - - - - - - - - - - - - - - -
    # - - - - - - Run Method  - - - - - - 
    # - - - - - - - - - - - - - - - - - -
    def run(self):
        # This method runs in a separate thread
        global done
        counterThing = 0
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    self.stream.seek(0)
                    self.gridScan()
                    
                    counterThing += 1
                    if counterThing < 10:
                        print ("taking an image")
                    else:
                        #img.save("out.bmp")
                        done = True
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the pool
                    with lock:
                        pool.append(self)

    # - - - - - - - - - - - - - - - - - -
    # - - - - - Makegrid Method - - - - - 
    # - - - - - - - - - - - - - - - - - -
    def makeGrid(self):
        # In this method we prepare a grid by using:
        # - width
        # - height
        # - spacer
        # The grid is made of values which can directly be used on the stream
        self.grid = []
        self.indexMapX = []
        self.indexMapY = []
        # rgb-Stream: 0,0,0 ,0,0,0, 0,0,0, ... 
        # The stream starts in the top left corner of the image. 
        _x = 0
        _y = 0
        while(_y + 2*self.spacer < self.height):
            while(_x < self.width):
                self.grid.append(self.streamOffset + 3*(_y*self.width + _x))
                self.indexMapX.append(_x)
                self.indexMapY.append(_y)
                _x += self.spacer
            _x = 0
            _y += self.spacer
        print("grid length: ", len(self.grid))
        print("second grid entry :", self.grid[1])

    # - - - - - - - - - - - - - - - - - -
    # - - - - - GridScan Method - - - - - 
    # - - - - - - - - - - - - - - - - - -
    def gridScan(self):
        for index, entry in enumerate(self.grid):
            self.stream.seek(entry)
            if struct.unpack('B', self.stream.read(1))[0] > self.threshold:
                print("found something at:")
                print("x: ", self.indexMapX[index])
                print("y: ", self.indexMapY[index])
                print("start closer examination")
                self.centeringHorizontal(entry)

    # - - - - - - - - - - - - - - - - - -
    # - - Centering Horizontal Method - - 
    # - - - - - - - - - - - - - - - - - -
    def centeringHorizontal(self, streamIndex):
        self.stream.seek(streamIndex)
        # see how far we can go to the left
        # -> searching into the minus

        # see how far we can go to the right
        # -> searching into the plus

        # calculate the new center
        # centerCorrection = (left + right)/2 


    # - - - - - - - - - - - - - - - - - -
    # - - Centering Vertical Method - - - 
    # - - - - - - - - - - - - - - - - - -
    def centeringVertical(self):

# - - - - - - - - - - - - - - - - - -
# - - - - Streams Function  - - - - - 
# - - - - - - - - - - - - - - - - - -
def streams():
    while not done:
        with lock:
            if pool:
                processor = pool.pop()
            else:
                processor = None
        if processor:
            yield processor.stream
            processor.event.set()
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.02)

# - - - - - - - - - - - - - - - - - -
# - - - - - Main Program  - - - - - - 
# - - - - - - - - - - - - - - - - - -
with picamera.PiCamera() as camera:
    pool = [ImageProcessor(camWidth, camHeight, 20) for i in range(4)]
    camera.resolution = (camWidth, camHeight)
    camera.framerate = 90
    time.sleep(2)
    # Now fix the values
    camera.shutter_speed = 2720 #int(camera.exposure_speed/4)
    print(str(camera.shutter_speed))
    camera.exposure_mode = 'off'
    g = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = g
    camera.capture_sequence(streams(), 'rgb', use_video_port=True)

# Shut down the processors in an orderly fashion
while pool:
    with lock:
        processor = pool.pop()
    processor.terminated = True
    processor.join()
