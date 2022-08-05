"""
A wrapper around the Lumenera Lucam API exposed by lucamapi.dll, liblucamapi.so, LuCamSDK.framework

 DynamicLibrary is a class that uses ctypes to wrap the DLL
 Api is the class you want to use. It uses DynamicLibrary, and makes life a little more pythonic.

 For a list of things available, use vars(lucamapi) or dir(lucamapi) on the Python command line

 To get started with the Api:

 import api.py
 api = Api()
 numCamera = api.NumCameras()
 handle = api.CameraOpen(int(numCameras))
 print api.lib.QueryVersion(handle)
 ...
 api.CameraClose(handle)

 The camera.py makes things a bit easier to do.
"""

import ctypes as C 
import os
import platform

__version__ = '1.0.1'

#// XXX_LIB_PATH

# see class DynamicLibrary below if you want to change this

#// LINUX_LIB_PATH is the where the script can expect to find the lucamsdk for linux package.
#// The SDK src, lib, include directories can all be found in the LINUX_LIB_PATH directory.
if platform.system() == 'Linux':
    LINUX_LIB_PATH = os.environ['LUMENERA_SDK']

DARWIN_LIB_PATH = '/Library/Frameworks/LuCamSDK.framework/Versions/Current'

#// API types we typically take from <windows.h>
#// THESE constants were stolen from ctypes.wintypes
#// ctypes.wintypes is broken on Linux at the moment.
HANDLE = C.c_void_p
BOOL = C.c_int
DWORD = C.c_ulong
HWND = HANDLE
HMENU = HANDLE

#//
#// Helper functions
#//
def GetPixelSize(pixelFormat):
    if (PIXEL_FORMAT_8 == pixelFormat):
        return  int(8 / 8)                                              # Changed this! JS
    elif(PIXEL_FORMAT_16 == pixelFormat):
        return int(16 / 8)
    elif(PIXEL_FORMAT_24 == pixelFormat):
        return int(24 / 8)
    elif(PIXEL_FORMAT_32 == pixelFormat):
        return int(32 / 8)
    elif (PIXEL_FORMAT_48 == pixelFormat):
        return int(48 / 8) 
    else:
        errMsg = 'Invalid pixel format ({0})'.format(pixelFormat)
        raise ApiError(ERROR_INVALID_PIXEL_FORMAT, errMsg)

class LUCAM_VERSION(C.Structure):
    _fields_ = [
        ('firmware',        C.c_uint), #// Not available with LucamEnumCameras
        ('fpga',            C.c_uint), #// Not available with LucamEnumCameras
        ('api',             C.c_uint),
        ('driver',          C.c_uint), #// Not available with LucamEnumCameras
        ('serialnumber',    C.c_uint), 
        ('cameraid',        C.c_uint)
    ]
    
    def Firmware(self):
        major = (self.firmware >> 8) & 0xFF
        minor = (self.firmware >> 0) & 0xFF
        return '{0}.{1}'.format(major, minor)
    def Fpga(self):
        major = (self.fpga >> 8) & 0xFF
        minor = (self.fpga >> 0) & 0xFF
        return '{0}.{1}'.format(major, minor)
    def Api(self):
        major = (self.api >> 24) & 0xFF
        minor = (self.api >> 16) & 0xFF
        rev   = (self.api >>  8) & 0xFF
        build = (self.api >>  0) & 0xFF
        return '{0}.{1}.{2}.{3}'.format(major, minor, rev, build)
    def Driver(self):
        major = (self.driver >> 24) & 0xFF
        minor = (self.driver >> 16) & 0xFF
        rev   = (self.driver >>  8) & 0xFF
        build = (self.driver >>  0) & 0xFF
        return '{0}.{1}.{2}.{3}'.format(major, minor, rev, build)
    def SerialNumber(self):
        return self.serialnumber
    def CameraId(self):
        return '0x{0:02X}'.format(self.cameraid)
    def __str__(self):
        return 'LUCAM_VERSION: firmware={0}, fpga={1}, api={2}, driver={3}, serialnumber={4}, cameraid={5}'.format(
            self.Firmware(), self.Fpga(), 
            self.Api(), self.Driver(),
            self.SerialNumber(), self.CameraId())
    def __repr__(self):
        return 'LUCAM_VERSION: firmware=0x{0:08X}, fpga=0x{1:08X}, api=0x{2:08X}, driver=0x{3:08X}, serialnumber={4}, cameraid=0x{5:02X}'.format(
            self.firmware, self.fpga, 
            self.api, self.driver,
            self.serialnumber, self.cameraid)

class LUCAM_IMAGE_FORMAT(C.Structure):
    _fields_ = [
        ('size',          C.c_uint),
        ('width',         C.c_uint),
        ('height',        C.c_uint),
        ('pixelFormat',   C.c_uint),
        ('imageSize',     C.c_uint),
        ('lucamReserved', C.c_uint*8),
    ]

    def GetPixelSize(self):
        return GetPixelSize(self.pixelFormat)
        
    def GetImageDimensions(self):
        """ Returns (imageWidth, imageHeight, numPixels) """
        imageWidth = self.width
        imageHeight = self.height
        return (imageWidth, imageHeight, imageWidth * imageHeight)
        
    def __str__(self):
        return 'LUCAM_IMAGE_FORMAT: size={0}, width={1}, height={2}, pixelFormat={3}, imageSize={4}'.format(
            self.size,
            self.width, 
            self.height,
            self.pixelFormat,
            self.imageSize)

    __repr__ = __str__

class LUCAM_FRAME_FORMAT(C.Structure):
    _fields_ = [
        ('xOffset',     C.c_uint),
        ('yOffset',     C.c_uint),
        ('width',       C.c_uint),
        ('height',      C.c_uint),
        ('pixelFormat', C.c_uint),
        ('subSampleX',  C.c_ushort),
        ('flagsX',      C.c_ushort),
        ('subSampleY',  C.c_ushort),
        ('flagsY',      C.c_ushort),
    ]
    
    def GetPixelSize(self):
        return GetPixelSize(self.pixelFormat)
        
    def GetImageDimensions(self):
        """ Returns (imageWidth, imageHeight, numPixels) """
        imageWidth = int(self.width / self.subSampleX)
        imageHeight = int(self.height / self.subSampleY) #################################################################
        return (imageWidth, imageHeight, imageWidth * imageHeight)
        
    def GetNumberOfPixels(self):
        return self.GetImageDimensions()[2]

    def GetImageSize(self):
        """ Returns the image size, in bytes """
        numPixels = self.GetNumberOfPixels()
        pixelSize = self.GetPixelSize()
        return numPixels * pixelSize
        
    def __str__(self):
        return 'LUCAM_FRAME_FORMAT: top=({0},{1}), {2} x {3}, pixelFormat={4}, subSample=({5},{6}), flagsX={7}, flagsY={8}'.format(
            self.xOffset, self.yOffset,
            self.width, self.height,
            PixelFormats[self.pixelFormat],
            self.subSampleX, self.subSampleY,
            self.flagsX, self.flagsY)

    __repr__ = __str__

class LUCAM_SNAPSHOT(C.Structure):
    _fields_ = [
        ('exposure',        C.c_float),
        ('gain',            C.c_float),
        ('gainRed',         C.c_float),
        ('gainBlue',        C.c_float),
        ('gainGreen1',      C.c_float),
        ('gainGreen2',      C.c_float),
        ('strobe',          C.c_uint),
        ('strobeDelay',     C.c_float),
        ('useHWTrigger',    C.c_int),
        ('timeout',         C.c_float),
        ('format',          LUCAM_FRAME_FORMAT),
        ('shutterType',     C.c_uint),
        ('exposureDelay',   C.c_float),
        ('bufferLastFrame', C.c_uint),
        ('ulReserved1',     C.c_uint),
        ('flReserved1',     C.c_float),
        ('flReserved2',     C.c_float),
    ]
    
    def __str__(self):
        return 'LUCAM_SNAPSHOT: exp={0}, gain={1}, rggb=({2},{3},{4},{5}), useHWTrigger={6}, timeout={7}, format={8}'.format(
            self.exposure, 
            self.gain,
            self.gainRed, self.gainGreen1, self.gainGreen2, self.gainBlue,
            self.useHWTrigger,
            self.timeout,
            self.format)

    __repr__ = __str__

class LUCAM_CONVERSION(C.Structure):
    _fields_ = [
        ('DemosaicMethod',   C.c_ulong),
        ('CorrectionMatrix', C.c_ulong)
    ]

    def __str__(self):
        return 'LUCAM_CONVERSION: DM={0}, CM={1}'.format(self.DemosaicMethod, self.CorrectionMatrix)

    __repr__ = __str__
    
class LUCAM_CONVERSION_PARAMS(C.Structure):
    #// expected size of this is 44
    #// Saturation = 0.0 is greyscale
    #// Saturation = 1.0 is normal color
    #// DigitalGain can also be DigitalGainRed
    #// Set DigitalGain = 1.0 to match the result in ConvertFrameToRgb24
    #// DigitalWB_U can also be DigitalGainGreen
    #// Set DigitalWB_U = 0.0 to match the result in ConvertFrameToRgb24
    #// DigitalWB_V can also be DigitalGainBlue
    #// Set DigitalWB_V = 0.0 to match the result in ConvertFrameToRgb24
    _fields_ = [
        ('Size',                C.c_uint),
        ('DemosaicMethod',      C.c_uint),
        ('CorrectionMatrix',    C.c_uint),
        ('FlipX',               BOOL), 
        ('FlipY',               BOOL),
        ('Hue',                 C.c_float),
        ('Saturation',          C.c_float),
        ('UseColorGainsOverWb', BOOL),
        ('DigitalGain',         C.c_float),
        ('DigitalWB_U',         C.c_float),
        ('DigitalWB_V',         C.c_float)
    ]

    def __str__(self):
        return 'LUCAM_CONVERSION_PARAMS: Size={0}, DM={1}, CM={2}, FlipX={3}, FlipY={4}, Hue={5}, Sat={6}, UseColor={7}, Gain={8}, WB_U={9}, WB_V={10}'.format(
            self.Size, 
            self.DemosaicMethod,
            self.CorrectionMatrix,
            self.FlipX,
            self.FlipY,
            self.Hue,
            self.Saturation,
            self.UseColorGainsOverWb,
            self.DigitalGain,
            self.DigitalWB_U,
            self.DigitalWB_V)

    __repr__ = __str__
    

pBOOL = C.POINTER(BOOL)
pBYTE = C.POINTER(C.c_byte)
pUBYTE = C.POINTER(C.c_ubyte)
pUSHORT = C.POINTER(C.c_ushort)
pFLOAT = C.POINTER(C.c_float)
pLONG = C.POINTER(C.c_long)
pULONG = C.POINTER(C.c_ulong)
pULONGLONG = C.POINTER(C.c_ulonglong)

pHANDLE = C.POINTER(HANDLE)
pLUCAM_VERSION = C.POINTER(LUCAM_VERSION)
pLUCAM_FRAME_FORMAT = C.POINTER(LUCAM_FRAME_FORMAT)
pLUCAM_IMAGE_FORMAT = C.POINTER(LUCAM_IMAGE_FORMAT)
pLUCAM_SNAPSHOT = C.POINTER(LUCAM_SNAPSHOT)
pLUCAM_CONVERSION = C.POINTER(LUCAM_CONVERSION)
pLUCAM_CONVERSION_PARAMS = C.POINTER(LUCAM_CONVERSION_PARAMS)

#//
#// There's a lot of work to do to tell the ctypes class 
#// what the function signatures look like, so we'll
#// break it out into a helper function
#//
#// If you can make use of it for some reason, here you go.
#// 
    
def InitializeLucamLibFunctionSignatures(lib):
    
    #// Camera enumeration and connection
    lib.LucamNumCameras.argtypes = []
    lib.LucamNumCameras.restype = C.c_ulong
    lib.LucamEnumCameras.argtypes = [pLUCAM_VERSION, C.c_ulong]
    lib.LucamEnumCameras.restype  = C.c_ulong
    lib.LucamCameraOpen.argtypes = [C.c_ulong]
    lib.LucamCameraOpen.restype = HANDLE
    lib.LucamCameraClose.argtypes = [HANDLE]
    lib.LucamCameraClose.restype = BOOL
    lib.LucamCameraReset.argtypes = [HANDLE]
    lib.LucamCameraReset.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamSelectExternInterface.argtypes = [C.c_ulong]
        lib.LucamSelectExternInterface.restype = BOOL

    #// Camera Info
    lib.LucamQueryVersion.argtypes = [HANDLE, pLUCAM_VERSION]
    lib.LucamQueryVersion.restype = BOOL
    lib.LucamQueryExternInterface.argtypes = [HANDLE, pULONG]
    lib.LucamQueryExternInterface.restype = BOOL
    lib.LucamGetCameraId.argtypes = [HANDLE, pULONG]
    lib.LucamGetCameraId.restype = BOOL
    lib.LucamGetHardwareRevision.argtypes = [HANDLE, pULONG] 
    lib.LucamGetHardwareRevision.restype = BOOL
    lib.LucamEnumAvailableFrameRates.argtypes = [HANDLE, C.c_ulong, pFLOAT]
    lib.LucamEnumAvailableFrameRates.restype  = C.c_ulong
    lib.LucamGetTruePixelDepth.argtypes = [HANDLE, pULONG]
    lib.LucamGetTruePixelDepth.restype = BOOL

    #// Properties
    lib.LucamGetProperty.argtypes = [HANDLE, C.c_ulong, pFLOAT, pULONG]
    lib.LucamGetProperty.restype  = BOOL
    lib.LucamSetProperty.argtypes = [HANDLE, C.c_ulong, C.c_float, C.c_ulong]
    lib.LucamSetProperty.restype  = BOOL
    lib.LucamPropertyRange.argtypes = [HANDLE, C.c_ulong, pFLOAT, pFLOAT, pFLOAT, pULONG]
    lib.LucamPropertyRange.restype = BOOL

    #// Image Format
    lib.LucamSetFormat.argtypes = [HANDLE, pLUCAM_FRAME_FORMAT, C.c_float]
    lib.LucamSetFormat.restype  = BOOL
    lib.LucamGetFormat.argtypes = [HANDLE, pLUCAM_FRAME_FORMAT, pFLOAT]
    lib.LucamGetFormat.restype  = BOOL
    lib.LucamGetVideoImageFormat.argtypes = [HANDLE, pLUCAM_IMAGE_FORMAT] 
    lib.LucamGetStillImageFormat.argtypes = [HANDLE, pLUCAM_IMAGE_FORMAT] 
    lib.LucamGetStillImageFormat.restype = BOOL
        
    #// Video Control
    lib.LucamStreamVideoControl.argtypes = [HANDLE, C.c_ulong, HWND]
    lib.LucamStreamVideoControl.restype = BOOL
            
    #// Video Images
    lib.LucamTakeVideo.argtypes = [HANDLE, C.c_long, pUBYTE]
    lib.LucamTakeVideo.restype  = BOOL
    lib.LucamTakeVideoEx.argtypes = [HANDLE, pUBYTE, pULONG, C.c_ulong]
    lib.LucamTakeVideoEx.restype  = BOOL
    if platform.system() == 'Windows':
        lib.LucamCancelTakeVideo.argtypes = [HANDLE]
        lib.LucamCancelTakeVideo.restype = BOOL

    #// Still Images
    lib.LucamTakeSnapshot.argtypes = [HANDLE, pLUCAM_SNAPSHOT, pUBYTE]
    lib.LucamTakeSnapshot.restype = C.c_int
    lib.LucamEnableFastFrames.argtypes = [HANDLE, pLUCAM_SNAPSHOT]
    lib.LucamEnableFastFrames.restype = BOOL
    lib.LucamTakeFastFrame.argtypes = [HANDLE, pUBYTE]
    lib.LucamTakeFastFrame.restype = BOOL
    lib.LucamTakeFastFrameNoTrigger.argtypes = [HANDLE, pUBYTE]
    lib.LucamTakeFastFrameNoTrigger.restype = BOOL
    lib.LucamForceTakeFastFrame.argtypes = [HANDLE, pUBYTE]
    lib.LucamForceTakeFastFrame.restype = BOOL
    lib.LucamTriggerFastFrame.argtypes = [HANDLE]
    lib.LucamTriggerFastFrame.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamCancelTakeFastFrame.argtypes = [HANDLE]
        lib.LucamCancelTakeFastFrame.restype = BOOL
    lib.LucamDisableFastFrames.argtypes = [HANDLE]
    lib.LucamDisableFastFrames.restype = BOOL
    lib.LucamSetTriggerMode.argtypes = [HANDLE, BOOL]
    lib.LucamSetTriggerMode.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamEnableSynchronousSnapshots.argtypes = [C.c_ulong, pHANDLE, C.POINTER(pLUCAM_SNAPSHOT)]
        lib.LucamEnableSynchronousSnapshots.restype = BOOL
        lib.LucamTakeSynchronousSnapshots.argtypes = [HANDLE, C.POINTER(pUBYTE)]
        lib.LucamTakeSynchronousSnapshots.restype = BOOL
        lib.LucamDisableSynchronousSnapshots.argtypes = [HANDLE]
        lib.LucamDisableSynchronousSnapshots.restype = BOOL
        

    #// Image Analysis
    if platform.system() == 'Windows':
        lib.LucamGetImageIntensity.argtypes = [HANDLE, C.POINTER(C.c_void_p), C.POINTER(C.c_void_p),
                                               C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong,
                                               pFLOAT, pFLOAT, pFLOAT, pFLOAT, pFLOAT]
        lib.LucamGetImageIntensity.restype = BOOL

    #// Raw Image Conversion
    lib.LucamConvertFrameToRgb24.argtypes = [HANDLE, pUBYTE, pUBYTE,
                                             C.c_ulong, C.c_ulong, C.c_ulong, pLUCAM_CONVERSION]
    lib.LucamConvertFrameToRgb24.restype = BOOL
    lib.LucamConvertFrameToRgb32.argtypes = [HANDLE, pUBYTE, pUBYTE,
                                             C.c_ulong, C.c_ulong, C.c_ulong, pLUCAM_CONVERSION]
    lib.LucamConvertFrameToRgb32.restype = BOOL
    lib.LucamConvertFrameToRgb48.argtypes = [HANDLE, pUSHORT, pUSHORT,
                                             C.c_ulong, C.c_ulong, C.c_ulong, pLUCAM_CONVERSION]
    lib.LucamConvertFrameToRgb48.restype = BOOL
    lib.LucamConvertFrameToRgb24Ex.argtypes = [HANDLE, pUBYTE, pUBYTE,
                                               pLUCAM_IMAGE_FORMAT, pLUCAM_CONVERSION_PARAMS]
    lib.LucamConvertFrameToRgb24Ex.restype = BOOL
    lib.LucamConvertFrameToRgb32Ex.argtypes = [HANDLE, pUBYTE, pUBYTE,
                                               pLUCAM_IMAGE_FORMAT, pLUCAM_CONVERSION_PARAMS]
    lib.LucamConvertFrameToRgb32Ex.restype = BOOL
    lib.LucamConvertFrameToRgb48Ex.argtypes = [HANDLE, pUSHORT, pUSHORT,
                                               pLUCAM_IMAGE_FORMAT, pLUCAM_CONVERSION_PARAMS]
    lib.LucamConvertFrameToRgb48Ex.restype = BOOL
    if platform.system() != 'Darwin':
        lib.LucamConvertFrameToGreyscale8Ex.argtypes = [HANDLE, pUBYTE, pUBYTE,
                                                        pLUCAM_IMAGE_FORMAT, pLUCAM_CONVERSION_PARAMS]
        lib.LucamConvertFrameToGreyscale8Ex.restype = BOOL
        lib.LucamConvertFrameToGreyscale16Ex.argtypes = [HANDLE, pUSHORT, pUSHORT,
                                                         pLUCAM_IMAGE_FORMAT, pLUCAM_CONVERSION_PARAMS]
        lib.LucamConvertFrameToGreyscale16Ex.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamConvertFrameToGreyscale8.argtypes = [HANDLE, pUBYTE, pUBYTE,
                                                      C.c_ulong, C.c_ulong, C.c_ulong, pLUCAM_CONVERSION]
        lib.LucamConvertFrameToGreyscale8.restype = BOOL
        lib.LucamConvertFrameToGreyscale16.argtypes = [HANDLE, pUSHORT, pUSHORT,
                                                       C.c_ulong, C.c_ulong, C.c_ulong, pLUCAM_CONVERSION]
        lib.LucamConvertFrameToGreyscale16.restype = BOOL
    #//LUCAM_API VOID LUCAM_EXPORT LucamConvertBmp24ToRgb24(UCHAR *pFrame, ULONG width, ULONG height) ;

    #// Save Image
    lib.LucamSaveImageEx.argtypes = [HANDLE, C.c_ulong, C.c_ulong, C.c_ulong, pUBYTE, C.c_char_p]
    lib.LucamSaveImageEx.restype = BOOL
    if platform.system() != 'Darwin':
        lib.LucamSaveImage.argtypes = [C.c_ulong, C.c_ulong, C.c_ulong, pUBYTE, C.c_char_p]
        lib.LucamSaveImage.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamSaveImageW.argtypes = [C.c_ulong, C.c_ulong, C.c_ulong, pUBYTE, C.c_wchar_p]
        lib.LucamSaveImageW.restype = BOOL
        lib.LucamSaveImageWEx.argtypes = [HANDLE, C.c_ulong, C.c_ulong, C.c_ulong, pUBYTE, C.c_wchar_p]
        lib.LucamSaveImageWEx.restype = BOOL

    #// Error Info
    lib.LucamGetLastError.argtypes = []
    lib.LucamGetLastError.restype = C.c_ulong
    lib.LucamGetLastErrorForCamera.argtypes = [HANDLE]
    lib.LucamGetLastErrorForCamera.restype = C.c_ulong

    #// Event Notification
    if platform.system() == 'Windows':
        lib.LucamRegisterEventNotification.argtypes = [HANDLE, C.c_ulong, C.c_int]
        lib.LucamRegisterEventNotification.restype = C.c_void_p
        lib.LucamUnregisterEventNotification.argtypes = [HANDLE, C.c_void_p]
        lib.LucamUnregisterEventNotification.restype = BOOL

    #// Callbacks
    if platform.system() == 'Windows':
        lib.LucamAddStreamingCallback.argtypes = [HANDLE, C.WINFUNCTYPE(None, C.c_void_p, pUBYTE, C.c_ulong), C.py_object]
    else:
        lib.LucamAddStreamingCallback.argtypes = [HANDLE, C.CFUNCTYPE(None, C.c_void_p, pUBYTE, C.c_ulong), C.py_object]
    lib.LucamAddStreamingCallback.restype = C.c_long
    lib.LucamRemoveStreamingCallback.argtypes = [HANDLE, C.c_long]
    lib.LucamRemoveStreamingCallback.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamAddSnapshotCallback.argtypes = [HANDLE, C.WINFUNCTYPE(None, C.c_void_p, pUBYTE, C.c_ulong), C.py_object]
    else:
        lib.LucamAddSnapshotCallback.argtypes = [HANDLE, C.CFUNCTYPE(None, C.c_void_p, pUBYTE, C.c_ulong), C.py_object]
    lib.LucamAddSnapshotCallback.restype = C.c_long
    lib.LucamRemoveSnapshotCallback.argtypes = [HANDLE, C.c_long]
    lib.LucamRemoveSnapshotCallback.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamAddRgbPreviewCallback.argtypes = [HANDLE, C.WINFUNCTYPE(None, C.c_void_p, pUBYTE, C.c_ulong, C.c_ulong), C.py_object, C.c_ulong]
    else:
        lib.LucamAddRgbPreviewCallback.argtypes = [HANDLE, C.CFUNCTYPE(None, C.c_void_p, pUBYTE, C.c_ulong, C.c_ulong), C.py_object, C.c_ulong]
    lib.LucamAddRgbPreviewCallback.restype = C.c_long
            

    #// DirectShow Features
    if platform.system() == 'Windows':
        lib.LucamDisplayPropertyPage.argtypes = [HANDLE, HWND]
        lib.LucamDisplayPropertyPage.restype = BOOL
        lib.LucamDisplayVideoFormatPage.argtypes = [HANDLE, HWND]
        lib.LucamDisplayVideoFormatPage.restype = BOOL
        lib.LucamCreateDisplayWindow.argtypes  = [HANDLE, C.c_char_p, DWORD, C.c_int, C.c_int, C.c_int, C.c_int, HWND, HMENU]
        lib.LucamCreateDisplayWindow.restype   = BOOL
        lib.LucamDestroyDisplayWindow.argtypes = [HANDLE]
        lib.LucamDestroyDisplayWindow.restype  = BOOL
        lib.LucamAdjustDisplayWindow.argtypes  = [HANDLE, C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_int]
        lib.LucamAdjustDisplayWindow.restype   = BOOL
        
    #// GPIO Control
    lib.LucamGpioRead.argtypes = [HANDLE, C.POINTER(C.c_uint8), C.POINTER(C.c_uint8)]
    lib.LucamGpioRead.restype = BOOL
    lib.LucamGpioWrite.argtypes = [HANDLE, C.c_uint8]
    lib.LucamGpioWrite.restype = BOOL
    lib.LucamGpoSelect.argtypes = [HANDLE, C.c_uint8]
    lib.LucamGpoSelect.restype = BOOL
    lib.LucamGpioConfigure.argtypes = [HANDLE, C.c_uint8]
    lib.LucamGpioConfigure.restype = BOOL
        
    #// Register Access
    if platform.system() == 'Windows':
        lib.LucamReadRegister.argtypes = [HANDLE, C.c_ulong, C.c_ulong, pULONG]
        lib.LucamReadRegister.restype = BOOL
        lib.LucamWriteRegister.argtypes = [HANDLE, C.c_ulong, C.c_ulong, pULONG]
        lib.LucamWriteRegister.restype = BOOL
        
    #// Perm Buffer Access
    lib.LucamPermanentBufferRead.argtypes = [HANDLE, pUBYTE, C.c_ulong, C.c_ulong]
    lib.LucamPermanentBufferRead.restype = BOOL
    lib.LucamPermanentBufferWrite.argtypes = [HANDLE, pUBYTE, C.c_ulong, C.c_ulong]
    lib.LucamPermanentBufferWrite.restype = BOOL

    #// Color Correction Matrices
    if platform.system() == 'Windows':
        lib.LucamSetupCustomMatrix.argtypes = [HANDLE, pFLOAT]
        lib.LucamSetupCustomMatrix.restype = BOOL
        lib.LucamGetCurrentMatrix.argtypes = [HANDLE, pFLOAT]
        lib.LucamGetCurrentMatrix.restype = BOOL

    #// One Shot Auto Features
    lib.LucamOneShotAutoExposure.argtypes = [HANDLE, C.c_uint, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
    lib.LucamOneShotAutoExposure.restype = BOOL
    lib.LucamOneShotAutoGain.argtypes = [HANDLE, C.c_uint, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
    lib.LucamOneShotAutoGain.restype = BOOL
    lib.LucamOneShotAutoWhiteBalance.argtypes = [HANDLE, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
    lib.LucamOneShotAutoWhiteBalance.restype = BOOL
    lib.LucamDigitalWhiteBalance.argtypes = [HANDLE, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
    lib.LucamDigitalWhiteBalance.restype = BOOL
    if platform.system() != 'Linux':
        lib.LucamOneShotAutoExposureEx.argtypes = [HANDLE, C.c_uint, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong, C.c_float]
        lib.LucamOneShotAutoExposureEx.restype = BOOL
        lib.LucamOneShotAutoWhiteBalanceEx.argtypes = [HANDLE, C.c_float, C.c_float, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
        lib.LucamOneShotAutoWhiteBalanceEx.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamDigitalWhiteBalanceEx.argtypes = [HANDLE, C.c_float, C.c_float, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
        lib.LucamDigitalWhiteBalanceEx.restype = BOOL
        lib.LucamAdjustWhiteBalanceFromSnapshot.argtypes = [HANDLE, pLUCAM_SNAPSHOT, pUBYTE, C.c_float, C.c_float, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
        lib.LucamAdjustWhiteBalanceFromSnapshot.restype = BOOL
        lib.LucamOneShotAutoIris.argtypes = [HANDLE, C.c_uint, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong]
        lib.LucamOneShotAutoIris.restype = BOOL
        lib.LucamContinuousAutoExposureEnable.argtypes = [HANDLE, C.c_uint, C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong, C.c_float]
        lib.LucamContinuousAutoExposureEnable.restype = BOOL
        lib.LucamContinuousAutoExposureDisable.argtypes = [HANDLE]
        lib.LucamContinuousAutoExposureDisable.restype = BOOL

    #// Electronic Lens Control (Autolens)
    if platform.system() == 'Windows' or (platform.system() == 'Linux' and lib.API_VERSION >= (2,2,0,0)):
        lib.LucamInitAutoLens.argtypes = [HANDLE, BOOL]
        lib.LucamInitAutoLens.restype = BOOL
        lib.LucamAutoFocusStart.argtypes = [HANDLE, 
                                            C.c_ulong, C.c_ulong, C.c_ulong, C.c_ulong, 
                                            C.c_float, C.c_float, C.c_float,
                                            C.c_void_p,#C.c_void_p,C.WINFUNCTYPE(BOOL, C.c_void_p, C.c_float)
                                            C.c_void_p]#C.py_object]
        lib.LucamAutoFocusStart.restype = BOOL
        lib.LucamAutoFocusWait.argtypes = [HANDLE, C.c_ulong]
        lib.LucamAutoFocusWait.restype = BOOL
        lib.LucamAutoFocusStop.argtypes = [HANDLE]
        lib.LucamAutoFocusStop.restype = BOOL
        lib.LucamAutoFocusQueryProgress.argtypes = [HANDLE, pFLOAT]
        lib.LucamAutoFocusQueryProgress.restype = BOOL

    #// Tap Correction
    if platform.system() != 'Darwin':
        lib.LucamPerformDualTapCorrection.argtypes = [HANDLE, pUBYTE, pLUCAM_IMAGE_FORMAT]
        lib.LucamPerformDualTapCorrection.restype = BOOL
    if platform.system() == 'Windows':
        lib.LucamPerformMonoGridCorrection.argtypes = [HANDLE, pUBYTE, pLUCAM_IMAGE_FORMAT]
        lib.LucamPerformMonoGridCorrection.restype = BOOL
        lib.LucamPerformMultiTapCorrection.argtypes = [HANDLE, pUBYTE, pLUCAM_IMAGE_FORMAT]
        lib.LucamPerformMultiTapCorrection.restype = BOOL
    else: 
        lib.LucamPerformMultiTapCorrection.argtypes = [HANDLE, pUBYTE, pLUCAM_IMAGE_FORMAT]
        lib.LucamPerformMultiTapCorrection.restype = BOOL

    #// Other
    if platform.system() == 'Windows':
        lib.LucamSetup8bitsLUT.argtypes = [HANDLE, pUBYTE, C.c_ulong]
        lib.LucamSetup8bitsLUT.restype = BOOL
        lib.LucamSetup8bitsColorLUT.argtypes = [HANDLE, pUBYTE, C.c_ulong, BOOL, BOOL, BOOL, BOOL]
        lib.LucamSetup8bitsColorLUT.restype = BOOL
        lib.LucamSetTimeout.argtypes = [HANDLE, BOOL, C.c_float]
        lib.LucamSetTimeout.restype = BOOL
        lib.LucamAutoRoiGet.argtypes = [HANDLE, pLONG, pLONG, pLONG, pLONG]
        lib.LucamAutoRoiGet.restype = BOOL
        lib.LucamAutoRoiSet.argtypes = [HANDLE, C.c_long, C.c_long, C.c_long, C.c_long] 
        lib.LucamAutoRoiSet.restype = BOOL
        lib.LucamDataLsbAlign.argtypes = [HANDLE, pLUCAM_IMAGE_FORMAT, pUBYTE]
        lib.LucamDataLsbAlign.restype = BOOL
        lib.LucamEnableInterfacePowerSpecViolation.argtypes = [HANDLE, BOOL]
        lib.LucamEnableInterfacePowerSpecViolation.restype = BOOL
        lib.LucamIsInterfacePowerSpecViolationEnabled.argtypes = [HANDLE, pBOOL]
        lib.LucamIsInterfacePowerSpecViolationEnabled.restype = BOOL

    # //Timestamps
    if (platform.system() == 'Windows' and lib.API_VERSION >= (2,1,1,42)) or (platform.system() == 'Linux' and lib.API_VERSION >= (2,2,0,0)):
        lib.LucamGetTimestampFrequency.argtypes = [HANDLE, pULONGLONG]
        lib.LucamGetTimestampFrequency.restype = BOOL
        lib.LucamGetTimestamp.argtypes = [HANDLE, pULONGLONG]
        lib.LucamGetTimestamp.restype = BOOL
        lib.LucamSetTimestamp.argtypes = [HANDLE, C.c_ulonglong]
        lib.LucamSetTimestamp.restype = BOOL
        lib.LucamEnableTimestamp.argtypes = [HANDLE, BOOL]
        lib.LucamEnableTimestamp.restype = BOOL
        lib.LucamIsTimestampEnabled.argtypes = [HANDLE, pBOOL]
        lib.LucamIsTimestampEnabled.restype = BOOL
        lib.LucamGetMetadata.argtypes = [HANDLE, pBYTE, pLUCAM_IMAGE_FORMAT, C.c_ulong, pULONGLONG]
        lib.LucamGetMetadata.restype = BOOL

#// Events
DEVICE_SURPRISE_REMOVAL = 32

#// Camera Interfaces       
INTERFACE_USB1  = 1
INTERFACE_USB2  = 2
INTERFACE_USB3  = 3
INTERFACE_GIGE  = 4

CameraInterfaces = { 
    INTERFACE_USB1: 'USB1',
    INTERFACE_USB2: 'USB2',
    INTERFACE_USB3: 'USB3',
    INTERFACE_GIGE: 'GigE'
}

#// Pixel Formats
PIXEL_FORMAT_8      = 0
PIXEL_FORMAT_16     = 1
PIXEL_FORMAT_24     = 2
PIXEL_FORMAT_YUV422 = 3
PIXEL_FORMAT_COUNT  = 4
PIXEL_FORMAT_FILTER = 5
PIXEL_FORMAT_32     = 6
PIXEL_FORMAT_48     = 7

PixelFormats = {
    PIXEL_FORMAT_8:      'PIXEL_FORMAT_8',
    PIXEL_FORMAT_16:     'PIXEL_FORMAT_16',
    PIXEL_FORMAT_24:     'PIXEL_FORMAT_24',
    PIXEL_FORMAT_32:     'PIXEL_FORMAT_32',
    PIXEL_FORMAT_48:     'PIXEL_FORMAT_48',
    PIXEL_FORMAT_YUV422: 'PIXEL_FORMAT_YUV422',
    PIXEL_FORMAT_COUNT:  'PIXEL_FORMAT_COUNT',
    PIXEL_FORMAT_FILTER: 'PIXEL_FORMAT_FILTER'
}

#// Shutter types
SHUTTER_GLOBAL         = 0
SHUTTER_ROLLING        = 1

#//     
#// Parameters for StreamVideoControl
#//
STOP_STREAMING  = 0
START_STREAMING = 1
START_DISPLAY   = 2
PAUSE_STREAM    = 3
START_RGBSTREAM = 6

#//
#// Property IDs
#//
PROPERTY_BRIGHTNESS                =  0
PROPERTY_CONTRAST                  =  1
PROPERTY_HUE                       =  2
PROPERTY_SATURATION                =  3
PROPERTY_SHARPNESS                 =  4
PROPERTY_GAMMA                     =  5

PROPERTY_PAN                       = 16
PROPERTY_TILT                      = 17
PROPERTY_ROLL                      = 18
PROPERTY_ZOOM                      = 19
PROPERTY_EXPOSURE                  = 20
PROPERTY_IRIS                      = 21
PROPERTY_FOCUS                     = 22

PROPERTY_GAIN                      = 40
PROPERTY_GAIN_RED                  = 41
PROPERTY_GAIN_BLUE                 = 42
PROPERTY_GAIN_GREEN1               = 43
PROPERTY_GAIN_GREEN2               = 44
PROPERTY_GAIN_MAGENTA              = 41
PROPERTY_GAIN_CYAN                 = 42
PROPERTY_GAIN_YELLOW1              = 43
PROPERTY_GAIN_YELLOW2              = 44

PROPERTY_STILL_EXPOSURE            = 50
PROPERTY_STILL_GAIN                = 51
PROPERTY_STILL_GAIN_RED            = 52
PROPERTY_STILL_GAIN_GREEN1         = 53
PROPERTY_STILL_GAIN_GREEN2         = 54
PROPERTY_STILL_GAIN_BLUE           = 55
PROPERTY_STILL_GAIN_MAGENTA        = 52
PROPERTY_STILL_GAIN_YELLOW1        = 53
PROPERTY_STILL_GAIN_YELLOW2        = 54
PROPERTY_STILL_GAIN_CYAN           = 55
PROPERTY_STILL_STROBE_DELAY        = 56

PROPERTY_DEMOSAICING_METHOD        = 64
PROPERTY_CORRECTION_MATRIX         = 65
PROPERTY_FLIPPING                  = 66

PROPERTY_DIGITAL_SATURATION        = 67 #// macOS
PROPERTY_DIGITAL_HUE               = 68 #// macOS

PROPERTY_DIGITAL_WHITEBALANCE_U    = 69 #// from -100 to 100
PROPERTY_DIGITAL_WHITEBALANCE_V    = 70 #// from -100 to 100
PROPERTY_DIGITAL_GAIN              = 71 #// from 0 to 2, 1 means a gain of 1.0
PROPERTY_DIGITAL_GAIN_RED          = 72 #// from 0 to 2.5, 1 means a gain of 1.0. Relates to GAIN_Y and WHITEBALANCE
PROPERTY_DIGITAL_GAIN_GREEN        = 73 #// from 0 to 2.5, 1 means a gain of 1.0. Relates to GAIN_Y and WHITEBALANCE
PROPERTY_DIGITAL_GAIN_BLUE         = 74 #// from 0 to 2.5, 1 means a gain of 1.0. Relates to GAIN_Y and WHITEBALANCE=

PROPERTY_COLOR_FORMAT              = 80 #// (read only)
PROPERTY_MAX_WIDTH                 = 81 #// (read only)
PROPERTY_MAX_HEIGHT                = 82 #// (read only)
PROPERTY_UNIT_WIDTH                = 83 #// (read only)
PROPERTY_UNIT_HEIGHT               = 84 #// (read only)

PROPERTY_ABS_FOCUS                 = 85 #// requires the auto lens to be initialized
PROPERTY_BLACK_LEVEL               = 86

PROPERTY_KNEE1_EXPOSURE            = 96
PROPERTY_STILL_KNEE1_EXPOSURE      = 96
PROPERTY_KNEE2_EXPOSURE            = 97
PROPERTY_STILL_KNEE2_EXPOSURE      = 97
PROPERTY_STILL_KNEE3_EXPOSURE      = 98
PROPERTY_VIDEO_KNEE                = 99
PROPERTY_KNEE1_LEVEL               = 99
PROPERTY_STILL_EXPOSURE_DELAY      = 100
PROPERTY_THRESHOLD                 = 101
PROPERTY_AUTO_EXP_TARGET           = 103
PROPERTY_TIMESTAMPS                = 105
PROPERTY_SNAPSHOT_CLOCK_SPEED      = 106 #// 0 is the fastest
PROPERTY_AUTO_EXP_MAXIMUM          = 107
PROPERTY_TEMPERATURE               = 108
PROPERTY_TRIGGER                   = 110
PROPERTY_TRIGGER_PIN               = 110 #// same as PROPERTY_TRIGGER
PROPERTY_FRAME_GATE                = 112
PROPERTY_EXPOSURE_INTERVAL         = 113
PROPERTY_PWM                       = 114
PROPERTY_MEMORY                    = 115 #// value is RO and represent # of frames in memory
PROPERTY_STILL_STROBE_DURATION     = 116
PROPERTY_FAN                       = 118
PROPERTY_SYNC_MODE                 = 119
PROPERTY_SNAPSHOT_COUNT            = 120
PROPERTY_LSC_X                     = 121
PROPERTY_LSC_Y                     = 122
PROPERTY_AUTO_IRIS_MAX             = 123
PROPERTY_LENS_STABILIZATION        = 124
PROPERTY_VIDEO_TRIGGER             = 125
PROPERTY_VIDEO_CLOCK_SPEED         = 126 #// 0 is the fastest, check for readonly flag.
PROPERTY_KNEE2_LEVEL               = 163
PROPERTY_THRESHOLD_LOW             = 165
PROPERTY_THRESHOLD_HIGH            = 166
PROPERTY_TEMPERATURE2              = 167
PROPERTY_LIGHT_FREQUENCY           = 168
PROPERTY_LUMINANCE                 = 169
PROPERTY_AUTO_GAIN_MAXIMUM         = 170
PROPERTY_STROBE_PIN                = 172
PROPERTY_TRIGGER_MODE              = 173
PROPERTY_FOCAL_LENGTH              = 174
PROPERTY_IRIS_LATENCY              = 175
PROPERTY_TAP_CONFIGURATION         = 176
PROPERTY_STILL_TAP_CONFIGURATION   = 177
PROPERTY_MAX_FRAME_RATE            = 184
PROPERTY_AUTO_GAIN_MINIMUM         = 186
PROPERTY_TIMESTAMP_HW_RESET        = 187
PROPERTY_IRIS_STEPS_COUNT          = 188
PROPERTY_JPEG_QUALITY              = 256
PROPERTY_HOST_AUTO_WB_ALGORITHM    = 258
PROPERTY_HOST_AUTO_EX_ALGORITHM    = 259


#// GEV specific properties
PROPERTY_GEV_IPCONFIG_LLA                        = 512 #/* use PROPERTY_FLAG_USE flag */
PROPERTY_GEV_IPCONFIG_DHCP                       = 513 #/* use PROPERTY_FLAG_USE flag */
PROPERTY_GEV_IPCONFIG_PERSISTENT                 = 514 #/* use PROPERTY_FLAG_USE flag */
PROPERTY_GEV_IPCONFIG_PERSISTENT_IPADDRESS       = 515 #/* use a non-cast */
PROPERTY_GEV_IPCONFIG_PERSISTENT_SUBNETMASK      = 516 #/* use a non-cast */
PROPERTY_GEV_IPCONFIG_PERSISTENT_DEFAULTGATEWAY  = 517 #/* use a non-cast */
PROPERTY_GEV_SCPD                                = 518 #


PropertyNames = {
    PROPERTY_BRIGHTNESS: 'PROPERTY_BRIGHTNESS',
    PROPERTY_CONTRAST: 'PROPERTY_CONTRAST',
    PROPERTY_HUE: 'PROPERTY_HUE',
    PROPERTY_SATURATION: 'PROPERTY_SATURATION',
    PROPERTY_SHARPNESS: 'PROPERTY_SHARPNESS',
    PROPERTY_GAMMA: 'PROPERTY_GAMMA',
    PROPERTY_PAN: 'PROPERTY_PAN',
    PROPERTY_TILT: 'PROPERTY_TILT',
    PROPERTY_ROLL: 'PROPERTY_ROLL',
    PROPERTY_ZOOM: 'PROPERTY_ZOOM',
    PROPERTY_EXPOSURE: 'PROPERTY_EXPOSURE',
    PROPERTY_IRIS: 'PROPERTY_IRIS',
    PROPERTY_FOCUS: 'PROPERTY_FOCUS',
    PROPERTY_GAIN: 'PROPERTY_GAIN',
    PROPERTY_GAIN_RED: 'PROPERTY_GAIN_RED',
    PROPERTY_GAIN_BLUE: 'PROPERTY_GAIN_BLUE',
    PROPERTY_GAIN_GREEN1: 'PROPERTY_GAIN_GREEN1',
    PROPERTY_GAIN_GREEN2: 'PROPERTY_GAIN_GREEN2',
    #// Aliases don't work in a map
#   PROPERTY_GAIN_MAGENTA: 'PROPERTY_GAIN_MAGENTA',
#   PROPERTY_GAIN_CYAN: 'PROPERTY_GAIN_CYAN',
#   PROPERTY_GAIN_YELLOW1: 'PROPERTY_GAIN_YELLOW1',
#   PROPERTY_GAIN_YELLOW2: 'PROPERTY_GAIN_YELLOW2',
    PROPERTY_STILL_EXPOSURE: 'PROPERTY_STILL_EXPOSURE',
    PROPERTY_STILL_GAIN: 'PROPERTY_STILL_GAIN',
    PROPERTY_STILL_GAIN_RED: 'PROPERTY_STILL_GAIN_RED',
    PROPERTY_STILL_GAIN_GREEN1: 'PROPERTY_STILL_GAIN_GREEN1',
    PROPERTY_STILL_GAIN_GREEN2: 'PROPERTY_STILL_GAIN_GREEN2',
    PROPERTY_STILL_GAIN_BLUE: 'PROPERTY_STILL_GAIN_BLUE',
    #// Aliases don't work in a map
#   PROPERTY_STILL_GAIN_MAGENTA
#   PROPERTY_STILL_GAIN_YELLOW1
#   PROPERTY_STILL_GAIN_YELLOW2
#   PROPERTY_STILL_GAIN_CYAN
    PROPERTY_STILL_STROBE_DELAY: 'PROPERTY_STILL_STROBE_DELAY',
    PROPERTY_DEMOSAICING_METHOD: 'PROPERTY_DEMOSAICING_METHOD',
    PROPERTY_CORRECTION_MATRIX: 'PROPERTY_CORRECTION_MATRIX',
    PROPERTY_FLIPPING: 'PROPERTY_FLIPPING',
    PROPERTY_DIGITAL_SATURATION: 'PROPERTY_DIGITAL_SATURATION',
    PROPERTY_DIGITAL_HUE: 'PROPERTY_DIGITAL_HUE',
    PROPERTY_DIGITAL_WHITEBALANCE_U: 'PROPERTY_DIGITAL_WHITEBALANCE_U',
    PROPERTY_DIGITAL_WHITEBALANCE_V: 'PROPERTY_DIGITAL_WHITEBALANCE_V',
    PROPERTY_DIGITAL_GAIN: 'PROPERTY_DIGITAL_GAIN',
    PROPERTY_DIGITAL_GAIN_RED: 'PROPERTY_DIGITAL_GAIN_RED',
    PROPERTY_DIGITAL_GAIN_GREEN: 'PROPERTY_DIGITAL_GAIN_GREEN',
    PROPERTY_DIGITAL_GAIN_BLUE: 'PROPERTY_DIGITAL_GAIN_BLUE',
    PROPERTY_COLOR_FORMAT: 'PROPERTY_COLOR_FORMAT',
    PROPERTY_MAX_WIDTH: 'PROPERTY_MAX_WIDTH',
    PROPERTY_MAX_HEIGHT: 'PROPERTY_MAX_HEIGHT',
    PROPERTY_UNIT_WIDTH: 'PROPERTY_UNIT_WIDTH',
    PROPERTY_UNIT_HEIGHT: 'PROPERTY_UNIT_HEIGHT',
    PROPERTY_ABS_FOCUS: 'PROPERTY_ABS_FOCUS',
    PROPERTY_BLACK_LEVEL: 'PROPERTY_BLACK_LEVEL',
    PROPERTY_KNEE1_EXPOSURE: 'PROPERTY_KNEE1_EXPOSURE',
    PROPERTY_STILL_KNEE1_EXPOSURE: 'PROPERTY_STILL_KNEE1_EXPOSURE',
    PROPERTY_KNEE2_EXPOSURE: 'PROPERTY_KNEE2_EXPOSURE',
    PROPERTY_STILL_KNEE2_EXPOSURE: 'PROPERTY_STILL_KNEE2_EXPOSURE',
    PROPERTY_STILL_KNEE3_EXPOSURE: 'PROPERTY_STILL_KNEE3_EXPOSURE',
    PROPERTY_VIDEO_KNEE: 'PROPERTY_VIDEO_KNEE',
    PROPERTY_KNEE1_LEVEL: 'PROPERTY_KNEE1_LEVEL',
    PROPERTY_STILL_EXPOSURE_DELAY: 'PROPERTY_STILL_EXPOSURE_DELAY',
    PROPERTY_THRESHOLD: 'PROPERTY_THRESHOLD',
    PROPERTY_AUTO_EXP_TARGET: 'PROPERTY_AUTO_EXP_TARGET',
    PROPERTY_TIMESTAMPS: 'PROPERTY_TIMESTAMPS',
    PROPERTY_SNAPSHOT_CLOCK_SPEED: 'PROPERTY_SNAPSHOT_CLOCK_SPEED',
    PROPERTY_AUTO_EXP_MAXIMUM: 'PROPERTY_AUTO_EXP_MAXIMUM',
    PROPERTY_TEMPERATURE: 'PROPERTY_TEMPERATURE',
    PROPERTY_TRIGGER: 'PROPERTY_TRIGGER',
    PROPERTY_TRIGGER_PIN: 'PROPERTY_TRIGGER_PIN',
    PROPERTY_FRAME_GATE: 'PROPERTY_FRAME_GATE',
    PROPERTY_EXPOSURE_INTERVAL: 'PROPERTY_EXPOSURE_INTERVAL',
    PROPERTY_PWM: 'PROPERTY_PWM',
    PROPERTY_MEMORY: 'PROPERTY_MEMORY',
    PROPERTY_STILL_STROBE_DURATION: 'PROPERTY_STILL_STROBE_DURATION',
    PROPERTY_FAN: 'PROPERTY_FAN',
    PROPERTY_SYNC_MODE: 'PROPERTY_SYNC_MODE',
    PROPERTY_SNAPSHOT_COUNT: 'PROPERTY_SNAPSHOT_COUNT',
    PROPERTY_LSC_X: 'PROPERTY_LSC_X',
    PROPERTY_LSC_Y: 'PROPERTY_LSC_Y',
    PROPERTY_AUTO_IRIS_MAX: 'PROPERTY_AUTO_IRIS_MAX',
    PROPERTY_LENS_STABILIZATION: 'PROPERTY_LENS_STABILIZATION',
    PROPERTY_VIDEO_TRIGGER: 'PROPERTY_VIDEO_TRIGGER',
    PROPERTY_VIDEO_CLOCK_SPEED: 'PROPERTY_VIDEO_CLOCK_SPEED',
    PROPERTY_KNEE2_LEVEL: 'PROPERTY_KNEE2_LEVEL',
    PROPERTY_THRESHOLD_LOW: 'PROPERTY_THRESHOLD_LOW',
    PROPERTY_THRESHOLD_HIGH: 'PROPERTY_THRESHOLD_HIGH',
    PROPERTY_TEMPERATURE2: 'PROPERTY_TEMPERATURE2',
    PROPERTY_LIGHT_FREQUENCY: 'PROPERTY_LIGHT_FREQUENCY',
    PROPERTY_LUMINANCE: 'PROPERTY_LUMINANCE',
    PROPERTY_AUTO_GAIN_MAXIMUM: 'PROPERTY_AUTO_GAIN_MAXIMUM',
    PROPERTY_STROBE_PIN: 'PROPERTY_STROBE_PIN',
    PROPERTY_TRIGGER_MODE: 'PROPERTY_TRIGGER_MODE',
    PROPERTY_FOCAL_LENGTH: 'PROPERTY_FOCAL_LENGTH',
    PROPERTY_IRIS_LATENCY: 'PROPERTY_IRIS_LATENCY',
    PROPERTY_TAP_CONFIGURATION: 'PROPERTY_TAP_CONFIGURATION',
    PROPERTY_STILL_TAP_CONFIGURATION: 'PROPERTY_STILL_TAP_CONFIGURATION',
    PROPERTY_MAX_FRAME_RATE: 'PROPERTY_MAX_FRAME_RATE',
    PROPERTY_AUTO_GAIN_MINIMUM: 'PROPERTY_AUTO_GAIN_MINIMUM',
    PROPERTY_TIMESTAMP_HW_RESET: 'PROPERTY_TIMESTAMP_HW_RESET',
    PROPERTY_IRIS_STEPS_COUNT: 'PROPERTY_IRIS_STEPS_COUNT',
    PROPERTY_JPEG_QUALITY: 'PROPERTY_JPEG_QUALITY',
    PROPERTY_HOST_AUTO_WB_ALGORITHM: 'PROPERTY_HOST_AUTO_WB_ALGORITHM',
    PROPERTY_HOST_AUTO_EX_ALGORITHM: 'PROPERTY_HOST_AUTO_EX_ALGORITHM',
    PROPERTY_GEV_IPCONFIG_LLA: 'PROPERTY_GEV_IPCONFIG_LLA',
    PROPERTY_GEV_IPCONFIG_DHCP: 'PROPERTY_GEV_IPCONFIG_DHCP',
    PROPERTY_GEV_IPCONFIG_PERSISTENT: 'PROPERTY_GEV_IPCONFIG_PERSISTENT',
    PROPERTY_GEV_IPCONFIG_PERSISTENT_IPADDRESS: 'PROPERTY_GEV_IPCONFIG_PERSISTENT_IPADDRESS',
    PROPERTY_GEV_IPCONFIG_PERSISTENT_SUBNETMASK: 'PROPERTY_GEV_IPCONFIG_PERSISTENT_SUBNETMASK',
    PROPERTY_GEV_IPCONFIG_PERSISTENT_DEFAULTGATEWAY: 'PROPERTY_GEV_IPCONFIG_PERSISTENT_DEFAULTGATEWAY',
    PROPERTY_GEV_SCPD: 'PROPERTY_GEV_SCPD',
}

def GetPropertyId(propertyName):
    for (id, name) in PropertyNames.iteritems():
        #print "'{0}','{1}','{2}'".format(id, name, propertyName)
        if (propertyName == name):
            return id
    return -1


PropertyNames2 = {
    'PROPERTY_BRIGHTNESS' : PROPERTY_BRIGHTNESS,
    'PROPERTY_CONTRAST' : PROPERTY_CONTRAST,
    'PROPERTY_HUE' : PROPERTY_HUE,
    'PROPERTY_SATURATION' : PROPERTY_SATURATION,
    'PROPERTY_SHARPNESS' : PROPERTY_SHARPNESS,
    'PROPERTY_GAMMA' : PROPERTY_GAMMA,
    'PROPERTY_PAN' : PROPERTY_PAN,
    'PROPERTY_TILT' : PROPERTY_TILT,
    'PROPERTY_ROLL' : PROPERTY_ROLL,
    'PROPERTY_ZOOM' : PROPERTY_ZOOM,
    'PROPERTY_EXPOSURE' : PROPERTY_EXPOSURE,
    'PROPERTY_IRIS' : PROPERTY_IRIS,
    'PROPERTY_FOCUS' : PROPERTY_FOCUS,
    'PROPERTY_GAIN' : PROPERTY_GAIN,
    'PROPERTY_GAIN_RED' : PROPERTY_GAIN_RED,
    'PROPERTY_GAIN_BLUE' : PROPERTY_GAIN_BLUE,
    'PROPERTY_GAIN_GREEN1' : PROPERTY_GAIN_GREEN1,
    'PROPERTY_GAIN_GREEN2' : PROPERTY_GAIN_GREEN2,
    'PROPERTY_GAIN_MAGENTA' : PROPERTY_GAIN_MAGENTA,
    'PROPERTY_GAIN_CYAN' : PROPERTY_GAIN_CYAN,
    'PROPERTY_GAIN_YELLOW1' : PROPERTY_GAIN_YELLOW1,
    'PROPERTY_GAIN_YELLOW2' : PROPERTY_GAIN_YELLOW2,
    'PROPERTY_STILL_EXPOSURE': PROPERTY_STILL_EXPOSURE,
    'PROPERTY_STILL_GAIN': PROPERTY_STILL_GAIN,
    'PROPERTY_STILL_GAIN_RED': PROPERTY_STILL_GAIN_RED,
    'PROPERTY_STILL_GAIN_GREEN1': PROPERTY_STILL_GAIN_GREEN1,
    'PROPERTY_STILL_GAIN_GREEN2': PROPERTY_STILL_GAIN_GREEN2,
    'PROPERTY_STILL_GAIN_BLUE': PROPERTY_STILL_GAIN_BLUE,
    'PROPERTY_STILL_STROBE_DELAY': PROPERTY_STILL_STROBE_DELAY,
    'PROPERTY_STILL_EXPOSURE_DELAY': PROPERTY_STILL_EXPOSURE_DELAY,
    'PROPERTY_DEMOSAICING_METHOD' : PROPERTY_DEMOSAICING_METHOD,
    'PROPERTY_CORRECTION_MATRIX' : PROPERTY_CORRECTION_MATRIX,
    'PROPERTY_FLIPPING' : PROPERTY_FLIPPING,
    'PROPERTY_DIGITAL_SATURATION': PROPERTY_DIGITAL_SATURATION,
    'PROPERTY_DIGITAL_HUE': PROPERTY_DIGITAL_HUE,
    'PROPERTY_DIGITAL_WHITEBALANCE_U' : PROPERTY_DIGITAL_WHITEBALANCE_U,
    'PROPERTY_DIGITAL_WHITEBALANCE_V' : PROPERTY_DIGITAL_WHITEBALANCE_V,
    'PROPERTY_DIGITAL_GAIN' : PROPERTY_DIGITAL_GAIN,
    'PROPERTY_DIGITAL_GAIN_RED' : PROPERTY_DIGITAL_GAIN_RED,
    'PROPERTY_DIGITAL_GAIN_GREEN' : PROPERTY_DIGITAL_GAIN_GREEN,
    'PROPERTY_DIGITAL_GAIN_BLUE' : PROPERTY_DIGITAL_GAIN_BLUE,
    'PROPERTY_COLOR_FORMAT' : PROPERTY_COLOR_FORMAT,
    'PROPERTY_MAX_WIDTH' : PROPERTY_MAX_WIDTH,
    'PROPERTY_MAX_HEIGHT' : PROPERTY_MAX_HEIGHT,
    'PROPERTY_UNIT_WIDTH' : PROPERTY_UNIT_WIDTH,
    'PROPERTY_UNIT_HEIGHT' : PROPERTY_UNIT_HEIGHT,
    'PROPERTY_ABS_FOCUS' : PROPERTY_ABS_FOCUS,
    'PROPERTY_BLACK_LEVEL' : PROPERTY_BLACK_LEVEL,
    'PROPERTY_KNEE1_EXPOSURE' : PROPERTY_KNEE1_EXPOSURE,
    'PROPERTY_STILL_KNEE1_EXPOSURE' : PROPERTY_STILL_KNEE1_EXPOSURE,
    'PROPERTY_KNEE2_EXPOSURE' : PROPERTY_KNEE2_EXPOSURE,
    'PROPERTY_STILL_KNEE2_EXPOSURE' : PROPERTY_STILL_KNEE2_EXPOSURE,
    'PROPERTY_STILL_KNEE3_EXPOSURE' : PROPERTY_STILL_KNEE3_EXPOSURE,
    'PROPERTY_VIDEO_KNEE' : PROPERTY_VIDEO_KNEE,
    'PROPERTY_KNEE1_LEVEL' : PROPERTY_KNEE1_LEVEL,
    'PROPERTY_THRESHOLD' : PROPERTY_THRESHOLD,
    'PROPERTY_AUTO_EXP_TARGET' : PROPERTY_AUTO_EXP_TARGET,
    'PROPERTY_TIMESTAMPS' : PROPERTY_TIMESTAMPS,
    'PROPERTY_SNAPSHOT_CLOCK_SPEED' : PROPERTY_SNAPSHOT_CLOCK_SPEED,
    'PROPERTY_AUTO_EXP_MAXIMUM' : PROPERTY_AUTO_EXP_MAXIMUM,
    'PROPERTY_TEMPERATURE' : PROPERTY_TEMPERATURE,
    'PROPERTY_TRIGGER' : PROPERTY_TRIGGER,
    'PROPERTY_TRIGGER_PIN' : PROPERTY_TRIGGER_PIN,
    'PROPERTY_FRAME_GATE' : PROPERTY_FRAME_GATE,
    'PROPERTY_EXPOSURE_INTERVAL' : PROPERTY_EXPOSURE_INTERVAL,
    'PROPERTY_PWM' : PROPERTY_PWM,
    'PROPERTY_MEMORY' : PROPERTY_MEMORY,
    'PROPERTY_STILL_STROBE_DURATION' : PROPERTY_STILL_STROBE_DURATION,
    'PROPERTY_FAN' : PROPERTY_FAN,
    'PROPERTY_SYNC_MODE' : PROPERTY_SYNC_MODE,
    'PROPERTY_SNAPSHOT_COUNT' : PROPERTY_SNAPSHOT_COUNT,
    'PROPERTY_LSC_X' : PROPERTY_LSC_X,
    'PROPERTY_LSC_Y' : PROPERTY_LSC_Y,
    'PROPERTY_AUTO_IRIS_MAX' : PROPERTY_AUTO_IRIS_MAX,
    'PROPERTY_LENS_STABILIZATION' : PROPERTY_LENS_STABILIZATION,
    'PROPERTY_VIDEO_TRIGGER' : PROPERTY_VIDEO_TRIGGER,
    'PROPERTY_VIDEO_CLOCK_SPEED' : PROPERTY_VIDEO_CLOCK_SPEED,
    'PROPERTY_KNEE2_LEVEL' : PROPERTY_KNEE2_LEVEL,
    'PROPERTY_THRESHOLD_LOW' : PROPERTY_THRESHOLD_LOW,
    'PROPERTY_THRESHOLD_HIGH' : PROPERTY_THRESHOLD_HIGH,
    'PROPERTY_TEMPERATURE2' : PROPERTY_TEMPERATURE2,
    'PROPERTY_LIGHT_FREQUENCY' : PROPERTY_LIGHT_FREQUENCY,
    'PROPERTY_LUMINANCE' : PROPERTY_LUMINANCE,
    'PROPERTY_AUTO_GAIN_MAXIMUM' : PROPERTY_AUTO_GAIN_MAXIMUM,
    'PROPERTY_STROBE_PIN' : PROPERTY_STROBE_PIN,
    'PROPERTY_TRIGGER_MODE' : PROPERTY_TRIGGER_MODE,
    'PROPERTY_FOCAL_LENGTH' : PROPERTY_FOCAL_LENGTH,
    'PROPERTY_IRIS_LATENCY' : PROPERTY_IRIS_LATENCY,
    'PROPERTY_TAP_CONFIGURATION' : PROPERTY_TAP_CONFIGURATION,
    'PROPERTY_STILL_TAP_CONFIGURATION' : PROPERTY_STILL_TAP_CONFIGURATION,
    'PROPERTY_MAX_FRAME_RATE' : PROPERTY_MAX_FRAME_RATE,
    'PROPERTY_AUTO_GAIN_MINIMUM' : PROPERTY_AUTO_GAIN_MINIMUM,
    'PROPERTY_TIMESTAMP_HW_RESET' :PROPERTY_TIMESTAMP_HW_RESET,
    'PROPERTY_IRIS_STEPS_COUNT': PROPERTY_IRIS_STEPS_COUNT,
    'PROPERTY_JPEG_QUALITY' : PROPERTY_JPEG_QUALITY,
    'PROPERTY_HOST_AUTO_WB_ALGORITHM': PROPERTY_HOST_AUTO_WB_ALGORITHM,
    'PROPERTY_HOST_AUTO_EX_ALGORITHM': PROPERTY_HOST_AUTO_EX_ALGORITHM,
    'PROPERTY_GEV_IPCONFIG_LLA': PROPERTY_GEV_IPCONFIG_LLA,
    'PROPERTY_GEV_IPCONFIG_DHCP': PROPERTY_GEV_IPCONFIG_DHCP,
    'PROPERTY_GEV_IPCONFIG_PERSISTENT': PROPERTY_GEV_IPCONFIG_PERSISTENT,
    'PROPERTY_GEV_IPCONFIG_PERSISTENT_IPADDRESS': PROPERTY_GEV_IPCONFIG_PERSISTENT_IPADDRESS,
    'PROPERTY_GEV_IPCONFIG_PERSISTENT_SUBNETMASK': PROPERTY_GEV_IPCONFIG_PERSISTENT_SUBNETMASK,
    'PROPERTY_GEV_IPCONFIG_PERSISTENT_DEFAULTGATEWAY': PROPERTY_GEV_IPCONFIG_PERSISTENT_DEFAULTGATEWAY,
    'PROPERTY_GEV_SCPD': PROPERTY_GEV_SCPD,
}

#def GetPropertyName(propertyId):
#   for (propName,id) in PropertyNames.iteritems():
#       #print "'{0}','{1}','{2}'".format(name, propName, value)
#       if (propertyId == id):
#           return propName
#
#   return "{0} (Unknown)".format(propertyId)

#// Timestamp & frame counter
#// For use with LucamGetMetadata
METADATA_FRAME_COUNTER =        1
METADATA_TIMESTAMP     =        2

#// Offset within the frame
METADATA_FRAME_COUNTER_OFFSET = 0
METADATA_TIMESTAMP_OFFSET     = 16

#// LUCAM_CONVERSION.DemosaicMethod
DEMOSAIC_METHOD_NONE           = 0
DEMOSAIC_METHOD_FAST           = 1
DEMOSAIC_METHOD_HIGH_QUALITY   = 2
DEMOSAIC_METHOD_HIGHER_QUALITY = 3
DEMOSAIC_METHOD_SIMPLE         = 8

DemosaicMethods = {
    DEMOSAIC_METHOD_NONE:           'DM_NONE',
    DEMOSAIC_METHOD_FAST:           'DM_FAST',
    DEMOSAIC_METHOD_HIGH_QUALITY:   'DM_HIGH_QUALITY',
    DEMOSAIC_METHOD_HIGHER_QUALITY: 'DM_HIGHER_QUALITY',
    DEMOSAIC_METHOD_SIMPLE:         'DM_SIMPLE'
}

#// LUCAM_CONVERSION.CorrectionMatrix
CORRECTION_MATRIX_NONE           = 0
CORRECTION_MATRIX_FLUORESCENT    = 1
CORRECTION_MATRIX_DAYLIGHT       = 2
CORRECTION_MATRIX_INCANDESCENT   = 3
CORRECTION_MATRIX_XENON_FLASH    = 4
CORRECTION_MATRIX_HALOGEN        = 5
CORRECTION_MATRIX_LED            = 6
CORRECTION_MATRIX_IDENTITY       = 14
CORRECTION_MATRIX_CUSTOM         = 15

CorrectionMatrices = {
    CORRECTION_MATRIX_NONE:         'CCM_NONE',
    CORRECTION_MATRIX_FLUORESCENT:  'CCM_FLUORESCENT',
    CORRECTION_MATRIX_DAYLIGHT:     'CCM_DAYLIGHT',
    CORRECTION_MATRIX_INCANDESCENT: 'CCM_INCANDESCENT',
    CORRECTION_MATRIX_XENON_FLASH:  'CCM_XENON_FLASH',
    CORRECTION_MATRIX_HALOGEN:      'CCM_HALOGEN',
    CORRECTION_MATRIX_LED:          'CCM_LED',
    CORRECTION_MATRIX_IDENTITY:     'CCM_IDENTITY',
    CORRECTION_MATRIX_CUSTOM:       'CCM_CUSTOM'
}

#// Values for the PROPERTY_FLIPPING
FLIPPING_NONE             = 0
FLIPPING_X                = 1
FLIPPING_Y                = 2
FLIPPING_XY               = 3

#// Values for the PROPERTY_TAP
TAP_SINGLE = 0
TAP_DUAL   = 1
TAP_QUAD   = 4

TapConfigs = {
    TAP_SINGLE: 'TAP_SINGLE',
    TAP_DUAL:   'TAP_DUAL',
    TAP_QUAD:   'TAP_QUAD'
}

#// Values for the PROPERTY_TRIGGER_MODE
TRIGGER_MODE_NORMAL = 0
TRIGGER_MODE_BULB   = 1

TriggerModes = {
    TRIGGER_MODE_NORMAL: 'NORMAL',
    TRIGGER_MODE_BULB:   'BULB',
}

#// Values for the PROPERTY_HOST_AUTO_WB_ALGORITHM and PROPERTY_HOST_AUTO_EX_ALGORITHM
AUTO_ALGORITHM_SIMPLE_AVERAGING = 0
AUTO_ALGORITHM_HISTOGRAM        = 1
AUTO_ALGORITHM_MACROBLOCKS      = 2

AutoAlgorithms = {
    AUTO_ALGORITHM_SIMPLE_AVERAGING: 'SIMPLE',
    AUTO_ALGORITHM_HISTOGRAM:        'HISTOGRAM',
    AUTO_ALGORITHM_MACROBLOCKS:      'MACROBLOCKS',
}

#// Values for the property COLOR_FORMAT
COLOR_FORMAT_MONO                        = 0
COLOR_FORMAT_BAYER_RGGB                  = 8
COLOR_FORMAT_BAYER_GRBG                  = 9
COLOR_FORMAT_BAYER_GBRG                  = 10
COLOR_FORMAT_BAYER_BGGR                  = 11
COLOR_FORMAT_BAYER_CYYM                  = 16
COLOR_FORMAT_BAYER_YCMY                  = 17
COLOR_FORMAT_BAYER_YMCY                  = 18
COLOR_FORMAT_BAYER_MYYC                  = 19

ColorFormats = {
    COLOR_FORMAT_MONO:       'MONO',
    COLOR_FORMAT_BAYER_RGGB: 'RGGB',
    COLOR_FORMAT_BAYER_GRBG: 'GRBG',
    COLOR_FORMAT_BAYER_GBRG: 'GBRG',
    COLOR_FORMAT_BAYER_BGGR: 'BGGR',
    COLOR_FORMAT_BAYER_CYYM: 'CYYM',
    COLOR_FORMAT_BAYER_YCMY: 'YCMY',
    COLOR_FORMAT_BAYER_YMCY: 'YMCY',
    COLOR_FORMAT_BAYER_MYYC: 'MYYC',
}

#// Property flags
PROPERTY_FLAG_USE                           = 0x80000000
PROPERTY_FLAG_AUTO                          = 0x40000000
PROPERTY_FLAG_MASTER                        = 0x40000000 #// for LUCAM_PROP_SYNC_MODE
PROPERTY_FLAG_STROBE_FROM_START_OF_EXPOSURE = 0x20000000
PROPERTY_FLAG_BACKLASH_COMPENSATION         = 0x20000000 #// LUCAM_PROP_IRIS and LUCAM_PROP_FOCUS
PROPERTY_FLAG_USE_FOR_SNAPSHOTS             = 0x04000000 #// For LUCAM_PROP_IRIS
PROPERTY_FLAG_POLARITY                      = 0x10000000
PROPERTY_FLAG_MEMORY_READBACK               = 0x08000000 #// for LUCAM_PROP_MEMORY
PROPERTY_FLAG_BUSY                          = 0x00040000
PROPERTY_FLAG_UNKNOWN_MAXIMUM               = 0x00020000
PROPERTY_FLAG_UNKNOWN_MINIMUM               = 0x00010000
PROPERTY_FLAG_LITTLE_ENDIAN                 = 0x80000000 #// for LUCAM_PROP_COLOR_FORMAT
PROPERTY_FLAG_ALTERNATE                     = 0x00080000 
PROPERTY_FLAG_READONLY                      = 0x00010000 #// in caps param of GetPropertyRange
#// Prop flags for VIDEO_TRIGGER (also uses LUCAM_PROP_FLAG_USE)
PROPERTY_FLAG_HW_ENABLE                     = 0x40000000
PROPERTY_FLAG_SW_TRIGGER                    = 0x00200000 #// self cleared

PropertyFlags = {
    PROPERTY_FLAG_USE: 'PROPERTY_FLAG_USE',
    PROPERTY_FLAG_AUTO: 'PROPERTY_FLAG_AUTO',
    PROPERTY_FLAG_STROBE_FROM_START_OF_EXPOSURE: 'PROPERTY_FLAG_STROBE_FROM_START_OF_EXPOSURE',
    PROPERTY_FLAG_POLARITY: 'PROPERTY_FLAG_POLARITY',
    PROPERTY_FLAG_MEMORY_READBACK: 'PROPERTY_FLAG_MEMORY_READBACK',
    PROPERTY_FLAG_USE_FOR_SNAPSHOTS: 'PROPERTY_FLAG_USE_FOR_SNAPSHOTS',
    PROPERTY_FLAG_ALTERNATE: 'PROPERTY_FLAG_ALTERNATE',
    PROPERTY_FLAG_BUSY: 'PROPERTY_FLAG_BUSY',
    PROPERTY_FLAG_UNKNOWN_MAXIMUM: 'PROPERTY_FLAG_UNKNOWN_MAXIMUM',
    PROPERTY_FLAG_UNKNOWN_MINIMUM: 'PROPERTY_FLAG_UNKNOWN_MINIMUM',
}


ERROR_NO_ERROR_ = 0
ERROR_NO_SUCH_INDEX = 1
ERROR_SNAPSHOT_NOT_SUPPORTED = 2
ERROR_INVALID_PIXEL_FORMAT = 3
ERROR_SUBSAMPLING_ZERO = 4
ERROR_BUSY = 5
ERROR_FAILED_TO_SET_SUBSAMPLING = 6
ERROR_FAILED_TO_SET_START_POSITION = 7
ERROR_PIXEL_FORMAT_NOT_SUPPORTED = 8
ERROR_INVALID_FRAME_FORMAT = 9
ERROR_PREPARATION_FAILED = 10
ERROR_CANNOT_RUN = 11
ERROR_NO_TRIGGER_CONTROL = 12
ERROR_NO_PIN = 13
ERROR_NOT_RUNNING = 14
ERROR_TRIGGER_FAILED = 15
ERROR_CANNOT_SET_UP_FRAME_FORMAT = 16
ERROR_DIRECTSHOW_INIT_ERROR_ = 17
ERROR_CAMERA_NOT_FOUND = 18
ERROR_TIMEOUT = 19
ERROR_PROPERTY_UNKNOWN = 20
ERROR_PROPERTY_UNSUPPORTED = 21
ERROR_PROPERTY_ACCESS_FAILED = 22
ERROR_LUCUSTOM_FILTER_NOT_FOUND = 23
ERROR_PREVIEW_NOT_RUNNING = 24
ERROR_LUTF_NOT_LOADED = 25
ERROR_DIRECTSHOW_ERROR_ = 26
ERROR_NO_MORE_CALLBACKS = 27
ERROR_UNDETERMINED_FRAME_FORMAT = 28
ERROR_INVALID_PARAMETER = 29
ERROR_NOT_ENOUGH_RESOURCES = 30
ERROR_INVALID_CONVERSION = 31
ERROR_PARAMETER_OUT_OF_RANGE = 32
ERROR_FILE_ERROR = 33
ERROR_GDIPLUS_NOT_FOUND = 34
ERROR_GDIPLUS_ERROR_ = 35
ERROR_INVALID_FORMAT_TYPE = 36
ERROR_CREATEDISPLAY_FAILED = 37
ERROR_DELTA_POLATION_LIB_NOT_FOUND = 38
ERROR_DELTA_POLATION_COMMAND_NOT_SUPPORTED = 39
ERROR_DELTA_POLATION_COMMAND_INVALID = 40
ERROR_INVALID_OPERATION_WHILE_PAUSED = 41
ERROR_CAPTURE_FAILED = 42
ERROR_DP_ERROR_ = 43
ERROR_INVALID_FRAME_RATE = 44
ERROR_INVALID_TARGET = 45
ERROR_FRAME_TOO_DARK = 46
ERROR_IKSCONTROL_PROPERTY_SET_NOT_FOUND = 47
ERROR_OPERATION_CANCELLED_BY_USER = 48
ERROR_IKSCONTROL_NOT_SUPPORTED = 49
ERROR_EVENT_NOT_SUPPORTED = 50
ERROR_NOT_LIVE_PREVIEWING = 51
ERROR_SET_POSITION_FAILED = 52
ERROR_NO_FRAME_RATE_LIST = 53
ERROR_FRAME_RATE_INCONSISTENT = 54
ERROR_CAMERA_NOT_CONFIGURED_FOR_COMMAND = 55
ERROR_GRAPHNOTREADY = 56
ERROR_CALLBACK_SETUP_ERROR_ = 57
ERROR_INVALID_TRIGGER_MODE = 58
ERROR_NOT_FOUND = 59
ERROR_PERMANENT_BUFFER_NOT_SUPPORTED = 60
ERROR_EEPROM_WRITE_FAILED = 61
ERROR_UNKNOWN_FILE_TYPE = 62
ERROR_EVENT_ID_NOT_SUPPORTED = 63
ERROR_EEPROM_IS_CORRUPT = 64
ERROR_VPD_SECTION_TOO_BIG = 65
ERROR_FRAME_TOO_BRIGHT = 66
ERROR_NO_CORRECTION_MATRIX = 67
ERROR_UNKNOWN_CAMERA_MODEL = 68
ERROR_API_TOO_OLD = 69
ERROR_SATURATION_IS_ZERO = 70
ERROR_ALREADY_INITIALISED = 71
ERROR_SAME_INPUT_AND_OUTPUT_FILE = 72
ERROR_FILE_CONVERSION_FAILED = 73
ERROR_FILE_ALREADY_CONVERTED = 74
ERROR_PROPERTY_PAGE_NOT_SUPPORTED = 75
ERROR_PROPERTY_PAGE_CREATION_FAILED = 76
ERROR_DIRECTSHOW_FILTER_NOT_INSTALLED = 77
ERROR_INDIVIDUAL_LUT_NOT_AVAILABLE = 78
ERROR_UNEXPECTED_ERROR_ = 79
ERROR_STREAMING_IS_STOPPED = 80
ERROR_MUST_BE_IN_SOFTWARE_TRIGGER_MODE = 81
ERROR_TARGET_TOO_DYNAMIC_FOR_AUTO_FOCUS = 82
ERROR_AUTO_LENS_NOT_INITIALIZED = 83
ERROR_LENS_NOT_INSTALLED = 84
ERROR_UNKNOWN_ERROR = 85
ERROR_NO_FEEDBACK_FOR_FOCUS = 86
ERROR_LUTF_TOO_OLD = 87
ERROR_UNKNOWN_AVI_FORMAT = 88
ERROR_UNKNOWN_AVI_TYPE = 89
ERROR_INVALID_AVI_CONVERSION = 90
ERROR_SEEK_FAILED = 91
ERROR_INVALID_OPERATION_WHILE_AVI_RUNNING = 92
ERROR_CAMERA_ALREADY_OPEN = 93
ERROR_NO_AVI_WHEN_SUBSAMPLED_HIGH_RES = 94
ERROR_ONLY_ON_MONOCHROME = 95
ERROR_NO_8BPP_TO_48BPP = 96
ERROR_LUT8_OBSOLETE = 97
ERROR_FUNCTION_NOT_SUPPORTED = 98
ERROR_RETRY_LIMIT_REACHED = 99
ERROR_LG_DEVICE_ERROR_ = 100
ERROR_INVALID_IP_CONFIGURATION = 101
ERROR_INVALID_LICENSE = 102
ERROR_NO_SYSTEM_ENUMERATOR = 103
ERROR_BUS_ENUMERATOR_NOT_INSTALLED = 104
ERROR_UNKNOWN_EXTERN_INTERFACE = 105
ERROR_INTERFACE_DRIVER_NOT_INSTALLED = 106
ERROR_CAMERA_DRIVER_NOT_INSTALLED = 107
ERROR_CAMERA_DRIVER_INSTALL_IN_PROGRESS = 108
ERROR_LUCAMAPIDOTDLL_NOT_FOUND = 109
ERROR_API_PROCEDURE_NOT_FOUND = 110
ERROR_PROPERTY_NOT_ENUMERABLE = 111
ERROR_PROPERTY_NOT_BUFFERABLE = 112
ERROR_SINGLE_TAP_IMAGE = 113
ERROR_UNKNOWN_TAP_CONFIGURATION = 114
ERROR_BUFFER_TOO_SMALL = 115
ERROR_IN_CALLBACK_ONLY = 116
ERROR_PROPERTY_UNAVAILABLE = 117
ERROR_TIMESTAMP_NOT_ENABLED = 118
ERROR_FRAMECOUNTER_NOT_ENABLED = 119
ERROR_NO_STATS_WHEN_NOT_STREAMING = 120
ERROR_FRAME_CAPTURE_PENDING = 121
ERROR_SEQUENCING_NOT_ENABLED = 122
ERROR_FEATURE_NOT_SEQUENCABLE = 123
ERROR_SEQUENCING_UNKNOWN_FEATURE_TYPE = 124
ERROR_SEQUENCING_INDEX_OUT_OF_SEQUENCE = 125
ERROR_SEQUENCING_BAD_FRAME_NUMBER = 126
#// the following are specific to linux
ERROR_CAMERA_NOT_OPENABLE = 1121
ERROR_CAMERA_NOT_SUPPORTED = 1122
ERROR_MMAP_FAILED = 1123
ERROR_NOT_WHILE_STREAMING = 1124
ERROR_NO_STREAMING_RIGHTS = 1125
ERROR_CAMERA_INITIALIZATION_ERROR = 1126
ERROR_CANNOT_VERIFY_PIXEL_FORMAT = 1127
ERROR_CANNOT_VERIFY_START_POSITION = 1128
ERROR_OS_ERROR = 1129
ERROR_BUFFER_NOT_AVAILABLE = 1130
ERROR_QUEUING_FAILED = 1131


ErrorDescriptions = { 
    ERROR_NO_ERROR_ : 'ERROR_NO_ERROR_',
    ERROR_NO_SUCH_INDEX : 'ERROR_NO_SUCH_INDEX',
    ERROR_SNAPSHOT_NOT_SUPPORTED : 'ERROR_SNAPSHOT_NOT_SUPPORTED',
    ERROR_INVALID_PIXEL_FORMAT : 'ERROR_INVALID_PIXEL_FORMAT',
    ERROR_SUBSAMPLING_ZERO : 'ERROR_SUBSAMPLING_ZERO',
    ERROR_BUSY : 'ERROR_BUSY',
    ERROR_FAILED_TO_SET_SUBSAMPLING : 'ERROR_FAILED_TO_SET_SUBSAMPLING',
    ERROR_FAILED_TO_SET_START_POSITION : 'ERROR_FAILED_TO_SET_START_POSITION',
    ERROR_PIXEL_FORMAT_NOT_SUPPORTED : 'ERROR_PIXEL_FORMAT_NOT_SUPPORTED',
    ERROR_INVALID_FRAME_FORMAT : 'ERROR_INVALID_FRAME_FORMAT',
    ERROR_PREPARATION_FAILED : 'ERROR_PREPARATION_FAILED',
    ERROR_CANNOT_RUN : 'ERROR_CANNOT_RUN',
    ERROR_NO_TRIGGER_CONTROL : 'ERROR_NO_TRIGGER_CONTROL',
    ERROR_NO_PIN : 'ERROR_NO_PIN',
    ERROR_NOT_RUNNING : 'ERROR_NOT_RUNNING',
    ERROR_TRIGGER_FAILED : 'ERROR_TRIGGER_FAILED',
    ERROR_CANNOT_SET_UP_FRAME_FORMAT : 'ERROR_CANNOT_SET_UP_FRAME_FORMAT',
    ERROR_DIRECTSHOW_INIT_ERROR_ : 'ERROR_DIRECTSHOW_INIT_ERROR_',
    ERROR_CAMERA_NOT_FOUND : 'ERROR_CAMERA_NOT_FOUND',
    ERROR_TIMEOUT : 'ERROR_TIMEOUT',
    ERROR_PROPERTY_UNKNOWN : 'ERROR_PROPERTY_UNKNOWN',
    ERROR_PROPERTY_UNSUPPORTED : 'ERROR_PROPERTY_UNSUPPORTED',
    ERROR_PROPERTY_ACCESS_FAILED : 'ERROR_PROPERTY_ACCESS_FAILED',
    ERROR_LUCUSTOM_FILTER_NOT_FOUND : 'ERROR_LUCUSTOM_FILTER_NOT_FOUND',
    ERROR_PREVIEW_NOT_RUNNING : 'ERROR_PREVIEW_NOT_RUNNING',
    ERROR_LUTF_NOT_LOADED : 'ERROR_LUTF_NOT_LOADED',
    ERROR_DIRECTSHOW_ERROR_ : 'ERROR_DIRECTSHOW_ERROR_',
    ERROR_NO_MORE_CALLBACKS : 'ERROR_NO_MORE_CALLBACKS',
    ERROR_UNDETERMINED_FRAME_FORMAT : 'ERROR_UNDETERMINED_FRAME_FORMAT',
    ERROR_INVALID_PARAMETER : 'ERROR_INVALID_PARAMETER',
    ERROR_NOT_ENOUGH_RESOURCES : 'ERROR_NOT_ENOUGH_RESOURCES',
    ERROR_INVALID_CONVERSION : 'ERROR_INVALID_CONVERSION',
    ERROR_PARAMETER_OUT_OF_RANGE : 'ERROR_PARAMETER_OUT_OF_RANGE',
    ERROR_FILE_ERROR : 'ERROR_FILE_ERROR',
    ERROR_GDIPLUS_NOT_FOUND : 'ERROR_GDIPLUS_NOT_FOUND',
    ERROR_GDIPLUS_ERROR_ : 'ERROR_GDIPLUS_ERROR_',
    ERROR_INVALID_FORMAT_TYPE : 'ERROR_INVALID_FORMAT_TYPE',
    ERROR_CREATEDISPLAY_FAILED : 'ERROR_CREATEDISPLAY_FAILED',
    ERROR_DELTA_POLATION_LIB_NOT_FOUND : 'ERROR_DELTA_POLATION_LIB_NOT_FOUND',
    ERROR_DELTA_POLATION_COMMAND_NOT_SUPPORTED : 'ERROR_DELTA_POLATION_COMMAND_NOT_SUPPORTED',
    ERROR_DELTA_POLATION_COMMAND_INVALID : 'ERROR_DELTA_POLATION_COMMAND_INVALID',
    ERROR_INVALID_OPERATION_WHILE_PAUSED : 'ERROR_INVALID_OPERATION_WHILE_PAUSED',
    ERROR_CAPTURE_FAILED : 'ERROR_CAPTURE_FAILED',
    ERROR_DP_ERROR_ : 'ERROR_DP_ERROR_',
    ERROR_INVALID_FRAME_RATE : 'ERROR_INVALID_FRAME_RATE',
    ERROR_INVALID_TARGET : 'ERROR_INVALID_TARGET',
    ERROR_FRAME_TOO_DARK : 'ERROR_FRAME_TOO_DARK',
    ERROR_IKSCONTROL_PROPERTY_SET_NOT_FOUND : 'ERROR_IKSCONTROL_PROPERTY_SET_NOT_FOUND',
    ERROR_OPERATION_CANCELLED_BY_USER : 'ERROR_OPERATION_CANCELLED_BY_USER',
    ERROR_IKSCONTROL_NOT_SUPPORTED : 'ERROR_IKSCONTROL_NOT_SUPPORTED',
    ERROR_EVENT_NOT_SUPPORTED : 'ERROR_EVENT_NOT_SUPPORTED',
    ERROR_NOT_LIVE_PREVIEWING : 'ERROR_NOT_LIVE_PREVIEWING',
    ERROR_SET_POSITION_FAILED : 'ERROR_SET_POSITION_FAILED',
    ERROR_NO_FRAME_RATE_LIST : 'ERROR_NO_FRAME_RATE_LIST',
    ERROR_FRAME_RATE_INCONSISTENT : 'ERROR_FRAME_RATE_INCONSISTENT',
    ERROR_CAMERA_NOT_CONFIGURED_FOR_COMMAND : 'ERROR_CAMERA_NOT_CONFIGURED_FOR_COMMAND',
    ERROR_GRAPHNOTREADY : 'ERROR_GRAPHNOTREADY',
    ERROR_CALLBACK_SETUP_ERROR_ : 'ERROR_CALLBACK_SETUP_ERROR_',
    ERROR_INVALID_TRIGGER_MODE : 'ERROR_INVALID_TRIGGER_MODE',
    ERROR_NOT_FOUND : 'ERROR_NOT_FOUND',
    ERROR_PERMANENT_BUFFER_NOT_SUPPORTED : 'ERROR_PERMANENT_BUFFER_NOT_SUPPORTED',
    ERROR_EEPROM_WRITE_FAILED : 'ERROR_EEPROM_WRITE_FAILED',
    ERROR_UNKNOWN_FILE_TYPE : 'ERROR_UNKNOWN_FILE_TYPE',
    ERROR_EVENT_ID_NOT_SUPPORTED : 'ERROR_EVENT_ID_NOT_SUPPORTED',
    ERROR_EEPROM_IS_CORRUPT : 'ERROR_EEPROM_IS_CORRUPT',
    ERROR_VPD_SECTION_TOO_BIG : 'ERROR_VPD_SECTION_TOO_BIG',
    ERROR_FRAME_TOO_BRIGHT : 'ERROR_FRAME_TOO_BRIGHT',
    ERROR_NO_CORRECTION_MATRIX : 'ERROR_NO_CORRECTION_MATRIX',
    ERROR_UNKNOWN_CAMERA_MODEL : 'ERROR_UNKNOWN_CAMERA_MODEL',
    ERROR_API_TOO_OLD : 'ERROR_API_TOO_OLD',
    ERROR_SATURATION_IS_ZERO : 'ERROR_SATURATION_IS_ZERO',
    ERROR_ALREADY_INITIALISED : 'ERROR_ALREADY_INITIALISED',
    ERROR_SAME_INPUT_AND_OUTPUT_FILE : 'ERROR_SAME_INPUT_AND_OUTPUT_FILE',
    ERROR_FILE_CONVERSION_FAILED : 'ERROR_FILE_CONVERSION_FAILED',
    ERROR_FILE_ALREADY_CONVERTED : 'ERROR_FILE_ALREADY_CONVERTED',
    ERROR_PROPERTY_PAGE_NOT_SUPPORTED : 'ERROR_PROPERTY_PAGE_NOT_SUPPORTED',
    ERROR_PROPERTY_PAGE_CREATION_FAILED : 'ERROR_PROPERTY_PAGE_CREATION_FAILED',
    ERROR_DIRECTSHOW_FILTER_NOT_INSTALLED : 'ERROR_DIRECTSHOW_FILTER_NOT_INSTALLED',
    ERROR_INDIVIDUAL_LUT_NOT_AVAILABLE : 'ERROR_INDIVIDUAL_LUT_NOT_AVAILABLE',
    ERROR_UNEXPECTED_ERROR_ : 'ERROR_UNEXPECTED_ERROR_',
    ERROR_STREAMING_IS_STOPPED : 'ERROR_STREAMING_IS_STOPPED',
    ERROR_MUST_BE_IN_SOFTWARE_TRIGGER_MODE : 'ERROR_MUST_BE_IN_SOFTWARE_TRIGGER_MODE',
    ERROR_TARGET_TOO_DYNAMIC_FOR_AUTO_FOCUS : 'ERROR_TARGET_TOO_DYNAMIC_FOR_AUTO_FOCUS',
    ERROR_AUTO_LENS_NOT_INITIALIZED : 'ERROR_AUTO_LENS_NOT_INITIALIZED',
    ERROR_LENS_NOT_INSTALLED : 'ERROR_LENS_NOT_INSTALLED',
    ERROR_UNKNOWN_ERROR : 'ERROR_UNKNOWN_ERROR',
    ERROR_NO_FEEDBACK_FOR_FOCUS : 'ERROR_NO_FEEDBACK_FOR_FOCUS',
    ERROR_LUTF_TOO_OLD : 'ERROR_LUTF_TOO_OLD',
    ERROR_UNKNOWN_AVI_FORMAT : 'ERROR_UNKNOWN_AVI_FORMAT',
    ERROR_UNKNOWN_AVI_TYPE : 'ERROR_UNKNOWN_AVI_TYPE',
    ERROR_INVALID_AVI_CONVERSION : 'ERROR_INVALID_AVI_CONVERSION',
    ERROR_SEEK_FAILED : 'ERROR_SEEK_FAILED',
    ERROR_INVALID_OPERATION_WHILE_AVI_RUNNING : 'ERROR_INVALID_OPERATION_WHILE_AVI_RUNNING',
    ERROR_CAMERA_ALREADY_OPEN : 'ERROR_CAMERA_ALREADY_OPEN',
    ERROR_NO_AVI_WHEN_SUBSAMPLED_HIGH_RES : 'ERROR_NO_AVI_WHEN_SUBSAMPLED_HIGH_RES',
    ERROR_ONLY_ON_MONOCHROME : 'ERROR_ONLY_ON_MONOCHROME',
    ERROR_NO_8BPP_TO_48BPP : 'ERROR_NO_8BPP_TO_48BPP',
    ERROR_LUT8_OBSOLETE : 'ERROR_LUT8_OBSOLETE',
    ERROR_FUNCTION_NOT_SUPPORTED : 'ERROR_FUNCTION_NOT_SUPPORTED',
    ERROR_RETRY_LIMIT_REACHED : 'ERROR_RETRY_LIMIT_REACHED',
    ERROR_LG_DEVICE_ERROR_ : 'ERROR_LG_DEVICE_ERROR_',
    ERROR_INVALID_IP_CONFIGURATION : 'ERROR_INVALID_IP_CONFIGURATION',
    ERROR_INVALID_LICENSE : 'ERROR_INVALID_LICENSE',
    ERROR_NO_SYSTEM_ENUMERATOR : 'ERROR_NO_SYSTEM_ENUMERATOR',
    ERROR_BUS_ENUMERATOR_NOT_INSTALLED : 'ERROR_BUS_ENUMERATOR_NOT_INSTALLED',
    ERROR_UNKNOWN_EXTERN_INTERFACE : 'ERROR_UNKNOWN_EXTERN_INTERFACE',
    ERROR_INTERFACE_DRIVER_NOT_INSTALLED : 'ERROR_INTERFACE_DRIVER_NOT_INSTALLED',
    ERROR_CAMERA_DRIVER_NOT_INSTALLED : 'ERROR_CAMERA_DRIVER_NOT_INSTALLED',
    ERROR_CAMERA_DRIVER_INSTALL_IN_PROGRESS : 'ERROR_CAMERA_DRIVER_INSTALL_IN_PROGRESS',
    ERROR_LUCAMAPIDOTDLL_NOT_FOUND : 'ERROR_LUCAMAPIDOTDLL_NOT_FOUND',
    ERROR_API_PROCEDURE_NOT_FOUND : 'ERROR_API_PROCEDURE_NOT_FOUND',
    ERROR_PROPERTY_NOT_ENUMERABLE : 'ERROR_PROPERTY_NOT_ENUMERABLE',
    ERROR_PROPERTY_NOT_BUFFERABLE : 'ERROR_PROPERTY_NOT_BUFFERABLE',
    ERROR_SINGLE_TAP_IMAGE : 'ERROR_SINGLE_TAP_IMAGE',
    ERROR_UNKNOWN_TAP_CONFIGURATION : 'ERROR_UNKNOWN_TAP_CONFIGURATION',
    ERROR_BUFFER_TOO_SMALL : 'ERROR_BUFFER_TOO_SMALL',
    ERROR_IN_CALLBACK_ONLY : 'ERROR_IN_CALLBACK_ONLY',
    ERROR_PROPERTY_UNAVAILABLE : 'ERROR_PROPERTY_UNAVAILABLE',
    ERROR_TIMESTAMP_NOT_ENABLED : 'ERROR_TIMESTAMP_NOT_ENABLED',
    ERROR_FRAMECOUNTER_NOT_ENABLED : 'ERROR_FRAMECOUNTER_NOT_ENABLED',
    ERROR_NO_STATS_WHEN_NOT_STREAMING : 'ERROR_NO_STATS_WHEN_NOT_STREAMING',
    ERROR_FRAME_CAPTURE_PENDING : 'ERROR_FRAME_CAPTURE_PENDING',
    ERROR_SEQUENCING_NOT_ENABLED : 'ERROR_SEQUENCING_NOT_ENABLED',
    ERROR_FEATURE_NOT_SEQUENCABLE : 'ERROR_FEATURE_NOT_SEQUENCABLE',
    ERROR_SEQUENCING_UNKNOWN_FEATURE_TYPE : 'ERROR_SEQUENCING_UNKNOWN_FEATURE_TYPE',
    ERROR_SEQUENCING_INDEX_OUT_OF_SEQUENCE : 'ERROR_SEQUENCING_INDEX_OUT_OF_SEQUENCE',
    ERROR_SEQUENCING_BAD_FRAME_NUMBER : 'ERROR_SEQUENCING_BAD_FRAME_NUMBER',
    ERROR_CAMERA_NOT_OPENABLE : 'ERROR_CAMERA_NOT_OPENABLE',
    ERROR_CAMERA_NOT_SUPPORTED : 'ERROR_CAMERA_NOT_SUPPORTED',
    ERROR_MMAP_FAILED : 'ERROR_MMAP_FAILED',
    ERROR_NOT_WHILE_STREAMING : 'ERROR_NOT_WHILE_STREAMING',
    ERROR_NO_STREAMING_RIGHTS : 'ERROR_NO_STREAMING_RIGHTS',
    ERROR_CAMERA_INITIALIZATION_ERROR : 'ERROR_CAMERA_INITIALIZATION_ERROR',
    ERROR_CANNOT_VERIFY_PIXEL_FORMAT : 'ERROR_CANNOT_VERIFY_PIXEL_FORMAT',
    ERROR_CANNOT_VERIFY_START_POSITION : 'ERROR_CANNOT_VERIFY_START_POSITION',
    ERROR_OS_ERROR : 'ERROR_OS_ERROR',
    ERROR_BUFFER_NOT_AVAILABLE : 'ERROR_BUFFER_NOT_AVAILABLE',
    ERROR_QUEUING_FAILED : 'ERROR_QUEUING_FAILED',
}

def GetApiErrorDescription(apiError):
    return ErrorDescriptions.get(apiError, "{0} (Unknown)".format(apiError))

#//
#// A thin wrapper around the dynamic library (.dll, .so) that exposes the Lumenera API
#// This uses ctypes to adapt from C to Python
#//
class DynamicLibrary:
    def __init__(self):
        if 'Windows' == platform.system():
            self.lib = C.windll.LoadLibrary("lucamapi.dll")
        elif 'Linux' == platform.system():
            # this section assumes that the LUMENERA_SDK is set and that the lib can be found there
            if 'arm' in platform.machine():
                archPath = "lib" + os.sep + "arm" + os.sep
            elif 'aarch64' in platform.machine():
                archPath = "lib" + os.sep + "aarch64" + os.sep
            else:
                #// ARCH BITS
                
                #// ARCH_BITS is used on linux to determine if this wrapper should look in 
                #// lib/i386 or lib/x86-64 for the liblucamapi.so.n.m
                #// ARCH_BITS is 32 on 32 bit systems and 64 on 64 bit systems
                ARCH_BITS = C.sizeof(C.c_void_p) * 8
                if ARCH_BITS == 32:
                    archPath = "lib" + os.sep + "i386" + os.sep
                else:
                    archPath = "lib" + os.sep + "x86-64" + os.sep
            shared_obj = os.listdir(LINUX_LIB_PATH + os.sep + archPath)[0]
            self.libPath = os.path.normpath(LINUX_LIB_PATH + os.sep + archPath + shared_obj)
            self.lib = C.cdll.LoadLibrary(self.libPath)
            print ("{0}".format(self.libPath))
        elif 'Darwin' == platform.system():
            self.libPath = os.path.normpath(DARWIN_LIB_PATH)
            self.lib = C.cdll.LoadLibrary(self.libPath + os.path.sep + 'LuCamSDK')
        else:
            raise Exception("{0} platform not yet supported".format(platform.system()))
        self.GetLibVersion()
        InitializeLucamLibFunctionSignatures(self.lib)
        
    def __str__(self):
        return str(self.lib)

    __repr__ = __str__
        
    def GetLibVersion(self):
        self.lib.API_VERSION = ()
        if 'Windows' == platform.system():
            try:
                from win32api import GetFileVersionInfo, HIWORD, LOWORD
                try:
                    VS_FIXEDFILEINFO = "\\"
                    info = GetFileVersionInfo('lucamapi.dll', VS_FIXEDFILEINFO)
                    self.lib.API_VERSION = (HIWORD(info['FileVersionMS']), LOWORD(info['FileVersionMS']), HIWORD(info['FileVersionLS']), LOWORD(info['FileVersionLS']))
                except:
                    self.lib.API_VERSION = (0,0,0,0)
            except ImportError:
                print('win32api is not available, setting api version to 2.1.1.50')
                self.lib.API_VERSION = (2,1,1,50)
        elif 'Linux' == platform.system():
            try:
                version = self.libPath.split('lucamapi.so.')[1]
                v = lambda x: int(version.split('.')[x]) if x < len(version.split('.')) else 0
                self.lib.API_VERSION = (v(0), v(1), v(2), v(3))
            except:
                self.lib.API_VERSION = (0,0,0,0)
        elif 'Darwin' == platform.system():
            try:
                from plistlib import readPlist
                pl = readPlist(self.libPath + os.path.sep + 'Resources/Info.plist')
                version = pl['CFBundleShortVersionString']
                v = lambda x: int(version.split('.')[x])
                self.lib.API_VERSION = (v(0), v(1), v(2), v(3))
            except:
                self.lib.API_VERSION = (0,0,0,0)
        else:
            self.lib.API_VERSION = (0,0,0,0)
        #print self.lib.API_VERSION

    def RegisterEvent(self, hCamera, event, hEvent):
        return self.lib.LucamRegisterEventNotification(HANDLE(hCamera), C.c_ulong(event), C.c_int(hEvent))

    def UnRegisterEvent(self, hCamera, hEvent):
        return self.lib.LucamUnregisterEventNotification(HANDLE(hCamera), hEvent)

    def AddStreamingCallback(self, hCamera, cb, context):
        return self.lib.LucamAddStreamingCallback(HANDLE(hCamera), cb, context)

    def RemoveStreamingCallback(self, hCamera, callbackId):
        return self.lib.LucamRemoveStreamingCallback(HANDLE(hCamera), callbackId)

    def AddSnapshotCallback(self, hCamera, cb, context):
        return self.lib.LucamAddSnapshotCallback(HANDLE(hCamera), cb, context)

    def RemoveSnapshotCallback(self, hCamera, callbackId):
        return self.lib.LucamRemoveSnapshotCallback(HANDLE(hCamera), callbackId)

    def AddRgbPreviewCallback(self, hCamera, cb, context, rgbPixelFormat):
        return self.lib.LucamAddRgbPreviewCallback(HANDLE(hCamera), cb, context, rgbPixelFormat)
    
    def RemoveRgbPreviewCallback(self, hCamera, callbackId):
        return self.lib.LucamRemoveRgbPreviewCallback(HANDLE(hCamera), callbackId)
    
    def SelectExternInterface(self, interface):
        return self.lib.LucamSelectExternInterface(C.c_ulong(interface))
        
    def NumCameras(self):
        return self.lib.LucamNumCameras()
        
    def EnumCameras(self):
        gigeNotInstalled = int("0xFFFFFFFF",0) # aka -1
        numCameras = self.NumCameras()
        if numCameras == gigeNotInstalled:
            print ("LucamNumCameras returned -1, are you trying to use GIGE but it isn't installed?")
            numCameras = 0
            
        verArray = (LUCAM_VERSION * numCameras)()
        
        if 0 == numCameras:
            return (0, verArray)
            
        rv = self.lib.LucamEnumCameras(pLUCAM_VERSION(verArray), C.c_ulong(numCameras))
        return (rv, verArray)
        
    def CameraOpen(self, cameraIndex):
        hCamera = self.lib.LucamCameraOpen(C.c_ulong(cameraIndex))
        return hCamera

    def CameraClose(self, hCamera):
        success = self.lib.LucamCameraClose(HANDLE(hCamera))
        return success

    def CameraReset(self, hCamera):
        success = self.lib.LucamCameraReset(HANDLE(hCamera))
        return success
        
    def GetProperty(self, hCamera, propertyId):
        value = C.c_float(0.0)
        flags = C.c_ulong(0)
        rv = self.lib.LucamGetProperty(HANDLE(hCamera), C.c_ulong(propertyId), pFLOAT(value), pULONG(flags))
        if (0 == rv):
            return (False,0.0, 0)
        return (True, value, flags)
        
    def SetProperty(self, hCamera, propertyId, newValue, flags = 0):
        rv = self.lib.LucamSetProperty(HANDLE(hCamera), C.c_ulong(propertyId), C.c_float(newValue), C.c_ulong(flags))
        return rv
    
    def PropertyRange(self, hCamera, propertyId):
        min = C.c_float(0)
        max = C.c_float(0)
        default = C.c_float(0)
        flags = C.c_ulong(0)
        rv = self.lib.LucamPropertyRange(HANDLE(hCamera), C.c_ulong(propertyId), 
                                         pFLOAT(min), pFLOAT(max), pFLOAT(default), pULONG(flags))
        if (0 == rv):
            return (False, 0.0, 0.0, 0.0, 0)
        return (True, min, max, default, flags)

    def StreamVideoControl(self, hCamera, streamState, hWnd):
        success = self.lib.LucamStreamVideoControl(HANDLE(hCamera), C.c_ulong(streamState), HWND(hWnd))
        return success
        
    def GetVideoImageFormat(self, hCamera):
        imageFormat = LUCAM_IMAGE_FORMAT()
        imageFormat.size = C.sizeof(LUCAM_IMAGE_FORMAT())
        success = self.lib.LucamGetVideoImageFormat(HANDLE(hCamera), pLUCAM_IMAGE_FORMAT(imageFormat))
        return (success, imageFormat)

    def GetStillImageFormat(self, hCamera):
        imageFormat = LUCAM_IMAGE_FORMAT()
        imageFormat.size = C.sizeof(LUCAM_IMAGE_FORMAT())
        success = self.lib.LucamGetStillImageFormat(HANDLE(hCamera), pLUCAM_IMAGE_FORMAT(imageFormat))
        return (success, imageFormat)

    def GetFormat(self, hCamera):
        frameFormat = LUCAM_FRAME_FORMAT()
        frameRate = C.c_float(0.0)
        success = self.lib.LucamGetFormat(HANDLE(hCamera), pLUCAM_FRAME_FORMAT(frameFormat), pFLOAT(frameRate))
        return (success, frameFormat, frameRate)
        
    def SetFormat(self, hCamera, frameFormat, frameRate):
        success = self.lib.LucamSetFormat(HANDLE(hCamera), pLUCAM_FRAME_FORMAT(frameFormat), C.c_float(frameRate))
        return success
            
    def TakeVideo(self, hCamera, numFrames, buffer):
        success = self.lib.LucamTakeVideo(HANDLE(hCamera), C.c_long(numFrames), pUBYTE(buffer))
        return success
        
    def TakeVideoEx(self, hCamera, buffer, pLength, timeout):
        success = self.lib.LucamTakeVideoEx(HANDLE(hCamera), pUBYTE(buffer), pULONG(C.c_ulong(pLength)), C.c_ulong(timeout))
        return success

    def CancelTakeVideo(self, hCamera):
        success = self.lib.LucamCancelTakeVideo(HANDLE(hCamera))
        return success
        
    def TakeSnapshot(self, hCamera, snapshotSettings, buffer):
        success = self.lib.LucamTakeSnapshot(HANDLE(hCamera), pLUCAM_SNAPSHOT(snapshotSettings), pUBYTE(buffer))
        return success
    
    def EnableFastFrames(self, hCamera, snapshotSettings):
        success = self.lib.LucamEnableFastFrames(HANDLE(hCamera), pLUCAM_SNAPSHOT(snapshotSettings))
        return success

    def DisableFastFrames(self, hCamera):
        success = self.lib.LucamDisableFastFrames(HANDLE(hCamera))
        return success

    def TakeFastFrame(self, hCamera, buffer):
        success = self.lib.LucamTakeFastFrame(HANDLE(hCamera), pUBYTE(buffer))
        return success

    def TakeFastFrameNoTrigger(self, hCamera, buffer):
        success = self.lib.LucamTakeFastFrameNoTrigger(HANDLE(hCamera), pUBYTE(buffer))
        return success

    def ForceTakeFastFrame(self, hCamera, buffer):
        success = self.lib.LucamForceTakeFastFrame(HANDLE(hCamera), pUBYTE(buffer))
        return success

    def TriggerFastFrame(self, hCamera):
        success = self.lib.LucamTriggerFastFrame(HANDLE(hCamera))
        return success

    def SetTriggerMode(self, hCamera, useHwTrigger):
        success = self.lib.LucamSetTriggerMode(HANDLE(hCamera), BOOL(useHwTrigger))
        return success

    def CancelTakeFastFrame(self, hCamera):
        success = self.lib.LucamCancelTakeFastFrame(HANDLE(hCamera))
        return success

    def EnableSynchronousSnapshots(self, numCameras, handles, snapshotSettings):
        success = self.lib.LucamEnableSynchronousSnapshots(C.c_ulong(numCameras), pHANDLE(handles), C.POINTER(pLUCAM_SNAPSHOT)(snapshotSettings))
        return success
    
    def TakeSynchronousSnapshots(self, syncHandle, ppBuffers):
        success = self.lib.LucamTakeSynchronousSnapshots(HANDLE(syncHandle), C.POINTER(pUBYTE)(ppBuffers))
        return success
    
    def DisableSynchronousSnapshots(self, syncHandle):
        success = self.lib.LucamDisableSynchronousSnapshots(HANDLE(syncHandle))
        return success
    
    def ConvertFrameToRgb24(self, hCamera, dstBuffer, srcBuffer, imageWidth, imageHeight, pixelFormat, conversionParams):
        success = self.lib.LucamConvertFrameToRgb24(HANDLE(hCamera), pUBYTE(dstBuffer), pUBYTE(srcBuffer), 
                                                    imageWidth, imageHeight, pixelFormat, pLUCAM_CONVERSION(conversionParams))
        return success

    def ConvertFrameToRgb32(self, hCamera, dstBuffer, srcBuffer, imageWidth, imageHeight, pixelFormat, conversionParams):
        success = self.lib.LucamConvertFrameToRgb32(HANDLE(hCamera), pUBYTE(dstBuffer), pUBYTE(srcBuffer), 
                                                    imageWidth, imageHeight, pixelFormat, pLUCAM_CONVERSION(conversionParams))
        return success

    def ConvertFrameToRgb48(self, hCamera, dstBuffer, srcBuffer, imageWidth, imageHeight, pixelFormat, conversionParams):
        success = self.lib.LucamConvertFrameToRgb48(HANDLE(hCamera), pUSHORT(dstBuffer), pUSHORT(srcBuffer), 
                                                    imageWidth, imageHeight, pixelFormat, pLUCAM_CONVERSION(conversionParams))
        return success

    def ConvertFrameToGreyscale8(self, hCamera, dstBuffer, srcBuffer, imageWidth, imageHeight, pixelFormat, conversionParams):
        success = self.lib.LucamConvertFrameToGreyscale8(HANDLE(hCamera), pUBYTE(dstBuffer), pUBYTE(srcBuffer), 
                                                         imageWidth, imageHeight, pixelFormat, pLUCAM_CONVERSION(conversionParams))
        return success

    def ConvertFrameToGreyscale16(self, hCamera, dstBuffer, srcBuffer, imageWidth, imageHeight, pixelFormat, conversionParams):
        success = self.lib.LucamConvertFrameToGreyscale16(HANDLE(hCamera), pUSHORT(dstBuffer), pUSHORT(srcBuffer), 
                                                          imageWidth, imageHeight, pixelFormat, pLUCAM_CONVERSION(conversionParams))
        return success

    def ConvertFrameToRgb24Ex(self, hCamera, dstBuffer, srcBuffer, imageFormat, lucamConversionParams):
        success = self.lib.LucamConvertFrameToRgb24Ex(HANDLE(hCamera), pUBYTE(dstBuffer), pUBYTE(srcBuffer), 
                                                      pLUCAM_IMAGE_FORMAT(imageFormat),
                                                      pLUCAM_CONVERSION_PARAMS(lucamConversionParams))
        return success

    def ConvertFrameToRgb32Ex(self, hCamera, dstBuffer, srcBuffer, imageFormat, lucamConversionParams):
        success = self.lib.LucamConvertFrameToRgb32Ex(HANDLE(hCamera), pUBYTE(dstBuffer), pUBYTE(srcBuffer), 
                                                      pLUCAM_IMAGE_FORMAT(imageFormat), 
                                                      pLUCAM_CONVERSION_PARAMS(lucamConversionParams))
        return success

    def ConvertFrameToRgb48Ex(self, hCamera, dstBuffer, srcBuffer, imageFormat, lucamConversionParams):
        success = self.lib.LucamConvertFrameToRgb48Ex(HANDLE(hCamera), pUSHORT(dstBuffer), pUSHORT(srcBuffer), 
                                                      pLUCAM_IMAGE_FORMAT(imageFormat), 
                                                      pLUCAM_CONVERSION_PARAMS(lucamConversionParams))
        return success

    def ConvertFrameToGreyscale8Ex(self, hCamera, dstBuffer, srcBuffer, imageFormat, lucamConversionParams):
        success = self.lib.LucamConvertFrameToGreyscale8Ex(HANDLE(hCamera), pUBYTE(dstBuffer), pUBYTE(srcBuffer), 
                                                           pLUCAM_IMAGE_FORMAT(imageFormat), 
                                                           pLUCAM_CONVERSION_PARAMS(lucamConversionParams))
        return success

    def ConvertFrameToGreyscale16Ex(self, hCamera, dstBuffer, srcBuffer, imageFormat, lucamConversionParams):
        success = self.lib.LucamConvertFrameToGreyscale16Ex(HANDLE(hCamera), pUSHORT(dstBuffer), pUSHORT(srcBuffer), 
                                                            pLUCAM_IMAGE_FORMAT(imageFormat), 
                                                            pLUCAM_CONVERSION_PARAMS(lucamConversionParams))
        return success

    def GetImageIntensity(self, hCamera, image, imageFormat, startX, startY, width, height):
        """ There are 3 ways to call this:
        GetImageIntensity w/ image = NULL, imageFormat = NULL -> with the settings you have, tell me what the next frame looks like
        GetImageIntensity w/ image = DATA, imageFormat = NULL -> with the settings you have, tell me what the DATA frame looks like
        GetImageIntensity w/ image = DATA, imageFormat = INFO -> using the INFO settings, tell me what the DATA frame looks like
        """
        pInt = C.c_float(0)
        pRed = C.c_float(0)
        pGreen1 = C.c_float(0)
        pGreen2 = C.c_float(0)
        pBlue = C.c_float(0)
        if image is None:
            im = image
        else:
            im = C.cast(pUBYTE(image),C.POINTER(C.c_void_p))
        if imageFormat is None:
            imf = imageFormat
        else:
            imf = C.cast(pLUCAM_IMAGE_FORMAT(imageFormat),C.POINTER(C.c_void_p))
        success = self.lib.LucamGetImageIntensity(HANDLE(hCamera), im, imf,
                                                         C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height),
                                                         pFLOAT(pInt), 
                                                         pFLOAT(pRed), 
                                                         pFLOAT(pGreen1), 
                                                         pFLOAT(pGreen2), 
                                                         pFLOAT(pBlue))
        return (success, pInt.value, pRed.value, pGreen1.value, pGreen2.value, pBlue.value)

    def SaveImage(self, imageWidth, imageHeight, pixelFormat, buffer, fileName):
        success = self.lib.LucamSaveImage(imageWidth, imageHeight, pixelFormat, pUBYTE(buffer), C.c_char_p(fileName))
        return success

    def SaveImageEx(self, hCamera, imageWidth, imageHeight, pixelFormat, buffer, fileName):
        success = self.lib.LucamSaveImageEx(HANDLE(hCamera), imageWidth, imageHeight, pixelFormat, pUBYTE(buffer), C.c_char_p(fileName))
        return success
        
    def SaveImageW(self, imageWidth, imageHeight, pixelFormat, buffer, fileName):
        success = self.lib.LucamSaveImageW(imageWidth, imageHeight, pixelFormat, pUBYTE(buffer), C.c_wchar_p(fileName))
        return success

    def SaveImageWEx(self, hCamera, imageWidth, imageHeight, pixelFormat, buffer, fileName):
        success = self.lib.LucamSaveImageWEx(HANDLE(hCamera), imageWidth, imageHeight, pixelFormat, pUBYTE(buffer), C.c_wchar_p(fileName))
        return success
        
    def GetLastError(self):
        return self.lib.LucamGetLastError()
        
    def GetLastErrorForCamera(self, hCamera):
        return self.lib.LucamGetLastErrorForCamera(HANDLE(hCamera))

    def DisplayPropertyPage(self, hCamera, hWnd):
        return self.lib.LucamDisplayPropertyPage(HANDLE(hCamera), HWND(hWnd))

    def DisplayVideoFormatPage(self, hCamera, hWnd):
        return self.lib.LucamDisplayVideoFormatPage(HANDLE(hCamera), HWND(hWnd))

    def QueryVersion(self, hCamera):
        versionInfo = LUCAM_VERSION()
        success = self.lib.LucamQueryVersion(HANDLE(hCamera), pLUCAM_VERSION(versionInfo))
        return (success, versionInfo)
        
    def QueryExternInterface(self, hCamera):
        interfaceType = C.c_ulong(0)
        success = self.lib.LucamQueryExternInterface(HANDLE(hCamera), pULONG(interfaceType))
        return (success, interfaceType.value)
        
    def GetCameraId(self, hCamera):
        cameraId = C.c_ulong(0)
        success = self.lib.LucamGetCameraId(HANDLE(hCamera), pULONG(cameraId))
        return (success, cameraId.value)
        
    def GetHardwareRevision(self, hCamera):
        hardwareRevision = C.c_ulong(0)
        success = self.lib.LucamGetHardwareRevision(HANDLE(hCamera), pULONG(hardwareRevision))
        return (success, hardwareRevision.value)

    def CreateDisplayWindow(self, hCamera, title, style, x, y, width, height, hParentId, hChildId):
        print("CreateDisplayWindow:hCamera = {0}, title='{1}', x={2}, y={3}, width={4}, height={5}, hParentId={6}, hChildId={7}".format(hCamera, title, x, y, width, height, hParentId, hChildId))
        success = self.lib.LucamCreateDisplayWindow(HANDLE(hCamera), C.c_char_p(title), DWORD(style), C.c_int(x), C.c_int(y), C.c_int(width), C.c_int(height), HWND(hParentId), HMENU(hChildId))
        return success

    def AdjustDisplayWindow(self, hCamera, title, x, y, width, height):
        #print "hCamera = {0}, title='{1}', x={2}, y={3}, width={4}, height={5}".format(hCamera, title, x, y, width, height)
        success = self.lib.LucamAdjustDisplayWindow(HANDLE(hCamera), C.c_char_p(title), C.c_int(x), C.c_int(y), C.c_int(width), C.c_int(height))
        return success
                
    def QueryDisplayFrameRate(self, hCamera):
        frameRate = C.c_float(0.0)
        success = self.lib.LucamQueryDisplayFrameRate(HANDLE(hCamera), pFLOAT(frameRate))
        return (success, frameRate)

    def DestroyDisplayWindow(self, hCamera):
        success = self.lib.LucamDestroyDisplayWindow(HANDLE(hCamera))
        return success

    def GpioRead(self, hCamera):
        outputBits = C.c_uint8(0)
        inputBits  = C.c_uint8(0)
        success = self.lib.LucamGpioRead(HANDLE(hCamera), C.POINTER(C.c_uint8)(outputBits), C.POINTER(C.c_uint8)(inputBits))
        return (success, outputBits, inputBits)
        
    def GpioWrite(self, hCamera, outputBits):
        success = self.lib.LucamGpioWrite(HANDLE(hCamera), C.c_uint8(outputBits))
        return success
    
    def GpoSelect(self, hCamera, enableBits):
        success = self.lib.LucamGpoSelect(HANDLE(hCamera), C.c_uint8(enableBits))
        return success

    #// For Lm and Lt cameras only
    def GpioConfigure(self, hCamera, configureBits):
        success = self.lib.LucamGpioConfigure(HANDLE(hCamera), C.c_uint8(configureBits))
        return success

    def EnumAvailableFrameRates(self, hCamera, count):
        if 0 == count:
            temp = C.c_float(0.0)
            result = self.lib.LucamEnumAvailableFrameRates(HANDLE(hCamera), C.c_ulong(0), pFLOAT(temp))
            return (result, ())
        
        frameRateArray = (C.c_float  * count)()
        result = self.lib.LucamEnumAvailableFrameRates(HANDLE(hCamera), C.c_ulong(count), pFLOAT(frameRateArray))
        return (result, frameRateArray)

    def GetTruePixelDepth(self, hCamera):
        truePixelDepth = C.c_ulong(0)
        success = self.lib.LucamGetTruePixelDepth(HANDLE(hCamera), pULONG(truePixelDepth) )
        return (success, truePixelDepth.value)

    def ReadRegister(self, hCamera, baseAddress, numRegs):
        """ Read a set of register values, starting at baseAddress """
        registerArray = (C.c_ulong * numRegs)()
        success = self.lib.LucamReadRegister(HANDLE(hCamera), C.c_ulong(baseAddress), C.c_ulong(numRegs), pULONG(registerArray) )
        return (success, registerArray)
        
    def WriteRegister(self, hCamera, baseAddress, registers):
        """ Write the array of values to the registers, starting at baseAddress """
        print ('WriteRegister does nothing')
        #lib.LucamWriteRegister.argtypes = [ HANDLE, C.c_ulong, C.c_ulong, C.POINTER(C.c_ulong) ]
        #lib.LucamWriteRegister.restype = BOOL
        pass

    def PermBufferRead(self, hCamera, offset=0, length=1):
        bufArray = (C.c_ubyte * length)()
        success = self.lib.LucamPermanentBufferRead(HANDLE(hCamera), pUBYTE(bufArray), C.c_ulong(offset), C.c_ulong(length))
        return (success, bufArray)

    def PermBufferWrite(self, hCamera, bufArray, offset=0):
        buflen = len(bufArray)
        buf = (C.c_ubyte*buflen)(*list(bytearray(bufArray)))
        success = self.lib.LucamPermanentBufferWrite(HANDLE(hCamera), buf, C.c_ulong(offset), C.c_ulong(buflen))
        return success

    def SetupCustomMatrix(self, hCamera, matrixValues):
        success = self.lib.LucamSetupCustomMatrix(HANDLE(hCamera), pFLOAT(matrixValues))
        return success

    def GetCurrentMatrix(self, hCamera):
        matrixArray = (C.c_float * 9)()
        success = self.lib.LucamGetCurrentMatrix(HANDLE(hCamera), pFLOAT(matrixArray))
        return (success, matrixArray)
        
    def OneShotAutoExposure(self, hCamera, target, startX, startY, width, height):
        success = self.lib.LucamOneShotAutoExposure(HANDLE(hCamera), C.c_uint(target), 
                                                    C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def OneShotAutoExposureEx(self, hCamera, target, startX, startY, width, height, lightingPeriod):
        # float lightingPeriod /* milliseconds, should be 8.333 in North America*/);
        success = self.lib.LucamOneShotAutoExposureEx(HANDLE(hCamera), C.c_uint(target), 
                                                      C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height), 
                                                      C.c_float(lightingPeriod))
        return success

    def OneShotAutoGain(self, hCamera, target, startX, startY, width, height):
        success = self.lib.LucamOneShotAutoGain(HANDLE(hCamera), C.c_uint(target), 
                                                C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def OneShotAutoIris(self, hCamera, target, startX, startY, width, height):
        success = self.lib.LucamOneShotAutoIris(HANDLE(hCamera), C.c_uint(target), 
                                                       C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def OneShotAutoWhiteBalance(self, hCamera, startX, startY, width, height):
        success = self.lib.LucamOneShotAutoWhiteBalance(HANDLE(hCamera), C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def OneShotAutoWhiteBalanceEx(self, hCamera, redOverGreen, blueOverGreen, startX, startY, width, height):
        success = self.lib.LucamOneShotAutoWhiteBalanceEx(HANDLE(hCamera), C.c_float(redOverGreen), C.c_float(blueOverGreen), 
                                                          C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def DigitalWhiteBalance(self, hCamera, startX, startY, width, height):
        success = self.lib.LucamDigitalWhiteBalance(HANDLE(hCamera), C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def DigitalWhiteBalanceEx(self, hCamera, redOverGreen, blueOverGreen, startX, startY, width, height):
        success = self.lib.LucamDigitalWhiteBalanceEx(HANDLE(hCamera), C.c_float(redOverGreen), C.c_float(blueOverGreen), 
                                                      C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def AdjustWhiteBalanceFromSnapshot(self, hCamera, snapshotSettings, buffer, redOverGreen, blueOverGreen, startX, startY, width, height):
        success = self.lib.LucamAdjustWhiteBalanceFromSnapshot(HANDLE(hCamera), 
                                                               pLUCAM_SNAPSHOT(snapshotSettings), pUBYTE(buffer), 
                                                               C.c_float(redOverGreen), C.c_float(blueOverGreen), 
                                                               C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height))
        return success

    def ContinuousAutoExposureEnable(self, hCamera, target, startX, startY, width, height, lightingPeriod):
        # float lightingPeriod /* milliseconds, should be 8.333 in North America*/);
        success = self.lib.LucamContinuousAutoExposureEnable(HANDLE(hCamera), C.c_uint(target), 
                                                             C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height), 
                                                             C.c_float(lightingPeriod))
        return success

    def ContinuousAutoExposureDisable(self, hCamera):
        success = self.lib.LucamContinuousAutoExposureDisable(HANDLE(hCamera))
        return success

    def PerformDualTapCorrection(self, hCamera, data, imageFormat):
        success = self.lib.LucamPerformDualTapCorrection(HANDLE(hCamera), pUBYTE(data), pLUCAM_IMAGE_FORMAT(imageFormat))
        return success

    def PerformMultiTapCorrection(self, hCamera, data, imageFormat):
        success = self.lib.LucamPerformMultiTapCorrection(HANDLE(hCamera), pUBYTE(data), pLUCAM_IMAGE_FORMAT(imageFormat))
        return success

    def PerformMonoGridCorrection(self, hCamera, data, imageFormat):
        success = self.lib.LucamPerformMonoGridCorrection(HANDLE(hCamera), pUBYTE(data), pLUCAM_IMAGE_FORMAT(imageFormat))
        return success

    def InitAutoLens(self, hCamera, force):
        success = self.lib.LucamInitAutoLens(HANDLE(hCamera), BOOL(force))
        return success

    def AutoFocusStart(self, hCamera, startX, startY, width, height, _callback):
        putZeroThere1 = 0.0
        putZeroThere2 = 0x8000 # use 0x8000 in putZerothere2 to disable update in focus range, from Autolens
        putZeroThere3 = 0.0
        success = self.lib.LucamAutoFocusStart(HANDLE(hCamera), 
                                               C.c_ulong(startX), C.c_ulong(startY), C.c_ulong(width), C.c_ulong(height), 
                                               C.c_float(putZeroThere1), C.c_float(putZeroThere2), C.c_float(putZeroThere3),
                                               _callback , None)
        return success
    def AutoFocusWait(self, hCamera, timeout):
        success = self.lib.LucamAutoFocusWait(HANDLE(hCamera), C.c_ulong(timeout))
        return success

    def AutoFocusStop(self, hCamera):
        success = self.lib.LucamAutoFocusStop(HANDLE(hCamera))
        return success

    def AutoFocusQueryProgress(self, hCamera):
        progress = C.c_float(0.0)
        success = self.lib.LucamAutoFocusQueryProgress(HANDLE(hCamera), pFLOAT(progress))
        return (success, progress.value)

    def DataLsbAlign(self, hCamera, imageFormat, data):
        # does the bit shift for you.
        # Little Endian data remains Little Endian
        success = self.lib.LucamDataLsbAlign(HANDLE(hCamera), pLUCAM_IMAGE_FORMAT(imageFormat), pUBYTE(data))
        return success

    def AutoRoiGet(self, hCamera):
        startX = C.c_long(0)
        startY = C.c_long(0)
        width = C.c_long(0)
        height = C.c_long(0)
        rv = self.lib.LucamAutoRoiGet(HANDLE(hCamera), pLONG(startX), pLONG(startY), pLONG(width), pLONG(height))
        if (0 == rv):
            return (False, 0, 0, 0, 0)
        return (True, startX, startY, width, height)

    def AutoRoiSet(self, hCamera, startX, startY, width, height):
        success = self.lib.LucamAutoRoiSet(HANDLE(hCamera), C.c_long(startX), C.c_long(startY), C.c_long(width), C.c_long(height))
        return success

    def Setup8bitsLUT(self, hCamera, LUT, length):
        pLut = (C.c_ubyte * len(LUT))(*list(bytearray(LUT)))
        success = self.lib.LucamSetup8bitsLUT(HANDLE(hCamera), pLut, C.c_ulong(length))
        return success

    def Setup8bitsColorLUT(self, hCamera, LUT, length, applyOnRed, applyOnGreen1, applyOnGreen2, applyOnBlue):
        pLut = (C.c_ubyte * len(LUT))(*list(bytearray(LUT)))
        success = self.lib.LucamSetup8bitsColorLUT(HANDLE(hCamera), pLut, C.c_ulong(length), 
                                                   BOOL(applyOnRed), BOOL(applyOnGreen1), BOOL(applyOnGreen2), BOOL(applyOnBlue))
        return success

    def SetTimeout(self, hCamera, forStills, timeout):
        success = self.lib.LucamSetTimeout(HANDLE(hCamera), BOOL(forStills), C.c_float(timeout))
        return success

    def EnableInterfacePowerSpecViolation(self, hCamera, enable):
        success = self.lib.LucamEnableInterfacePowerSpecViolation(HANDLE(hCamera), BOOL(enable))
        return success

    def IsInterfacePowerSpecViolationEnabled(self, hCamera):
        pIsEnabled = BOOL(False)
        success = self.lib.LucamIsInterfacePowerSpecViolationEnabled(HANDLE(hCamera), pBOOL(pIsEnabled))
        return (success, pIsEnabled.value)

    def GetTimestampFrequency(self, hCamera):
        timestampFrequency = C.c_ulonglong(0)
        success = self.lib.LucamGetTimestampFrequency(HANDLE(hCamera), pULONGLONG(timestampFrequency))
        return (success, timestampFrequency.value)

    def GetTimestamp(self, hCamera):
        timestamp = C.c_ulonglong(0)
        success = self.lib.LucamGetTimestamp(HANDLE(hCamera), pULONGLONG(timestamp))
        return (success, timestamp.value)

    def SetTimestamp(self, hCamera, timestamp):
        success = self.lib.LucamSetTimestamp(HANDLE(hCamera), C.c_ulonglong(timestamp))
        return success

    def EnableTimestamp(self, hCamera, enable):
        success = self.lib.LucamEnableTimestamp(HANDLE(hCamera), BOOL(enable))
        return success

    def IsTimestampEnabled(self, hCamera):
        isEnabled = BOOL(False)
        success = self.lib.LucamIsTimestampEnabled(HANDLE(hCamera), pBOOL(isEnabled))
        return (success, isEnabled.value)

    def GetMetadata(self, hCamera, imageBuffer, imageFormat, metaDataIndex):
        timestamp = C.c_ulonglong(0)
        success = self.lib.LucamGetMetadata(HANDLE(hCamera), 
                                            pBYTE(imageBuffer), 
                                            pLUCAM_IMAGE_FORMAT(imageFormat), 
                                            C.c_ulong(metaDataIndex), 
                                            pULONGLONG(timestamp))
        return (success, timestamp.value)


class ApiError(Exception):
    def __init__(self, errorCode, hCamera = None):
        Exception.__init__(self, GetApiErrorDescription(errorCode))
        self.errorCode = errorCode
        self.hCamera = hCamera
    
    def __str__(self):
        return "{0} ({1}), hCamera=0x{2:08X}".format(GetApiErrorDescription(self.errorCode), self.errorCode, self.hCamera)
        
    def __repr__(self):
        return self.__str__()
        

#//
#// More pythonic wrapper around the low level class
#// We also check for errors, and raise exceptions as required
#//     
class Api:
    def __init__(self):
        self.lib = DynamicLibrary()
        
    def __str__(self):
        return str(self.lib)

    def SelectInterface(self, interface):
        rv = self.lib.SelectExternInterface(interface)
        if False == rv:
            raise ApiError(self.LastError())

    def NumCameras(self):
        return self.lib.NumCameras()

    def EnumCameras(self):
        return self.lib.EnumCameras()[1]
        
    def GetCameraIndex(self, serialNumber, cameraList = None):
        """ Given a list of cameras (returned by EnumCameras), determine the index
        in the list of the camera with the given serial number.
        If the cameraList is not specified, EnumCameras will be called
        -1 is returned on failure """
        if cameraList is None:
            cameraList = self.EnumCameras()

        cameraIndex = -2 #// Because we might add 1 later
        for index, camera in enumerate(cameraList):
            if serialNumber == camera.serialnumber:
                cameraIndex = index
                break
        #// The index expected by CameraOpen is 1-based, not 0-based
        return cameraIndex + 1

    def CameraOpen(self, cameraId = 1):
        """ If you pass in a camera id less than or equal to 100, we assume it's a camera index.
        If you pass in an id greater than 100, we assume it's a 
        serial number, and will look up the camera index for you """

        if cameraId > 100:
            cameraId = self.GetCameraIndex(cameraId)

        hCamera = self.lib.CameraOpen(cameraId)
        if (None == hCamera):
            raise ApiError(self.LastError())
        return hCamera
        
    def CameraClose(self, hCamera):
        success = self.lib.CameraClose(hCamera)
        if (0 == success):
            raise ApiError(self.LastError())

    #// This must not raise an exception
    def LastError(self):
        return self.lib.GetLastError()
    
    def EnableSyncSnaps(self, handleList, snapshotSettingList):
        if platform.system() == 'Windows':
            assert len(handleList) == len(snapshotSettingList)
            numCameras = len(handleList)
            handles = (HANDLE * numCameras)()
            settings = (C.POINTER(LUCAM_SNAPSHOT) * numCameras)()
            for i in range(numCameras):
                handles[i] = handleList[i]
                settings[i] = C.POINTER(LUCAM_SNAPSHOT)(snapshotSettingList[i])
            syncHandle = self.lib.EnableSynchronousSnapshots(numCameras, handles, settings)
            if (0 == syncHandle):
                raise ApiError(self.LastError())
            return syncHandle
    
    def TakeSyncSnaps(self, syncHandle, handleList):
        if platform.system() == 'Windows':
            bufList = []
            numCameras = len(handleList)
            pBuf = (C.POINTER(C.c_ubyte) * numCameras)()
            for i in range(numCameras):
                (success, imageFormat) = self.lib.GetStillImageFormat(handleList[i])
                bufferSize = GetPixelSize(imageFormat.pixelFormat) * imageFormat.imageSize
                buf = (C.c_ubyte * bufferSize)()
                bufList.append(buf)
                pBuf[i] = C.POINTER(C.c_ubyte)(buf)
            success = self.lib.TakeSynchronousSnapshots(syncHandle, pBuf)
            if (0 == success):
                raise ApiError(self.LastError())
            return bufList
    
    def DisableSyncSnaps(self, syncHandle):
        if platform.system() == 'Windows':
            success = self.lib.DisableSynchronousSnapshots(syncHandle)
            if (0 == success):
                raise ApiError(self.LastError())
            return success
        
if platform.system() == 'Windows':
    SupportedFileExtensions = ("bmp", "jpg", "tif")
else:
    SupportedFileExtensions = ("bmp", "tif")
    
