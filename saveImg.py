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
globalPicCounter = 0

# - - - - - - - - - - - - - - - - - -
# - - - Image Processor Class - - - - 
# - - - - - - - - - - - - - - - - - -
class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.picNmbrMax = 20
        self.streams = [io.BytesIO() for i in range(0, self.picNmbrMax)]
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.streamIndex = 0
        self.imgNmbr = []

    def run(self):
        # This method runs in a separate thread
        global done
        global globalPicCounter
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    self.streams[self.streamIndex].seek(0)
                    
                    globalPicCounter += 1
                    tmp = globalPicCounter
                    self.imgNmbr.append(tmp)
                    print ("taking an image")
                    print (tmp)
                finally:
                    # Reset the stream and event
                    self.streams[self.streamIndex].seek(0)
                    #self.streams[self.streamIndex].truncate()

                    self.streamIndex += 1
                    if self.streamIndex >= self.picNmbrMax:
                        # Set done to True if you want the script to terminate
                        done = True

                    self.event.clear()

                    # Return ourselves to the pool
                    with lock:
                        pool.append(self)

# - - - - - - - - - - - - - - - - - -
# - - - - Streams Function  - - - - - 
# - - - - - - - - - - - - - - - - - -
# This function hands the capture sequence function streams down in which
# it can put the pixeldata
def streams():
    print("start!")
    time.sleep(0.5)
    while not done:
        with lock:
            if pool:
                processor = pool.pop()
            else:
                processor = None
        if processor:
            yield processor.streams[processor.streamIndex]
            processor.event.set()
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.02)
            print("starved!")

# - - - - - - - - - - - - - - - - - -
# - - - - - Main Program  - - - - - - 
# - - - - - - - - - - - - - - - - - -
with picamera.PiCamera() as camera:
    pool = [ImageProcessor() for i in range(4)]
    camera.resolution = (128, 256)  #196, 256
    camera.framerate = 90
    time.sleep(2)
    # Now fix the values
    camera.shutter_speed = 2720 #int(camera.exposure_speed/4)
    print(str(camera.shutter_speed))
    camera.exposure_mode = 'off'
    g = camera.awb_gains
    camera.awb_mode = 'off'
    camera.awb_gains = g
    camera.capture_sequence(streams(), use_video_port=True)
    #camera.capture_sequence(streams(), 'yuv', use_video_port=True)

# if we come this far "done" was set to true!
# Shut down the processors in an orderly fashion
while pool:
    with lock:
        processor = pool.pop()
    for index, nmbr in enumerate(processor.imgNmbr):
        try:
            img = Image.open(processor.streams[index])
            img.save("out" + str(nmbr) + ".bmp")
        except:
            print("couldn't do it")
    processor.terminated = True
    processor.join()



# - - - - - - - - - - - - - - - - - -
# - - - - - - - MEMO  - - - - - - - - 
# - - - - - - - - - - - - - - - - - -

# What is the next step.
# I mean really, what does it look like?
# I think I really want to program a debug function for the ball position determination
# algorithm.
# We are able to get a lot of 90fps pics and save them after recording.
# we just need to add some functionality (the drawing of the ball position point)
# and then, in the end, we should try to implement this thing into the PingPongPi file.








