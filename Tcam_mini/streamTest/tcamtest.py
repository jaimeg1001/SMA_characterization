from tcam import TCam
from time import sleep
from PIL import Image
import base64
from array import array
import numpy as np


def convert(img):

    dimg = base64.b64decode(img["radiometric"])
    ra = array('H', dimg)
    imgmin = 65535
    imgmax = 0
    for i in ra:
        if i < imgmin:
            imgmin = i
        if i > imgmax:
            imgmax = i
    delta = imgmax - imgmin
    a = np.zeros((120,160,3), np.uint8)
    for r in range(0, 120):
        for c in range(0, 160):
            val = int((ra[(r * 160) + c] - imgmin) * 255 / delta)
            if val > 255:
                a[r, c] = [255, 255, 255]
            else:
                a[r, c] = [val, val, val]
    return a

########### Main Program ############

if __name__ == '__main__':
    ip = "192.168.11.143"
    tcam = TCam()
    tcam.connect(ip)
    frame = tcam.get_frame()
    tcam.start_stream()
    try:
        while True:
            if tcam.frame_count() != 0:
                print("Hay imagenes")
                frame = tcam.get_frame()
                img = convert(frame)
            else:
                sleep(0.01)
            print("Frames en cola: ",tcam.frame_count())
    except KeyboardInterrupt:
        print("Exception")
        tcam.shutdown()