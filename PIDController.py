import serial

# - - - - - - - - - - - - - - - - - -
# - - - - - PIDController - - - - - - 
# - - - - - - - - - - - - - - - - - -
class PIDController():
    def __init__(self, w, h):
        self.port = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=3.0)
        self.oldCoords = [[0,0,0],[0,0,0],[0,0,0],[0,0,0]] 
        self.oldCoordsEveryStep = [[0,0,0],[0,0,0],[0,0,0],[0,0,0]] 
        self.movingDown = False
        self.waitFlag = False
        self.waitCounter = 0
        self.width = w
        self.height = h
        self.xCor = 0
        self.zCor = 0
        self.upVal = 0.8

    # - - - - - - - - - - - - - - - - - -
    # - - - - - - - Update  - - - - - - - 
    # - - - - - - - - - - - - - - - - - -
    def update(self, x, y, z):
        if self.oldCoordsEveryStep[0][1] < y:
            self.movingDown = True
        else:
            self.movingDown = False

        if self.waitFlag:
            self.waitCounter += 1
        if self.waitCounter >= 16:
            self.waitFlag = False
            self.waitCounter = 0

        # update old Coords
        self.oldCoordsEveryStep.pop(0)           # pop first entry
        self.oldCoordsEveryStep.append([x,y,z])  # append to the end

        if y > 60 and self.movingDown and not self.waitFlag:
            # update old Coords
            self.oldCoords.pop(0)           # pop first entry
            self.oldCoords.append([x,y,z])  # append to the end

            self.waitFlag = True
            self.updatePID()
            #self.sendData()


    # - - - - - - - - - - - - - - - - - -
    # - - - - - - Update PID  - - - - - - 
    # - - - - - - - - - - - - - - - - - -
    def updatePID(self):
        # X Axis
        # P
        _xP = self.oldCoords[3][0]/180.0;  #500
        print("_xP: ", _xP)
        _xD = (self.oldCoords[3][0] - self.oldCoords[2][0])/150.0 #500
        print("_xD: ", _xD)

        self.xCor = round(_xP + _xD, 3)

        _zP = self.oldCoords[3][2] / 30.0 #70
        print("_zP: ", _zP)
        _zD = (self.oldCoords[3][2] - self.oldCoords[2][2])/35.0 #This was commented out
        print("_zD: ", _zD)

        self.zCor = round(_zP + _zD, 3)

    # - - - - - - - - - - - - - - - - - -
    # - - - - - - Send Data - - - - - - - 
    # - - - - - - - - - - - - - - - - - -
    def sendData(self):
        print("will attempt to send some data")
        downStr = "X" + str(self.xCor) + " Y" + str(self.zCor) + " Z" + str(-self.xCor) + "\r\n"
        downHoriStr = "X0.0 Y0.0 Z0.0\r\n"
        upStr = "X" + str(self.xCor + self.upVal) + " Y" + str(self.zCor + self.upVal) + " Z" + str(-self.xCor + self.upVal) + "\r\n"
        print(downStr)
        print(upStr)
        self.port.write(b"\r\n")
        self.port.write(b"G17 G20 G90 G94 G54 G0\r\n")
        #self.port.write(downStr.encode())
        self.port.write(upStr.encode())
        self.port.write(downHoriStr.encode())

