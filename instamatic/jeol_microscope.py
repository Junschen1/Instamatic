import atexit
import comtypes.client

MAGNIFICATIONS = [
 50,
 60,
 80,
 100,
 150,
 200,
 300,
 400,
 500,
 600,
 800,
 1000,
 1200,
 1500,
 2000,
 2500,
 3000,
 4000,
 5000,
 6000,
 8000,
 10000,
 12000,
 15000,
 20000,
 25000,
 30000,
 40000,
 50000,
 60000,
 80000,
 100000,
 120000,
 150000,
 200000,
 250000,
 300000,
 400000,
 500000,
 600000,
 800000,
 1000000,
 1200000,
 1500000,
 2000000]

MAGNIFICATION_MODES = {2500: "mag1", 50: "lowmag"}

FUNCTION_MODES = ('mag1', 'mag2', 'lowmag', 'samag', 'diff')

# constants for Jeol Hex value
ZERO = 32768
MAX = 65535
MIN = 0

class JeolMicroscope(object):
    """docstring for microscope"""
    def __init__(self):
        super(JeolMicroscope, self).__init__()
        
        # initial COM in multithread mode if not initialized otherwise
        try:
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)
        except WindowsError:
            comtypes.CoInitialize()

        # get the JEOL COM library and create the TEM3 object
        temext = comtypes.client.GetModule(('{CE70FCE4-26D9-4BAB-9626-EC88DB7F6A0A}', 3, 0))
        self.tem3 = comtypes.client.CreateObject(temext.TEM3, comtypes.CLSCTX_ALL)
        
        # initialize each interface from the TEM3 object
        self.ht3 = self.tem3.CreateHT3()
        self.eos3 = self.tem3.CreateEOS3()
        self.lens3 = self.tem3.CreateLens3()
        self.def3 = self.tem3.CreateDef3()
        # self.detector3 = self.tem3.CreateDetector3()
        # self.camera3 = self.tem3.CreateCamera3()
        # self.mds3 = self.tem3.CreateMDS3()
        self.stage3 = self.tem3.CreateStage3()
        # self.feg3 = self.tem3.CreateFEG3()
        # self.filter3 = self.tem3.CreateFilter3()
        # self.apt3 = self.tem3.CreateApt3()

        # wait for interface to activate
        t = 0
        while self.ht3.GetHTValue() != 0:
            time.sleep(1)
            t += 1
            if t > 60:
                raise RuntimeError("Cannot establish microscope connection (timeout).")

        atexit.register(self.releaseConnection)

    def __del__(self):
        comtypes.CoUninitialize()

    def getBrightness(self):
        value, result = self.lens3.GetCL3()
        return value

    def setBrightness(self, value):
        self.lens3.setCL3(value)

    def getMagnification(self):
        value, unit_str, label_str, result = self.eos3.GetMagValue()
        return value

    def setMagnification(self, value):
        if value not in MAGNIFICATIONS:
            value = min(MAGNIFICATIONS.keys(), key=lambda x: abs(x-value))
        
        # get best mode for magnification
        for k in sorted(MAGNIFICATION_MODES.keys()):
            if k <= value:
                new_mode = MAGNIFICATION_MODES[k]

        current_mode = self.getFunctionMode()
        if current_mode != new_mode:
            self.setFunctionMode(new_mode)
        
        self.eos3.SetMagValue(value)

    def getMagnificationIndex(self):
        value = self.getMagnification()
        return MAGNIFICATIONS.index(value)

    def setMagnificationIndex(self, index):
        value = MAGNIFICATIONS[index]
        self.setMagnification(value)

    def getGunShift(self):
        x, y, result = self.def3.GetGunA2()
        return x, y

    def setGunShift(self, x, y):
        self.def3.SetGunA2(x, y)

    def getGunTilt(self):
        x, y, result = self.def3.GetGunA1()
        return x, y

    def setGunTilt(self, x, y):
        self.def3.SetGunA1(x, y)

    def getBeamShift(self):
        x, y, result = self.def3.GetCLA1()
        return x, y

    def setBeamShift(self, x, y):
        self.def3.SetCLA1(x, y)

    def getBeamTilt(self):
        x, y, result = self.def3.GetCLA2()
        return x, y

    def setBeamTilt(self, x, y):
        self.def3.SetCLA2(x, y)

    def getImageShift(self):
        x, y, result = self.def3.GetIS1()
        return x,y 

    def setImageShift(self, x, y):
        self.def3.GetIS1(x, y)

    def getStagePosition(self):
        """a and b in degrees"""
        x, y, z, a, b, result = self.stage3.GetPos()
        return x, y, z, a, b

    def isStageMoving(self):
        x, y, z, a, b, result = self.stage3.GetStatus()
        return x or y or z or a or b 

    def waitForStage(self, delay=0.1):
        while self.isStageMoving():
            time.sleep(delay)

    def setStageX(self, value):
        self.stage3.SetX(value)
        self.waitForStage()

    def setStageY(self, value):
        self.stage3.SetY(value)
        self.waitForStage()

    def setStageZ(self, value):
        self.stage3.SetZ(value)
        self.waitForStage()

    def setStageA(self, value):
        self.stage3.SetA(value)
        self.waitForStage()

    def setStageB(self, value):
        self.stage3.SetB(value)
        self.waitForStage()

    def setStagePosition(self, x=None, y=None, z=None, a=None, b=None):
        if z:
            self.setStageZ(z)
        if a:
            self.setStageA(a)
        if b:
            self.setStageB(b)
        if x:
            self.setStageX(x)
        if y:
            self.setStageY(y)

        nx, ny, nz, na, nb = self.getStagePosition()
        if x and nx != x:
            print " >> Warning: stage position x -> requested: {}, got: {}".format(x, nx)
        if y and ny != y:
            print " >> Warning: stage position y -> requested: {}, got: {}".format(y, ny)
        if z and nz != z:
            print " >> Warning: stage position z -> requested: {}, got: {}".format(z, nz)
        if a and na != a:
            print " >> Warning: stage position a -> requested: {}, got: {}".format(a, na)
        if b and nb != b:
            print " >> Warning: stage position b -> requested: {}, got: {}".format(b, nb)

    def getFunctionMode(self): # lowmag, mag1, samag
        """mag1, mag2, lowmag, samag, diff"""
        mode, name, result = self.eos3.GetFunctionMode()
        return FUNCTION_MODES[mode]

    def setFunctionMode(self, value):
        """mag1, mag2, lowmag, samag, diff"""
        if isinstance(value, str):
            try:
                value = FUNCTION_MODES.index(value)
            except ValueError:
                raise ValueError("Unrecognized function mode: {}".format(value))
        self.eos3.SetFunctionMode(value)

    def getDiffractionFocus(self): #IC1
        raise NotImplementedError

    def setDiffractionFocus(self, value): #IC1
        raise NotImplementedError

    def getDiffractionShift(self):
        x, y, result = self.def3.GetPLA()
        return x, y

    def setDiffractionShift(self, x, y):
        self.def3.SetPLA(x, y)

    def releaseConnection(self):
        comtypes.CoUninitialize()
        print "Connection to microscope released"