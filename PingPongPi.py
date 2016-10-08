import io
import time
import threading
import picamera
import picamera.array
from PIL import Image
import numpy as np
import struct
from PIDController import PIDController


# - - - - - - - - - - - - - - - - - -
# Create a pool of image processors
# - - - - - - - - - - - - - - - - - -
done = False
lock = threading.Lock()
pool = []
camWidth = 96 #96
camHeight = 128 #128

# - - - - - - - - - - - - - - - - - -
# - - - Image Processor Class - - - - 
# - - - - - - - - - - - - - - - - - -
class ImageProcessor(threading.Thread):
    def __init__(self, w, h, spcr):
        super(ImageProcessor, self).__init__()
        self.width = w
        self.height = h
        self.objPosX = 0
        self.objPosY = 0
        self.objPosZ = 0
        self.spacer = spcr
        self.streamOffset = 1
        self.centerStreamIndex = 0
        self.threshold = 75
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
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    self.stream.seek(0)
                    self.gridScan()
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
        while(_y + self.spacer < self.height):
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
                self.objPosX = self.indexMapX[index]
                self.objPosY = self.indexMapY[index]
                self.centerStreamIndex = entry
                # print("x: ", self.objPosX)
                # print("y: ", self.objPosY)
                # print("start closer examination")
                self.cenHori()
                self.cenVeri()
                self.cenHori()
                print("found something at:")
                print("x: ", self.objPosX)
                print("y: ", self.objPosY)
                print("z: ", self.objPosZ)
                pidCon.update(self.objPosX, self.objPosY, self.objPosZ)
                break

    # - - - - - - - - - - - - - - - - - -
    # - - Centering Horizontal Method - - 
    # - - - - - - - - - - - - - - - - - -
    def cenHori(self):
        stepsLeft = 0
        stepsRight = 0
        try:
            # see how far we can go to the left
            self.stream.seek(self.centerStreamIndex)
            while(struct.unpack('B', self.stream.read(1))[0] > self.threshold):
                stepsLeft -= 1 
                self.stream.seek(self.centerStreamIndex + stepsLeft*3)
            # print("stepsLeft: ", stepsLeft)
            # see how far we can go to the right
            self.stream.seek(self.centerStreamIndex)
            while(struct.unpack('B', self.stream.read(1))[0] > self.threshold):
                stepsRight += 1 
                self.stream.seek(self.centerStreamIndex + stepsRight*3)
            # print("stepsRight: ", stepsRight)
            # calculate the new center
            centerCor = round((stepsLeft + stepsRight)/2) 
            self.objPosX += centerCor
            self.centerStreamIndex += centerCor*3
            # print("new x: ", self.objPosX)
            
            # calculate Z axis:
            self.objPosZ = stepsRight - stepsLeft
        except:
            pass

    # - - - - - - - - - - - - - - - - - -
    # - - Centering Vertical Method - - - 
    # - - - - - - - - - - - - - - - - - -
    def cenVeri(self):
        stepsUp = 0
        stepsDown = 0
        try:
            # see how far we can go Up 
            self.stream.seek(self.centerStreamIndex)
            while(struct.unpack('B', self.stream.read(1))[0] > self.threshold):
                stepsUp -= 1 
                self.stream.seek(self.centerStreamIndex + stepsUp*3*self.width)
            # print("stepsUp: ", stepsUp)
            # see how far we can go Down 
            self.stream.seek(self.centerStreamIndex)
            while(struct.unpack('B', self.stream.read(1))[0] > self.threshold):
                stepsDown += 1 
                self.stream.seek(self.centerStreamIndex + stepsDown*3*self.width)
            # print("stepsDown: ", stepsDown)
            # calculate the new center
            centerCor = round((stepsUp + stepsDown)/2) 
            self.objPosY += centerCor
            self.centerStreamIndex += centerCor*3*self.width
            # print("new y: ", self.objPosY)
        except:
            pass

# - - - - - - - - - - - - - - - - - -
# - - - - Streams Function  - - - - - 
# - - - - - - - - - - - - - - - - - -
def streams():
    global done
    while not done:
        try:
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
                print("pool is starved")
                time.sleep(0.02)
        except KeyboardInterrupt:
            print ("Ctrl-c pressed ...")
            done = True


# - - - - - - - - - - - - - - - - - -
# - - - - - Main Program  - - - - - - 
# - - - - - - - - - - - - - - - - - -
pidCon = PIDController(camWidth, camHeight)
pidCon.sendData()
with picamera.PiCamera() as camera:
    pool = [ImageProcessor(camWidth, camHeight, 15) for i in range(4)]
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
print("shutting down program")
while pool:
    with lock:
        processor = pool.pop()
    processor.terminated = True
    processor.join()
