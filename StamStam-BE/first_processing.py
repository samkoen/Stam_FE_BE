
import cv2
import numpy as np
import imutils









from collections import namedtuple
BLevel = namedtuple("BLevel", ['brange', 'bval'])

#all possible levels
_blevels = [
    BLevel(brange=range(0, 24), bval=0),
    BLevel(brange=range(23, 47), bval=1),
    BLevel(brange=range(46, 70), bval=2),
    BLevel(brange=range(69, 93), bval=3),
    BLevel(brange=range(92, 116), bval=4),
    BLevel(brange=range(115, 140), bval=5),
    BLevel(brange=range(139, 163), bval=6),
    BLevel(brange=range(162, 186), bval=7),
    BLevel(brange=range(185, 209), bval=8),
    BLevel(brange=range(208, 232), bval=9),
    BLevel(brange=range(231, 256), bval=10),
]


def detect_level(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    _, _, v = cv2.split(hsv)
    h_val = int(np.average(v.flatten()))

    for blevel in _blevels:
       if h_val in blevel.brange:
           return blevel.bval
    raise ValueError("Brightness Level Out of Range")

def increase_brightness(img, value=30):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)

    lim = 255 - value
    v[v > lim] = 255
    v[v <= lim] += value

    final_hsv = cv2.merge((h, s, v))
    img = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)
    return img






def resize(img):
    print('Original Dimensions : ', img.shape)
    scale_percent = 850/img.shape[0]
    width = int(img.shape[1] * scale_percent)
    height = int(img.shape[0] * scale_percent)
    dim = (width, height)
    resized = cv2.resize(img, dim, interpolation=cv2.INTER_AREA)
    print('reaized : ', resized.shape)
    #cv2.imshow('mask2', resized)
    #cv2.waitKey(0)
    #cv2.destroyAllWindows()

    return resized


def adjust_gamma(image, gamma=1.0):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** invGamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")

    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)


def get_contour(frame,erose=False,dilate=False,gshow=False,name=None):

    # cv2.namedWindow("original", cv2.WINDOW_NORMAL)
    # cv2.imshow("original",frame)
    #
    # cv2.threshold(frame,0,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C);
    # cv2.namedWindow("tresh", cv2.WINDOW_NORMAL)
    # cv2.imshow("tresh", frame)
    # cv2.waitKey(0)
    #


    level = detect_level(frame)
    if level<=5:
        #frame = increase_brightness(frame)
        frame = adjust_gamma(frame,1.3)
    elif level>=8:
        frame = adjust_gamma(frame, 0.7)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)




    lower_black = np.array([-20, -20, -50])
    upper_black = np.array([190, 280, 90])
    # Threshold the HSV image to get only black colors
    mask = cv2.inRange(hsv, lower_black, upper_black)

    res = cv2.bitwise_and(frame, frame, mask=mask)
    if erose:
        kernel = np.ones((3, 3), np.uint8)
        erosion = cv2.erode(mask, kernel, iterations=2)
    elif dilate:
        kernel = np.ones((3, 3), np.uint8)
        erosion = cv2.dilate(mask, kernel, iterations=2)
    else:
        erosion = mask

    #cv2.imshow("erosion", erosion)
    #cv2.waitKey(0)
    # dilation = cv2.dilate(mask, kernel, iterations=1)
    # cv2.imshow("dilation", dilation)
    # cv2.waitKey(0)
    #cv2.imshow('frame', frame)
    #cv2.imshow('mask', mask)
    #cv2.imshow('res', res)
    if imutils.is_cv2() or imutils.is_cv4():
        contours, hierarchy = cv2.findContours(erosion.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    elif imutils.is_cv3():
        aaa, contours, hierarchy = cv2.findContours(erosion.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    #print('len: ', len(contours))
    mask = np.zeros(frame.shape, dtype=np.uint8)

    win_name = "rects_{}".format(name)
    if gshow:
        #cv2.namedWindow("mask2", cv2.WINDOW_NORMAL)
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    final_countours=[]
    for idx in range(len(contours)):
        x, y, w, h = cv2.boundingRect(contours[idx])
        mask[y:y + h, x:x + w] = 0
        cv2.drawContours(mask, contours, idx, (255, 255, 255), -1)
        # r = float(cv2.countNonZero(mask[y:y + h, x:x + w])) / (w * h)

        if w > 5 and h > 8 and w < 1000:
            #print("width: {} - hight {}". format(w, h))
            cv2.rectangle(frame, (x, y), (x + w - 1, y + h - 1), (0, 255, 0), 2)
            final_countours.append(contours[idx])

            #cv2.imshow('rects', frame)
            #cv2.imshow('mask2', mask)
            #cv2.waitKey(0)

    if gshow:
        #cv2.imshow('mask2', mask)
        cv2.imshow(win_name, frame)
        #cv2.imwrite('rects2.png', frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return final_countours
