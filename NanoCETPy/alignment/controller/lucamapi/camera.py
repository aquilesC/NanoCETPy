#//
#// Wrapping the Lumenera API into a camera-centric class.
#//
import platform

from .api import *

__version__ = "1.0.1"


class LivePreviewConfig():

    WS_OVERLAPPED       = 0x00000000#L
    WS_POPUP            = 0x80000000#L
    WS_CHILD            = 0x40000000#L
    WS_MINIMIZE         = 0x20000000#L
    WS_VISIBLE          = 0x10000000#L
    WS_DISABLED         = 0x08000000#L
    WS_CLIPSIBLINGS     = 0x04000000#L
    WS_CLIPCHILDREN     = 0x02000000#L
    WS_MAXIMIZE         = 0x01000000#L
    WS_BORDER           = 0x00800000#L
    WS_DLGFRAME         = 0x00400000#L
    WS_CAPTION          = WS_BORDER | WS_DLGFRAME
    WS_VSCROLL          = 0x00200000#L
    WS_HSCROLL          = 0x00100000#L
    WS_SYSMENU          = 0x00080000#L
    WS_THICKFRAME       = 0x00040000#L
    WS_GROUP            = 0x00020000#L
    WS_TABSTOP          = 0x00010000#L

    WS_MINIMIZEBOX      = 0x00020000#L
    WS_MAXIMIZEBOX      = 0x00010000#L

    #//
    #// Common Window Styles
    #//
    WS_OVERLAPPEDWINDOW = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX

    WS_POPUPWINDOW = WS_POPUP | WS_BORDER | WS_SYSMENU

    WS_TILED            = WS_OVERLAPPED
    WS_ICONIC           = WS_MINIMIZE
    WS_SIZEBOX          = WS_THICKFRAME
    WS_TILEDWINDOW      = WS_OVERLAPPEDWINDOW
    

#    def __init__(self, title = "", style = WS_OVERLAPPEDWINDOW, x = 0, y = 0, width = 0, height = 0, hParent = 0, hChild = 0):
#        self.title = title
#        self.style = style
#        self.x = x
#        self.y = y
#        self.width   = width
#        self.height  = height
#        self.hParent = hParent
#        self.hChild  = hChild


class LivePreviewSession():
    """ 
        Manages the starting and stopping of a live preview session
        
        For use this way:
        with LivePreviewSession(camera) as lps:
            do stuff
        #// at this point, the live preview window is killed, and streaming stopped
    """
    
    def __init__(self, camera):
        self.camera = camera
            
    def __enter__(self):
        self.camera.SetStreamState(START_DISPLAY)
        
    def __exit__(self, type, value, traceback):
        self.camera.SetStreamState(STOP_STREAMING)
        self.camera.DestroyLivePreview()        
                

class PropertyLimits():
    def __init__(self, min, max, default, flags):
        self.min = min
        self.max = max
        self.default = default
        self.flags = flags
        
    def __str__(self):
        return "min={0}, max={1}, default={2}, flags=0x{3:08X}".format(self.min, self.max, self.default, self.flags)
        
    __repr__ = __str__


    
#//
#// More pythonic wrapper around the API methods that expect a camera handle.
#// We also check for errors, and raise exceptions as required
#//     
class Camera():
    def __init__(self, api, hCamera, bitsPer16BitPixel = None):
        if api is None:
            raise ValueError("lib parameter is invalid")
        if api.lib is None:
            raise ValueError("lib parameter is invalid")
        if hCamera is None:
            raise ValueError("pCamera parameter is invalid")
            
#       self._api = api
        self._lib = api.lib
        self._hCamera = hCamera
        self._bitsPer16BitPixel = bitsPer16BitPixel
        
    def __str__(self):
        return "hCamera = {0}\n{1}".format(self._hCamera, self.VersionInfo())

    __repr__ = __str__

    #// Bad things happen if the camera is streaming when Python exits.
    def __del__(self):
        self.Close()

    def Close(self):
        if (self._hCamera is not None):
            #// Stop streaming, THEN kill the preview window (not the other way around)
            try:
                self.SetCameraState(self._hCamera, STOP_STREAMING)
            except:
                pass
            try:
                self.DestroyLivePreview()
            except:
                pass
            try:
                self._lib.CameraClose(self._hCamera)
            except:
                pass
        self._hCamera = None
        
    def GetHandle(self):
        return self._hCamera

    #// This must not raise an exception
    def LastError(self):
        return self._lib.GetLastErrorForCamera(self._hCamera)

    def RaiseApiError(self):
        raise ApiError(self.LastError(), self._hCamera)
    
    def Reset(self):
        success = self._lib.CameraReset(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return

    def GetPropertyInfo(self, propertyId):
        (success, value, flags) = self._lib.GetProperty(self._hCamera, propertyId)
        if (0 == success):
            self.RaiseApiError()
        return ( value.value, flags.value )
        
    def GetPropertyValue(self, propertyId):
        return self.GetPropertyInfo(propertyId)[0]
    
    def GetPropertyFlags(self, propertyId):
        return self.GetPropertyInfo(propertyId)[1]
        
    def PropertyIsReadOnly(self, propertyId):
        limits = self.GetPropertyLimits(propertyId)
        if limits.flags & PROPERTY_FLAG_READONLY:
            return True
        else:
            return False
        
    def SetProperty(self, propertyId, value, flags = -1):
        #print("setting property {0} to {1}, {2}".format(propertyId, value, flags))
        if (-1 == flags):
            #print "reading current flags"
            #// Flags not specified. Read current flag settings
            (currValue, flags) = self.GetPropertyInfo(propertyId)
        #print("setting property {0} to {1}, {2}".format(propertyId, value, flags))
        success = self._lib.SetProperty(self._hCamera, propertyId, value, flags)
        if (0 == success):
            self.RaiseApiError()
            
    #// Allow access to the property values using a short-cut.
    #// e.g. camera.exposure is the same as camera.GetPropertyValue(PROPERTY_EXPOSURE)
    def __getattr__(self, name):
        #print "name = '{0}'".format(name)  
        name = name.upper()
        name = 'PROPERTY_' + name
        propertyId = GetPropertyId(name)
        if (-1 != propertyId):
            return self.GetPropertyValue(propertyId)
                
        raise AttributeError(name)

    def __setattr__(self, name, value):
        #print "Set attr {0}={1}".format(name, value)
        #// If it's private, pass it through
        if name.startswith('_'):
            self.__dict__[name] = value
            return
            
        name = name.upper()
        name = 'PROPERTY_' + name
        propertyId = GetPropertyId(name)
        if (-1 != propertyId):  
            #print "Setting property {0}({1}) to {2}".format(name, propertyId, value)
            self.SetProperty(propertyId, value)
            return
                
        raise AttributeError(name)
            
    def GetPropertyLimits(self, propertyId):
        retVals = self._lib.PropertyRange(self._hCamera, propertyId)
        if (0 == retVals[0]):
            self.RaiseApiError()
        return PropertyLimits( retVals[1].value, retVals[2].value, retVals[3].value, retVals[4].value )
        
    def SetStreamState(self, streamState, hWnd = 0):
        success = self._lib.StreamVideoControl(self._hCamera, streamState, hWnd)
        if (0 == success):
            self.RaiseApiError()
        return
    
    def GetFormat(self):
        (success, frameFormat, frameRate) = self._lib.GetFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (frameFormat, frameRate.value)

    def SetFormat(self, frameFormat, frameRate):
        success = self._lib.SetFormat(self._hCamera, frameFormat, frameRate)
        if (0 == success):
            self.RaiseApiError()
        
    def GetFrameFormat(self):
        return self.GetFormat()[0]
        
    def GetFrameRate(self):
        return self.GetFormat()[1]
            
    def GetVideoImageFormat(self):
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return imageFormat
    
    def GetStillImageFormat(self):
        (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return imageFormat
    
    #// Simple value-add method
    def IsColor(self):
        """ Returns True for color cameras, False for mono """
        colorFormat = self.GetPropertyValue(PROPERTY_COLOR_FORMAT)
        return COLOR_FORMAT_MONO != colorFormat
    
    def IsLittleEndian(self):
        flags = self.GetPropertyFlags(PROPERTY_COLOR_FORMAT)
        if (flags & PROPERTY_FLAG_LITTLE_ENDIAN):
            return True
        return False
    
    def _WriteRawDataToFile(self, buffer, fileName):
        """ If the filename is not specified, do nothing """
        if fileName is not None:
            with open(fileName, "wb") as f:
                f.write(buffer)
        return        

    def GetImageIntensity(self, image=None, imageFormat=None, startX=None, startY=None, width=None, height=None):
        frameFormat = self.GetFrameFormat()
        if startX == None:
            startX = 0
        if startY == None:
            startY = 0
        if width == None:
            width = frameFormat.width
        if height == None:
            height = frameFormat.height
        (success, pInt, pR, pG1, pG2, pB) = self._lib.GetImageIntensity(self._hCamera, image, imageFormat, startX, startY, width, height)
        if (0 == success):
            self.RaiseApiError()
        return (pInt, pR, pG1, pG2, pB)

    def CaptureRawVideoImageEx(self, timeout):
        frameFormat = self.GetFrameFormat()
        imageSizeInBytes = frameFormat.GetImageSize()
        buffer = (C.c_ubyte * (imageSizeInBytes))()
        success = self._lib.TakeVideoEx(self._hCamera, buffer, imageSizeInBytes, timeout)
        if (0 == success):
            self.RaiseApiError()
        return (buffer, frameFormat)
    
    def CaptureRawVideoImage(self, fileName = None):
        frameFormat = self.GetFrameFormat()
        imageSizeInBytes = frameFormat.GetImageSize()
        buffer = (C.c_ubyte * (imageSizeInBytes))()
        
        success = self._lib.TakeVideo(self._hCamera, 1, buffer)
        if (0 == success):
            self.RaiseApiError()
            
        self._WriteRawDataToFile(buffer, fileName)
        return (buffer, frameFormat)
    
    def CancelVideo(self):
        success = self._lib.CancelTakeVideo(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (success)        

    def CaptureVideoImage(self, pixelFormat, fileName = None, demosaicMethod = DEMOSAIC_METHOD_HIGH_QUALITY, correctionMatrix = CORRECTION_MATRIX_FLUORESCENT):
        """ Capture a raw video image, and format it to something useful. If a filename is specified, save the formated image to a file """
        (rawBuffer, frameFormat) = self.CaptureRawVideoImage()
        (imageBuffer, frameFormat) = self.ConvertRaw(rawBuffer, frameFormat, pixelFormat, demosaicMethod, correctionMatrix)
        if fileName is not None:
            (imageWidth, imageHeight, numPixels) = frameFormat.GetImageDimensions()
            success = self._lib.SaveImageEx(self._hCamera, imageWidth, imageHeight, pixelFormat, imageBuffer, fileName)
            if (0 == success):
                self.RaiseApiError()
        return (imageBuffer, frameFormat)
        
    def SaveImageToFile(self, fileName, imageBuffer, imageWidth, imageHeight, pixelFormat = PIXEL_FORMAT_24):
        return self._lib.SaveImageEx(self._hCamera, imageWidth, imageHeight, pixelFormat, imageBuffer, fileName)
        
    def ConvertRaw(self, rawBuffer, frameFormat, pixelFormat = PIXEL_FORMAT_24, demosaicMethod = DEMOSAIC_METHOD_HIGH_QUALITY, correctionMatrix = CORRECTION_MATRIX_FLUORESCENT):
        """ 
            Given a raw image from the camera, convert it to another format.
            If you ask for PIXEL_FORMAT_8 for PIXEL_FORMAT_16, we assume you want monochrome.
            GetPixelSize() will raise an error if it's an invalid pixel format
        """
        (imageWidth, imageHeight, numPixels) = frameFormat.GetImageDimensions()
        pixelSize = GetPixelSize(pixelFormat)
        dstBuffer = (C.c_ubyte * int(numPixels * pixelSize))() #################################################################

        conversionParams = LUCAM_CONVERSION()
        conversionParams.DemosaicMethod = demosaicMethod
        conversionParams.CorrectionMatrix = correctionMatrix

        if (PIXEL_FORMAT_8 == pixelFormat):
            success = self._lib.ConvertFrameToGreyscale8(self._hCamera, dstBuffer, rawBuffer, imageWidth, imageHeight, frameFormat.pixelFormat, conversionParams)
        elif (PIXEL_FORMAT_16 == pixelFormat):
            success = self._lib.ConvertFrameToGreyscale16(self._hCamera, dstBuffer, rawBuffer, imageWidth, imageHeight, frameFormat.pixelFormat, conversionParams)
        elif (PIXEL_FORMAT_24 == pixelFormat):
            success = self._lib.ConvertFrameToRgb24(self._hCamera, dstBuffer, rawBuffer, imageWidth, imageHeight, frameFormat.pixelFormat, conversionParams)
        elif (PIXEL_FORMAT_32 == pixelFormat):
            success = self._lib.ConvertFrameToRgb32(self._hCamera, dstBuffer, rawBuffer, imageWidth, imageHeight, frameFormat.pixelFormat, conversionParams)
        elif (PIXEL_FORMAT_48 == pixelFormat):
            success = self._lib.ConvertFrameToRgb48(self._hCamera, dstBuffer, rawBuffer, imageWidth, imageHeight, frameFormat.pixelFormat, conversionParams)
        else:
            raise ApiError(ERROR_INVALID_PIXEL_FORMAT, self._hCamera)
            
        if (0 == success):
            self.RaiseApiError()
        return (dstBuffer, frameFormat)

    def ConvertRawEx(self, rawBuffer, pixelFormat=PIXEL_FORMAT_24, imageFormat=None, conversionParams=None):  # TESTER
        if conversionParams is None:
            conversionParams = self.CreateConversionParams()
        if imageFormat is None:
            (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
            
        (imageWidth, imageHeight, numPixels) = imageFormat.GetImageDimensions()
        pixelSize = GetPixelSize(pixelFormat)
        dstBuffer = (C.c_ubyte * (numPixels * pixelSize))()
        
        if (PIXEL_FORMAT_8 == pixelFormat):
            success = self._lib.ConvertFrameToGreyscale8Ex(self._hCamera, dstBuffer, rawBuffer, imageFormat, conversionParams)
        elif (PIXEL_FORMAT_16 == pixelFormat):
            success = self._lib.ConvertFrameToGreyscale16Ex(self._hCamera, dstBuffer, rawBuffer, imageFormat, conversionParams)
        elif (PIXEL_FORMAT_24 == pixelFormat):
            success = self._lib.ConvertFrameToRgb24Ex(self._hCamera, dstBuffer, rawBuffer, imageFormat, conversionParams)
        elif (PIXEL_FORMAT_32 == pixelFormat):
            success = self._lib.ConvertFrameToRgb32Ex(self._hCamera, dstBuffer, rawBuffer, imageFormat, conversionParams)
        elif (PIXEL_FORMAT_48 == pixelFormat):
            success = self._lib.ConvertFrameToRgb48Ex(self._hCamera, dstBuffer, rawBuffer, imageFormat, conversionParams)
        else:
            raise ApiError(ERROR_INVALID_PIXEL_FORMAT, self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (dstBuffer, imageFormat)
    
    def CreateConversionParams(self, DM = None, CM = None, FlipX = None, FlipY = None, Hue = None, Saturation = None, UseColor = None, Gain = None, WB_U = None, WB_V = None):
        lcp = LUCAM_CONVERSION_PARAMS()
        assert C.sizeof(lcp) == 44 # the expected size of this struct is 44 bytes
        lcp.Size = C.sizeof(lcp)
        if DM is None:
            lcp.DemosaicMethod = DEMOSAIC_METHOD_FAST
        else:
            lcp.DemosaicMethod = DM
        if CM is None:
            lcp.CorrectionMatrix = CORRECTION_MATRIX_FLUORESCENT
        else:
            lcp.CorrectionMatrix = CM
        if FlipX is None:
            lcp.FlipX = 0
        else:
            lcp.FlipX = FlipX
        if FlipY is None:
            lcp.FlipY = 0
        else:
            lcp.FlipY = FlipY
        if Hue is None:
            lcp.Hue = 0.0
        else:
            lcp.Hue = Hue
        if Saturation is None:
            lcp.Saturation = 1.0
        if UseColor is None:
            lcp.UseColorGainsOverWb = 0
        else:
            lcp.UseColorGainsOverWb = UseColor
        if Gain is None:
            lcp.DigitalGain = 1.0
        else:
            lcp.DigitalGain = Gain
        if WB_U is None:
            lcp.DigitalWB_U = 0.0
        else:
            lcp.DigitalWB_U = WB_U
        if WB_V is None:
            lcp.DigitalWB_V = 0.0
        else:
            lcp.DigitalWB_V = WB_V
        return lcp

    def CreateSnapshotSettings(self, exposure = None, gain = None, width = None, height = None, pixelFormat = None, useHardwareTrigger = None, timeout = None):
        """ Return a LUCAM_SNAPSHOT struct that has useful defaults. Adjust as necessary. """
        snapshot = LUCAM_SNAPSHOT()
        assert C.sizeof(snapshot) == 92 # the expected size of this struct is 92 bytes
        if exposure is None:
            snapshot.exposure = self.GetPropertyLimits(PROPERTY_EXPOSURE).default
        else:
            snapshot.exposure = exposure
        if gain is None:
            snapshot.gain = self.GetPropertyLimits(PROPERTY_GAIN).default
        else:
            snapshot.gain = gain
        if self.IsColor():
            snapshot.gainRed    = self.GetPropertyLimits(PROPERTY_GAIN_RED).default
            snapshot.gainBlue   = self.GetPropertyLimits(PROPERTY_GAIN_BLUE).default
            snapshot.gainGreen1 = self.GetPropertyLimits(PROPERTY_GAIN_GREEN1).default
            snapshot.gainGreen2 = self.GetPropertyLimits(PROPERTY_GAIN_GREEN2).default
        else:
            snapshot.gainRed    = 1.0
            snapshot.gainBlue   = 1.0
            snapshot.gainGreen1 = 1.0
            snapshot.gainGreen2 = 1.0
        snapshot.strobe = 0
        snapshot.strobeDelay = 0.0
        if useHardwareTrigger is None:
            snapshot.useHWTrigger = 0
        else:
            snapshot.useHWTrigger = useHardwareTrigger
        if (timeout is None):
            if useHardwareTrigger:
                snapshot.timeout = -1
            else:
                snapshot.timeout = 1000
        else:
            snapshot.timeout = timeout
        snapshot.format.xOffset = 0
        snapshot.format.yOffset = 0
        if width is None:
            snapshot.format.width  = int(self.GetPropertyValue(PROPERTY_MAX_WIDTH))
        else:
            snapshot.format.width = width
        if height is None:
            snapshot.format.height = int(self.GetPropertyValue(PROPERTY_MAX_HEIGHT))
        else:
            snapshot.format.height = height
        if pixelFormat is None:
            snapshot.format.pixelFormat = PIXEL_FORMAT_16
        else:
            snapshot.format.pixelFormat = pixelFormat
        snapshot.format.subSampleX = 1
        snapshot.format.flagsX = 0
        snapshot.format.subSampleY = 1
        snapshot.format.flagsY = 0 
        snapshot.shutterType = SHUTTER_GLOBAL
        snapshot.exposureDelay = 0.0
        snapshot.bufferLastFrame = 0
        snapshot.ulReserved1 = 0
        snapshot.flReserved1 = 0.0
        snapshot.flReserved2 = 0.0
        return snapshot
        
    def CaptureRawSnapshotImage(self, snapshotSettings, fileName = None):
        """ We return a buffer and  frame format, in the same way as TakeVideo does. """
        imageSizeInBytes = snapshotSettings.format.GetImageSize()
        buffer = (C.c_ubyte * int(imageSizeInBytes))() #########################################################################
        success = self._lib.TakeSnapshot(self._hCamera, snapshotSettings, buffer)
        if (0 == success):
            self.RaiseApiError()
        self._WriteRawDataToFile(buffer, fileName)
        return (buffer, snapshotSettings.format)
    
    def CaptureSnapshotImage(self, snapshotSettings, pixelFormat, fileName = None, demosaicMethod = DEMOSAIC_METHOD_HIGH_QUALITY, correctionMatrix = CORRECTION_MATRIX_FLUORESCENT):
        """ Capture a raw snapshot image, and format it to something useful """ 
        (rawBuffer, frameFormat) = self.CaptureRawSnapshotImage(snapshotSettings)
        (imageBuffer, frameFormat) = self.ConvertRaw(rawBuffer, frameFormat, pixelFormat, demosaicMethod, correctionMatrix)
        if fileName is not None:
            (imageWidth, imageHeight, numPixels) = frameFormat.GetImageDimensions()
            success = self._lib.SaveImageEx(self._hCamera, imageWidth, imageHeight, pixelFormat, imageBuffer, fileName)
            if (0 == success):
                self.RaiseApiError()
        return (imageBuffer, frameFormat)

    def EnableFastFrames(self, snapshotSettings):
        success = self._lib.EnableFastFrames(self._hCamera, snapshotSettings)
        if (0 == success):
            self.RaiseApiError()
        return (success)

    def TakeFastFrame(self):
        """ We return a buffer. """
        (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        buffer = (C.c_ubyte * imageFormat.imageSize)()
        success = self._lib.TakeFastFrame(self._hCamera, buffer)
        if (0 == success):
            self.RaiseApiError()
        return (buffer)
    
    def TakeFastFrameNoTrigger(self):
        """ We return a buffer. """
        (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        buffer = (C.c_ubyte * imageFormat.imageSize)()
        success = self._lib.TakeFastFrameNoTrigger(self._hCamera, buffer)
        if (0 == success):
            self.RaiseApiError()
        return (buffer)

    def ForceTakeFastFrame(self):
        (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        buffer = (C.c_ubyte * imageFormat.imageSize)()
        success = self._lib.ForceTakeFastFrame(self._hCamera, buffer)
        if (0 == success):
            self.RaiseApiError()
        return (buffer)

    def TriggerFastFrame(self):
        success = self._lib.TriggerFastFrame(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (success)        

    def SetHwTriggerMode(self):
        success = self._lib.SetTriggerMode(self._hCamera, True)
        if (0 == success):
            self.RaiseApiError()
        return (success)        

    def SetSwTriggerMode(self):
        success = self._lib.SetTriggerMode(self._hCamera, False)
        if (0 == success):
            self.RaiseApiError()
        return (success)        

    def CancelTakeFastFrame(self):
        success = self._lib.CancelTakeFastFrame(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (success)        

    def DisableFastFrames(self):
        success = self._lib.DisableFastFrames(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (success)        

    def GetPixelFormat(self):
        return self.GetFrameFormat().pixelFormat

    def DualTapCorrect(self, imageData, videoMode=True):
        imageFormat = None
        if videoMode:
            (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        else:
            (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.PerformDualTapCorrection(self._hCamera, imageData, imageFormat)
        if (0 == success):
            self.RaiseApiError()
        return (success)
                
    def MultiTapCorrect(self, imageData, videoMode=True):
        imageFormat = None
        if videoMode:
            (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        else:
            (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.PerformMultiTapCorrection(self._hCamera, imageData, imageFormat)
        if (0 == success):
            self.RaiseApiError()
        return (success)
                
    def MonoGridCorrection(self, imageData, videoMode=True):
        imageFormat = None
        if videoMode:
            (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        else:
            (success, imageFormat) = self._lib.GetStillImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.PerformMonoGridCorrection(self._hCamera, imageData, imageFormat)
        if (0 == success):
            self.RaiseApiError()
        return (success)

    def SetPixelFormat(self, pixelFormat):
        (frameFormat, frameRate) = self.GetFormat()
        frameFormat.pixelFormat = pixelFormat
        success = self._lib.SetFormat(self._hCamera, frameFormat, frameRate)
        if (0 == success):
            self.RaiseApiError()

    def DisplayPropertyPage(self, hWnd = 0):
        return self._lib.DisplayPropertyPage(self._hCamera, hWnd)

    def DisplayVideoFormatPage(self, hWnd = 0):
        return self._lib.DisplayVideoFormatPage(self._hCamera, hWnd)

    def VersionInfo(self):
        (success, versionInfo) = self._lib.QueryVersion(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return versionInfo
        
    def SerialNumber(self):
        return self.VersionInfo().serialnumber
        
    def InterfaceType(self):
        interfaceType = C.c_ulong(0)
        (success, interfaceType) = self._lib.QueryExternInterface(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return int(interfaceType)
        
    def ModelId(self):
        (success, modelId) = self._lib.GetCameraId(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return int(modelId)
        
    def HardwareRevision(self):
        (success, hardwareRevision) = self._lib.GetHardwareRevision(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return hardwareRevision
        
    def LivePreviewFrameRate(self):
        (success, frameRate) = self._lib.QueryDisplayFrameRate(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return frameRate.value

    def CreateLivePreview(self, title = "", style = None, x = 0, y = 0, width = 0, height = 0, hParentId = 0, hChildId = 0):
        if style is None:
            style = LivePreviewConfig.WS_OVERLAPPED|LivePreviewConfig.WS_MINIMIZEBOX|LivePreviewConfig.WS_CAPTION|LivePreviewConfig.WS_SYSMENU|LivePreviewConfig.WS_VISIBLE
        if 0 == width:
            width = self.GetFrameFormat().width / 2
        if 0 == height:
            height = self.GetFrameFormat().height / 2
        success = self._lib.CreateDisplayWindow(self._hCamera, title, style, x, y, width, height, hParentId, hChildId)
        if (0 == success):
            self.RaiseApiError()
        
    def AdjustLivePreview(self, title = "", x = 0, y = 0, width = 0, height = 0):
        success = self._lib.AdjustDisplayWindow(self._hCamera, title, x, y, width, height)
        if (0 == success):
            self.RaiseApiError()
        
    def DestroyLivePreview(self):
        success = self._lib.DestroyDisplayWindow(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return
        
    def GpoSelect(self, enableBits):
        success = self._lib.GpoSelect(self._hCamera, enableBits)
        if (0 == success):
            self.RaiseApiError()

    #// For Lm and Lt cameras only
    def GpioConfigure(self, configureBits):
        success = self._lib.GpioConfigure(self._hCamera, configureBits)
        if (0 == success):
            self.RaiseApiError()

    #// Returns (output bits, input bits)
    def GpioRead(self):
        (success, outputBits, inputBits) = self._lib.GpioRead(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (outputBits.value, inputBits.value)
    
    #// Returns the current state of the general purpose input bits
    def GpiRead(self):
        return self.GpioRead()[1]
        
    #// What are the current settings for the outputs?
    def GpoRead(self):
        return self.GpioRead()[0]

    def GpoWrite(self, outputBits):
        success = self._lib.GpioWrite(self._hCamera, outputBits)
        if (0 == success):
            self.RaiseApiError()

    def SupportedFrameRates(self):
        (count, _) = self._lib.EnumAvailableFrameRates(self._hCamera, 0)
        if 0 == count:
            return ()
        (count, tempFrameRates) = self._lib.EnumAvailableFrameRates(self._hCamera, count)
        #// Convert from tuple of C.c_float to array of float
        frameRates = []
        for frameRate in range(count):
            frameRates += (tempFrameRates[frameRate],)
        return frameRates
    
    def BitsPer16BitPixel(self):
        if self._bitsPer16BitPixel is not None:
            return self._bitsPer16BitPixel
        (success, maxBitsPerPixel) = self._lib.GetTruePixelDepth(self._hCamera)
        if 0 == success:
            print("Warning! Can't determine bits per 16-bit pixel. Assuming 10.")
            return 10
        return maxBitsPerPixel
        
    def ReadRegisters(self, baseAddress, numRegs):
        """ Return an array of register values """ 
        (success, registerArray)  = self._lib.ReadRegister(self._hCamera, baseAddress, numRegs)
        if (0 == success):
            self.RaiseApiError()
        return map(int, registerArray)
        
    def ReadRegister(self, baseAddress):
        """ Return a register value """ 
        dataArray = self.ReadRegisters(baseAddress, 1)
        assert 1 == len(dataArray) 
        return dataArray[0]
        
    def WriteRegisters(self, baseAddress, registers):
        if (baseAddress < 0) or (0 == len(registers)):
            raise ApiError(ERROR_INVALID_PARAMETER, self._hCamera)
        ulongValueArray = [C.c_ulong(r) for r in registers]
        success = self._lib.WriteRegister(self._hCamera, baseAddress, len(ulongValueArray), ulongValueArray)
        if (0 == success):
            self.RaiseApiError()

    def WriteRegister(self, baseAddress, value):
        return self.WriteRegisters(baseAddress, [value])

    def ReadPermanentBuffer(self, offset, length):
        if (offset < 0) or (length < 0):
            raise ApiError(ERROR_INVALID_PARAMETER, self._hCamera)
        (success, buf) = self._lib.PermBufferRead(self._hCamera, offset, length)
        if (0 == success):
            self.RaiseApiError()
        return (success, buf)

    def WritePermanentBuffer(self, data, offset):
        if (offset < 0) or (0 == len(data)):
            raise ApiError(ERROR_INVALID_PARAMETER, self._hCamera)
        return self._lib.PermBufferWrite(self._hCamera, data, offset)

    def SetCustomMatrix(self, matrixValues):
        if (3 != len(matrixValues)):
            raise ApiError(ERROR_INVALID_PARAMETER, self._hCamera)
        for r in range(len(matrixValues)):
            if (3 != len(matrixValues[r])):
                raise ApiError(ERROR_INVALID_PARAMETER, self._hCamera)
        
        #// Convert from 2D array of floats to 1D array of C.c_floats
        floatValues = (C.c_float * 9)()
        for r in range(len(matrixValues)):
            for c in range(len(matrixValues[r])):
                floatValues[r * 3 + c] = matrixValues[r][c]
        
        success = self._lib.SetupCustomMatrix(self._hCamera, floatValues)
        if (0 == success):
            self.RaiseApiError()

    def GetLivePreviewMatrix(self):
        """ Returns a 2D matrix """
        (success, matrixArray) = self._lib.GetCurrentMatrix(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        #// Convert from 1D array of C.c_floats to 2D array of floats.
        matrix2D = [[ matrixArray[r * 3 + c] for c in range(3)] for r in range(3)]
        return matrix2D
        
    def OneShotAutoExposure(self, target):
        assert target >= 0
        assert target <= 255
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.OneShotAutoExposure(self._hCamera, target, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def OneShotAutoExposureEx(self, target, period):
        assert target >= 0
        assert target <= 255
        assert period >= 0
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.OneShotAutoExposureEx(self._hCamera, target, 0, 0, imageFormat.width, imageFormat.height, period)
        if (0 == success):
            self.RaiseApiError()
        return success
        
    def OneShotAutoGain(self, target):
        assert target >= 0
        assert target <= 255
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.OneShotAutoGain(self._hCamera, target, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def OneShotAutoIris(self, target):
        assert target >= 0
        assert target <= 255
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.OneShotAutoIris(self._hCamera, target, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def OneShotAutoWhiteBalance(self):
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.OneShotAutoWhiteBalance(self._hCamera, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def OneShotAutoWhiteBalanceEx(self):
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.OneShotAutoWhiteBalanceEx(self._hCamera, 1.0, 1.0, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def DigitalWhiteBalance(self):
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.DigitalWhiteBalance(self._hCamera, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def DigitalWhiteBalanceEx(self):
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.DigitalWhiteBalanceEx(self._hCamera, 1.0, 1.0, 0, 0, imageFormat.width, imageFormat.height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def WhiteBalanceFromSnapshot(self, snapshotSettings, imageData):
        ff = snapshotSettings.format
        success = self._lib.AdjustWhiteBalanceFromSnapshot(self._hCamera, snapshotSettings, imageData, 1.0, 1.0,
                                                           ff.xOffset, ff.yOffset, ff.width/ff.subSampleX, ff.height/ff.subSampleY)
        if (0 == success):
            self.RaiseApiError()
        return success

    def ContinuousAutoExposureEnable(self, target):
        assert target >= 0
        assert target <= 255
        (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.ContinuousAutoExposureEnable(self._hCamera, target, 0, 0, imageFormat.width, imageFormat.height, 8.333)
        if (0 == success):
            self.RaiseApiError()
        return success

    def ContinuousAutoExposureDisable(self):
        success = self._lib.ContinuousAutoExposureDisable(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return success

    def InitAutoLens(self, force=False):
        success = self._lib.InitAutoLens(self._hCamera, force)
        if (0 == success):
            self.RaiseApiError()
        return success
    
    def AutoFocusStart(self, startX, startY, width, height, _callback = None):
        if( _callback != None) and (platform.system() == 'Windows' ):
            #CB = C.WINFUNCTYPE(BOOL, C.c_void_p, C.c_float)#C.c_float)
            #_callback = CB(_callback)
            #print "Not using callback for windows. There is an issue with the python wrapper that causes it to crash!"
            _callback = None
        elif (_callback != None) and (platform.system() == 'Linux'):
            CB = C.CFUNCTYPE(None, C.c_void_p, C.c_float, C.c_ulong)
            _callback = CB(_callback)
        success = self._lib.AutoFocusStart(self._hCamera,startX,startY,width,height,_callback)
        if (0 == success):
           self.RaiseApiError()  
        return success

    def AutoFocusWait(self, timeout):
        success = self._lib.AutoFocusWait(self._hCamera, timeout)
        return success

    def AutoFocusStop(self):
        success = self._lib.AutoFocusStop(self._hCamera)
        print("Success: " + str(success))
        if (0 == success):
            self.RaiseApiError()
        return success

    def AutoFocusQueryProgress(self):
        (success, progress) = self._lib.AutoFocusQueryProgress(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (success, progress)

    def AlignDataLsb(self, imageData, imageFormat=None):
        if imageFormat is None:
            (success, imageFormat) = self._lib.GetVideoImageFormat(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        success = self._lib.DataLsbAlign(self._hCamera,imageFormat,imageData)
        if (0 == success):
            self.RaiseApiError()

    def AutoRoiGet(self):
        (success, startX, startY, width, height) = self._lib.AutoRoiGet(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return (startX, startY, width, height)

    def AutoRoiSet(self, startX, startY, width, height):
        success = self._lib.AutoRoiSet(self._hCamera, startX, startY, width, height)
        if (0 == success):
            self.RaiseApiError()
        return success

    def SetVideoTimeout(self, timeout):
        success = self._lib.SetTimeout(self._hCamera, False, timeout)
        if (0 == success):
            self.RaiseApiError()
        return success

    def SetStillTimeout(self, timeout):
        success = self._lib.SetTimeout(self._hCamera, True, timeout)
        if (0 == success):
            self.RaiseApiError()
        return success

    def EnableTimestamp(self):
        success = self._lib.EnableTimestamp(self._hCamera, True)
        if (0 == success):
            self.RaiseApiError()
        return success
    
    def DisableTimestamp(self):
        success = self._lib.EnableTimestamp(self._hCamera, False)
        if (0 == success):
            self.RaiseApiError()
        return success
    
    def IsTimestampEnabled(self):
        (success, enabled) = self._lib.IsTimestampEnabled(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return enabled
        
    def SetTimestamp(self, newTimestamp):
        success = self._lib.SetTimestamp(self._hCamera, newTimestamp)
        if (0 == success):
            self.RaiseApiError()
        return success
    
    def Setup8bitsLUT(self, lut, length):
        # lut should be a list like [0, 1, 2, ..., etc]
        success = self._lib.Setup8bitsLUT(self._hCamera, lut, length)
        if (0 == success):
            self.RaiseApiError()
        return success

    def Setup8bitsColorLUT(self, lut, length, applyOnRed, applyOnGreen1, applyOnGreen2, applyOnBlue):
        # lut should be a list like [0, 1, 2, ..., etc]
        success = self._lib.Setup8bitsColorLUT(self._hCamera, lut, length, applyOnRed, applyOnGreen1, applyOnGreen2, applyOnBlue)
        if (0 == success):
            self.RaiseApiError()
        return success

    def GetTimestamp(self):
        (success, timestamp) = self._lib.GetTimestamp(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return timestamp
    
    def GetTimestampFreq(self):
        (success, freq) = self._lib.GetTimestampFrequency(self._hCamera)
        if (0 == success):
            self.RaiseApiError()
        return freq
        
    def GetMetaDataTimestamp(self, imageData, imageFormat):
        timeStamp = 0
        (success, timeStamp) = self._lib.GetMetadata(self._hCamera, imageData, imageFormat, METADATA_TIMESTAMP)
        if (0 == success):
            self.RaiseApiError()
        return timeStamp
    
    def GetMetaDataFrameCounter(self, imageData, imageFormat):
        frameCounter = 0
        (success, frameCounter) = self._lib.GetMetadata(self._hCamera, imageData, imageFormat, METADATA_FRAME_COUNTER)
        if (0 == success):
            self.RaiseApiError()
        return frameCounter
