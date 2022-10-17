"""
    Utility functions for some image processing used in alignment 
"""

import numpy as np
from scipy import ndimage

def centroid(image):
    m00 = np.sum(image)
    m10, m01 = np.arange(0,image.shape[0],1) * np.sum(image, axis=1), np.arange(0,image.shape[1],1) * np.sum(image, axis=0)
    m10, m01 = np.sum(m10), np.sum(m01)
    return int(m10/m00), int(m01/m00)

def gaussian2d_array(mean, var, size = (1000, 1000)):
    x, y = np.meshgrid(np.arange(0,size[0],1),np.arange(0,size[1],1), indexing='ij')
    return (1. / np.sqrt(2 * np.pi * var)) * np.exp(-((x-mean[0])**2 + (y-mean[1])**2) / (2 * var)) 

def circle2d_array(center, radius, size=(1000,1000)):
    x, y = np.meshgrid(np.arange(0,size[0],1),np.arange(0,size[1],1), indexing='ij')
    return 1 * ((x - center[0])**2 + (y - center[1])**2 <= radius**2)

def to_uint8(image):
    m = np.max(image)
    if m == 0: return image
    else:
        image = 255 * (image/m)
        image = image.astype(np.uint8)
        return image

def image_convolution(image, kernel=np.ones((5,5))):
    convolution = ndimage.convolve(image, kernel, mode='reflect')
    return convolution    