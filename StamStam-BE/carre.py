# GenData.py

import sys
import numpy as np
import cv2
import os
import itertools

# module level variables ##########################################################################
MIN_CONTOUR_AREA = 50

RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30

###################################################################################################

def union(a, b):
    x = min(a[0], b[0])
    y = min(a[1], b[1])
    w = max(a[0] + a[2], b[0] + b[2]) - x
    h = max(a[1] + a[3], b[1] + b[3]) - y
    return (x, y, w, h)


def intersection(a, b):
    x = max(a[0], b[0])
    y = max(a[1], b[1])
    w = min(a[0] + a[2], b[0] + b[2]) - x
    h = min(a[1] + a[3], b[1] + b[3]) - y
    if w < 0 or h < 0: return ()  # or (0,0,0,0) ?
    return (x, y, w, h)

def is_kouf(a,b):
    if a[1] > b[1]:
        bas = a
        haut = b
    else:
        bas = b
        haut = a

    # dans le bas, la hauteur est plus grande que la largeur
    if bas[3] < bas[2]:
        return False

    if bas[1]+bas[3] < haut[1] + haut[3]:
        return False


    r_l = haut[2] / bas[2]
    r_h = haut[3] / bas[3]
    if 1.5 < r_l < 6 and 0.6 < r_h < 2.2:
        ratio_inter_haut = (bas[0] + bas[2] - haut[0]) / haut[2]
        ratio_inter_bas = (bas[0] + bas[2] - haut[0]) / bas[2]

        ratio_inter_haut_h=(haut[1] + haut[3] - bas[1]) / haut[3]
        ratio_inter_bas_h=(haut[1] + haut[3] - bas[1]) / bas[3]


        if 0.1 < ratio_inter_haut < 0.8 and 0.7 < ratio_inter_bas < 1.9  and 0.1 < ratio_inter_haut_h < 0.7 and 0.2 < ratio_inter_bas_h < 1:
            return True
        else:
            pass
    return False

def my_sort_2(myContours):
    max_width = max(myContours, key=lambda r: r[0] + r[2])[0]
    max_height = max(myContours, key=lambda r: r[3])[3]
    nearest = max_height * 1.1
    myContours.sort(key=lambda r: (int(nearest * round(float(r[1]) / nearest)) * max_width + r[0]))


    # contours = list(c)
    #
    # # Example - contours = [(287, 117, 13, 46), (102, 117, 34, 47), (513, 116, 36, 49), (454, 116, 32, 49), (395, 116, 28, 48), (334, 116, 31, 49), (168, 116, 26, 49), (43, 116, 30, 48), (224, 115, 33, 50), (211, 33, 34, 47), ( 45, 33, 13, 46), (514, 32, 32, 49), (455, 32, 31, 49), (396, 32, 29, 48), (275, 32, 28, 48), (156, 32, 26, 49), (91, 32, 30, 48), (333, 31, 33, 50)]
    #
    # max_width = np.sum(c[::, (0, 2)], axis=1).max()
    # max_height = np.max(c[::, 3])
    # nearest = max_height * 1.4
    #
    # contours.sort(key=lambda r: (int(nearest * round(float(r[1]) / nearest)) * max_width + r[0]))
    #
    # for x, y, w, h in contours:
    #     print
    #     "{:4} {:4} {:4} {:4}".format(x, y, w, h)

def my_sort(rect,nb_line):
        sorted_rect_with_center = []
        ys = [let[1] + (let[3] / 3) for let in rect]
        z = np.hstack(ys)
        z = z.reshape((len(ys), 1))
        z = np.float32(z)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

        # Set flags (Just to avoid line break in the code)
        flags = cv2.KMEANS_RANDOM_CENTERS

        costs = []
        compactness, labels, centers = cv2.kmeans(z, nb_line, None, criteria, 10, flags)

        for i in range(0,nb_line):
            line = [(a, c) for a, c in zip(rect, labels) if c == i]
            line = [l[0] for l in line]
            line.sort(key=lambda x: x[0]+x[2],reverse=True)
            sorted_rect_with_center.append((centers[i][0],line))

        sorted_rect_with_center.sort(key=lambda x:x[0])
        sorted_rect = [x[1] for x in sorted_rect_with_center]
        flat_list = [item for sublist in sorted_rect for item in sublist]
        return flat_list


# def my_combine_boxes(boxes):
#     new_boxes=boxes.copy()
#     for current in new_boxes:
#         for b in new_boxes:
#             if current == b:
#                 continue
#             if intersection(current,b):
#                 if current[1] > b[1]:
#                     continue
#                 h_current =  current[3]
#                 h_b = b[3]
#                 #if current[2] > b[2]*1.5:
#                 if is_kouf(current,b):
#                     try:
#                         boxes.remove(current)
#                         boxes.remove(b)
#                         new_boxe=union(current,b)
#                         boxes.append(new_boxe)
#                     except Exception as e:
#                         pass
#
#     return boxes

def combine_boxes(boxes):
    noIntersectLoop = False
    noIntersectMain = False
    posIndex = 0
    # keep looping until we have completed a full pass over each rectangle
    # and checked it does not overlap with any other rectangle
    while noIntersectMain == False:
        noIntersectMain = True
        posIndex = 0
        # start with the first rectangle in the list, once the first
        # rectangle has been unioned with every other rectangle,
        # repeat for the second until done
        while posIndex < len(boxes):
            noIntersectLoop = False
            while noIntersectLoop == False and len(boxes) > 1:
                a = boxes[posIndex]
                listBoxes = np.delete(boxes, posIndex, 0)
                index = 0
                for b in listBoxes:
                    # if there is an intersection, the boxes overlap
                    if intersection(a, b):
                        newBox = union(a, b)
                        listBoxes[index] = newBox
                        boxes = listBoxes
                        noIntersectLoop = False
                        noIntersectMain = False
                        index = index + 1
                        break
                    noIntersectLoop = True
                    index = index + 1
            posIndex = posIndex + 1

    return boxes.astype("int")


def main():

    def d(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
            print("({},{})".format(x, y))
            [intX, intY, intW, intH] = param[1:5]





    #imgTrainingNumbers = cv2.imread("images/001.jpg")            # read in training numbers image
    #imgTrainingNumbers = cv2.imread("images/t1.jpg")  # read in training numbers image
    imgTrainingNumbers = cv2.imread("images/R/008.jpg")  # read in training numbers image
    #imgTrainingNumbers = cv2.imread("images/Stam.jpg")

    if imgTrainingNumbers is None:                          # if image was not read successfully
        print ("error: image not read from file \n\n")        # print error message to std out
        os.system("pause")                                  # pause so user can see error message
        return                                              # and exit function (which exits program)
    # end if

    imgGray = cv2.cvtColor(imgTrainingNumbers, cv2.COLOR_BGR2GRAY)          # get grayscale image
    imgBlurred = cv2.GaussianBlur(imgGray, (5,5), 0)                        # blur

                                                        # filter image from grayscale to black and white
    imgThresh = cv2.adaptiveThreshold(imgBlurred,                           # input image
                                      255,                                  # make pixels that pass the threshold full white
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,       # use gaussian rather than mean, seems to give better results
                                      cv2.THRESH_BINARY_INV,                # invert so foreground will be white, background will be black
                                      11,                                   # size of a pixel neighborhood used to calculate threshold value
                                      2)                                    # constant subtracted from the mean or weighted mean

    cv2.imshow("imgThresh", imgThresh)      # show threshold image for reference



    imgThreshCopy = imgThresh.copy()        # make a copy of the thresh image, this in necessary b/c findContours modifies the image

    imgContours, npaContours, npaHierarchy = cv2.findContours(imgThreshCopy,        # input image, make sure to use a copy since the function will modify this image in the course of finding contours
                                                 cv2.RETR_EXTERNAL,                 # retrieve the outermost contours only
                                                 cv2.CHAIN_APPROX_SIMPLE)           # compress horizontal, vertical, and diagonal segments and leave only their end points


    rects=[]
    for npaContour in npaContours:                          # for each contour
        if cv2.contourArea(npaContour) > MIN_CONTOUR_AREA:          # if contour is big enough to consider
            rect = [intX, intY, intW, intH] = cv2.boundingRect(npaContour)         # get and break out bounding rect
            # cv2.rectangle(imgTrainingNumbers,  # draw rectangle on original training image
            #               (rect[0], rect[1]),  # upper left corner
            #               (rect[0] + rect[2], rect[1] + rect[3]),  # lower right corner
            #               (0, 0, 255),  # red
            #               2)  # thickness
            #cv2.imshow("training_numbers.png", imgTrainingNumbers)
            #intChar = cv2.waitKey(0)
            rects.append(rect)
    rects_after = rects
    #rects_after = combine_boxes(rects)

    for rect in rects_after:                          # for each contour

                                                # draw rectangle around each contour as we ask user for input
            cv2.rectangle(imgTrainingNumbers,           # draw rectangle on original training image
                          (rect[0], rect[1]),                 # upper left corner
                          (rect[0]+rect[2],rect[1]+rect[3]),        # lower right corner
                          (0, 0, 255),                  # red
                          2)                            # thickness

            #imgROI = imgThresh[intY:intY+intH, intX:intX+intW]                                  # crop char out of threshold image
            #imgROIResized = cv2.resize(imgROI, (RESIZED_IMAGE_WIDTH, RESIZED_IMAGE_HEIGHT))     # resize image, this will be more consistent for recognition and storage

            # cv2.imshow("imgROI", imgROI)                    # show cropped out char for reference
            # cv2.imshow("imgROIResized", imgROIResized)      # show resized image for reference
            cv2.imshow("training_numbers.png", imgTrainingNumbers)      # show training numbers image, this will now have red rectangles drawn on it

            #cv2.setMouseCallback("training_numbers.png", d,[npaContour,intX, intY, intW, intH])
            #intChar = cv2.waitKey(0)                     # get key press
            # end if
        # end if
    # end for

    intChar = cv2.waitKey(0)
    cv2.destroyAllWindows()             # remove windows from memory

    return

###################################################################################################
if __name__ == "__main__":
    main()
# end if




