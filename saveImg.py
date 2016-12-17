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
counterThing = 0

# - - - - - - - - - - - - - - - - - -
# - - - Image Processor Class - - - - 
# - - - - - - - - - - - - - - - - - -
class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.streams = [io.BytesIO() for i in range(200)]
        self.event = threading.Event()
        self.terminated = False
        self.start()
        self.streamIndex = 0
        self.imgNmbr = []

    def run(self):
        # This method runs in a separate thread
        global done
        global counterThing
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    self.streams[self.streamIndex].seek(0)
                    # Read the image and do some processing on it
                    
                    
                    #self.stream.seek(1)
                    #print(struct.unpack('B', self.stream.read(1))[0])
                    
                    
                    counterThing += 1
                    tmp = counterThing
                    self.imgNmbr.append(tmp)
                    if tmp < 180:
                        print ("taking an image")
                        print (tmp)
                    
                    else:
                        
                        #img.save("outLast.bmp")
                        done = True
                    #...
                    #...
                    # Set done to True if you want the script to terminate
                    # at some point
                    #done=True
                finally:
                    # Reset the stream and event
                    self.streams[self.streamIndex].seek(0)
                    #self.streams[self.streamIndex].truncate()
                    self.streamIndex += 1
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
    print("pool is set up")
    print("wait for some seconds for mem check")
    time.sleep(12)
    print("wait finished")
    camera.resolution = (320, 480)  #196, 256
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

# I am pretty sure the counterThing can be used as is.
# we need to set up a streams array. 







