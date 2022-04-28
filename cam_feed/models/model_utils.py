from skimage import measure
import numpy as np

def centroid(image):
    m = measure.moments(image)
    return m[1,0]/m[0,0], m[0,1]/m[0,0]

def gaussian2d_array(mean, var, size = (1000, 1000)):
    x, y = np.meshgrid(np.arange(0,size[0],1),np.arange(0,size[1],1), indexing='ij')
    return (1. / np.sqrt(2 * np.pi * var)) * np.exp(-((x-mean[0])**2 + (y-mean[1])**2) / (2 * var)) 

def to_uint8(image):
    m = np.max(image)
    if m == 0: return image
    else:
        image = 255 * (image/m)
        image = image.astype(np.uint8)
        return image