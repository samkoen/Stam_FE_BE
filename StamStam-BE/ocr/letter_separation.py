import base64

import cv2
import imutils
import numpy as np

from ocr.Letter import Letter
#from ocr.model import lenet_stam_predict
# Si vous avez nommé le nouveau fichier lenet_stam_predict_fast.py
from ocr.model import lenet_stam_predict_fast as lenet_stam_predict
from rect_util import letter_union,is_horizontal_include,is_horizontal_include_from_col

MIN_CONTOUR_AREA = 100
MAX_CONTOUR_AREA = 10000
WEIGHT_FILE_1 = 'model/output/Adadelta_decay_256_30.hdf5'
WEIGHT_FILE_2 = 'model/output/Adamax_beta_1_256_30.hdf5'


def apply_threshold(img, argument):
    switcher = {
        1: cv2.threshold(cv2.GaussianBlur(img, (9, 9), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        2: cv2.threshold(cv2.GaussianBlur(img, (7, 7), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        3: cv2.threshold(cv2.GaussianBlur(img, (5, 5), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        4: cv2.threshold(cv2.medianBlur(img, 5), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        5: cv2.threshold(cv2.medianBlur(img, 3), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        6: cv2.adaptiveThreshold(cv2.GaussianBlur(img, (9, 9), 0), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 3, 2),
        7: cv2.adaptiveThreshold(cv2.medianBlur(img, 7), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 2),
        8: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2),
        9: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 2),
        10: cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 1501, 2),
    }
    return switcher.get(argument, "Invalid method")


def get_npa_contour(img, tresh=9):
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # get grayscale image
    #imgBlurred = cv2.blur(imgGray, (11, 11))  # blur
    #imgBlurred = cv2.addWeighted(imgGray,1.5,imgGray,-0.5,0)
    imgBlurred = imgGray
    # filter image from grayscale to black and white

    imgThresh_before_dilation = apply_threshold(imgBlurred, tresh)
    # imgThresh_before_dilation = cv2.adaptiveThreshold(imgBlurred,  # input image
    #                                                   255,  # make pixels that pass the threshold full white
    #                                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                                                   # use gaussian rather than mean, seems to give better results
    #                                                   cv2.THRESH_BINARY_INV,
    #                                                   # invert so foreground will be white, background will be black
    #                                                   31,
    #                                                   # size of a pixel neighborhood used to calculate threshold value
    #                                                   2)  # constant subtracted from the mean or weighted mean

    cv2.namedWindow("aaa", cv2.WINDOW_NORMAL)
    cv2.imshow("aaa", imgThresh_before_dilation)
    cv2.waitKey(0)

    # kernel = np.ones((3, 3), np.uint8)
    # imgThresh = cv2.dilate(imgThresh_before_dilation, kernel, iterations=2)
    imgThresh = imgThresh_before_dilation
    cv2.imshow("b", imgThresh)      # show threshold image for reference
    cv2.waitKey(0)
##########################################################################################################################
    # gray = cv2.bilateralFilter(imgGray, -1, 11, 11)
    # edged = cv2.Canny(gray, 10, 200)
    # imgThresh = edged
    # cv2.imshow("b", imgThresh)      # show threshold image for reference
    # cv2.waitKey(0)
##########################################################################################################################

    imgThreshCopy = imgThresh.copy()  # make a copy of the thresh image, this in necessary b/c findContours modifies the image

    # from scipy import ndimage
    # from skimage.feature import peak_local_max
    # from skimage.morphology import watershed
    #
    # D = ndimage.distance_transform_edt(imgThreshCopy)
    # localMax = peak_local_max(D, indices=False, min_distance=20,
    #                           labels=imgThreshCopy)
    # markers = ndimage.label(localMax, structure=np.ones((3, 3)))[0]
    # labels = watershed(-D, markers, mask=imgThreshCopy)
    #
    # # perform a connected component analysis on the local peaks,
    # # using 8-connectivity, then appy the Watershed algorithm
    # markers = ndimage.label(localMax, structure=np.ones((3, 3)))[0]
    # labels = watershed(-D, markers, mask=imgThreshCopy)


    #rect_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (1, 3))
    #imgThreshCopy = cv2.morphologyEx(imgThreshCopy, cv2.MORPH_CROSS, rect_kernel)
    # cv2.imshow('threshed', imgThreshCopy)
    # cv2.waitKey(0)

    kernel = np.ones((2, 2), np.uint8)
    imgThreshCopy = cv2.erode(imgThreshCopy, kernel, iterations=1)
    # imgThreshCopy = cv2.dilate(imgThreshCopy, kernel, iterations=1)


    if imutils.is_cv2() or imutils.is_cv4():
        imgContours, npaContours = cv2.findContours(imgThreshCopy, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # cv2.imshow("c", imgContours)  # show threshold image for reference
        # cv2.waitKey(0)
        cv2.destroyAllWindows()

        return (imgContours, npaContours)

    elif imutils.is_cv3():
        imgContours, npaContours, npaHierarchy = cv2.findContours(imgThreshCopy,
                                                                  # input image, make sure to use a copy since the function will modify this image in the course of finding contours
                                                                  # cv2.RETR_EXTERNAL,  # retrieve the outermost contours only
                                                                  cv2.RETR_TREE,
                                                                  cv2.CHAIN_APPROX_SIMPLE)  # compress horizontal, vertical, and diagonal segments and leave only their end points

        # cv2.imshow("c", imgContours)  # show threshold image for reference
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        return (imgContours, npaContours, npaHierarchy)



def img_to_letters(npa,img_src,WEIGHT_FILE):
    if imutils.is_cv3():
        npaContours = npa[1]
    elif imutils.is_cv2() or imutils.is_cv4():
        npaContours = npa[0]

    #imgContours = npa[0]
    #npaHierarchy = npa[2]

    #new_npaContours = []
    #new_imgContours = []
    #new_npaHierarchy = []

    #line = [(a, c) for a, c in zip(rect, labels) if c == i]
    #new_npa = [(a,b,c) for a,b,c in zip(npa[0],npa[1],npa[2]) if cv2.contourArea(b) > MIN_CONTOUR_AREA]
    #new_npa = [(b,c) for b,c in zip(npaContours,npaHierarchy[0]) if cv2.contourArea(b) > MIN_CONTOUR_AREA]

    rects = []
    arr_img = []
    my_npa_contours = []
    for npaContour in npaContours:  # for each contour
        if  MAX_CONTOUR_AREA > cv2.contourArea(npaContour) > MIN_CONTOUR_AREA:  # if contour is big enough to consider
            rect = [intX, intY, intW, intH] = cv2.boundingRect(npaContour)  # get and break out bounding rect
            rects.append(rect)
            my_npa_contours.append(npaContour)

            img_rect = img_src[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]
            img_rect = cv2.cvtColor(img_rect, cv2.COLOR_BGR2GRAY)
            img2828 = cv2.resize(img_rect, (28, 28))
            arr_img.append(img2828)

    testData = np.array(arr_img)

    predictions = lenet_stam_predict.predict(weight_file=WEIGHT_FILE, testData=testData)

    letters_val = list(zip(rects, arr_img, predictions,my_npa_contours))

    letters = [Letter(x[0], x[2], x[1], x[3] ) for x in letters_val if x[2] != 27]  # 27 is zevel
    return letters

def separate_letter(rect,img,WEIGHT_FILE):
    z = np.ones(img.shape,dtype=np.uint8) * 255
    img_s = img[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]
    z[rect[1]: rect[1] + rect[3], rect[0]: rect[0] + rect[2]] = img_s



    imgTraining = z.copy()
    (imgContours, npaContours, npaHierarchy) = get_npa_contour(imgTraining,6)
    letters = img_to_letters((imgContours, npaContours, npaHierarchy), imgTraining,WEIGHT_FILE)
    sort_contour_one_line(letters)

    # show_img_with_rect(letters, imgTraining, print_letter_flag=True)
    # cv2.destroyAllWindows()

    fix_issues_box(letters, z, WEIGHT_FILE)
    #show_img_with_rect(letters, z, print_letter_flag=True)
    return letters


def show_img_with_rect(letters,img,mouse_flag=False,print_letter_flag = False):
    img=img.copy()
    def d(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for let in letters:
                if let.rect[0] < x < let.rect[0] + let.rect[2] and let.rect[1] < y < let.rect[1] + let.rect[3]:
                    #print("{} - {},msg: {}".format(let._chr,let.real_chr, let.err_msg))
                    print("current: {} ----- err msg: {}".format(let.real_chr,let.err_msg))

                    #break

    cv2.namedWindow("training_numbers.png", cv2.WINDOW_NORMAL)
    #cv2.namedWindow("training_numbers.png")
    if mouse_flag:
        cv2.setMouseCallback("training_numbers.png", d)
    i=0
    for letter in letters:  # for each contour
        rect = letter.rect
        if letter.status!="OKK":
            cv2.rectangle(img,  # draw rectangle on original training image
                          (rect[0], rect[1]),  # upper left corner
                          (rect[0] + rect[2], rect[1] + rect[3]),  # lower right corner
                          #(0, 0, 255) if letter.error else (255,0,0) if letter.missing else (0,255,0),  # red
                          (0, 0, 255) if letter.status in ['wrong','superflus'] else (255, 0, 0) if letter.status=='missing' else (0, 255, 0),
                          2)  # thickness

        cv2.imshow("training_numbers.png", img)
        #cv2.imshow("training_numbers.png", cv2.resize(img,(1900,250)))

        if print_letter_flag:
            print("{} letter: {} --- {}".format(i,letter.rect, chr(letter._chr + 1488)))
            intChar = cv2.waitKey(0)  # get key press
        i=i+1

    # if flag:
    #     #cv2.setMouseCallback("training_numbers.png", d)
    #     cv2.waitKey(0)

def sort_contour_one_line(letters):
    letters.sort(key=lambda b: b.rect[0] + b.rect[2], reverse=True)

def sort_contour(letters,img_src):
    def print_lines(lines):
        print('=====================================')
        for line in lines:
            a=''
            for ch in line:
                a='{}{}'.format(a,ch.real_chr)
            print(a)

    from rect_util import is_include
    # sort all rect by their y
    width_mean = sum(l.rect[2] for l in letters)/len(letters)
    letters.sort(key=lambda b: b.rect[0]+b.rect[2],reverse=True)
    lines=[[letters[0]]]
    # last_rect_in_line = [letters[0]]
    for i in range(1,len(letters)):
        follow_letters = []
        last_idx=-1
        while len(follow_letters)==0 and last_idx > -3:# this loop is for the case 2 letters are on same line, \
            #but they have no height in common (for example, yud and the bar of the kuf
            line = 0
            for current_line in lines:
                if len(current_line) < abs(last_idx):
                    continue
                last_rect = current_line[last_idx]
                h = letters[i].follow(last_rect,width_mean)
                if h:
                    follow_letters.append( (letters[i],h,line,last_rect) )
                line = line + 1
            last_idx = last_idx -1
        if len(follow_letters)==0:
            # last_rect_in_line.append(letters[i])
            lines.append([letters[i]])

            if i > 100:
                cv2.destroyAllWindows()
                img = img_src.copy()
                cv2.namedWindow("training_numbers.png", cv2.WINDOW_NORMAL)
                rect = letters[i].rect
                cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (255, 0, 0), 5)
                cv2.imshow("training_numbers.png", img)
                cv2.waitKey(0)

        else:
            if i> 100    :
                cv2.destroyAllWindows()
                img = img_src.copy()
                cv2.namedWindow("training_numbers.png", cv2.WINDOW_NORMAL)
                rect = letters[i].rect
                cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (0, 255, 0), 5)
                cv2.imshow("training_numbers.png", img)
                cv2.waitKey(0)

                for f in follow_letters:
                    cv2.rectangle(img, (f[3].rect[0], f[3].rect[1]), (f[3].rect[0] + f[3].rect[2], f[3].rect[1] + f[3].rect[3]), (255, 0, 0), 5)
                    cv2.imshow("training_numbers.png", img)
                f = max(follow_letters, key=lambda f: f[1])
                cv2.rectangle(img, (f[3].rect[0], f[3].rect[1]),
                              (f[3].rect[0] + f[3].rect[2], f[3].rect[1] + f[3].rect[3]), (0, 0, 255), 5)
                cv2.imshow("training_numbers.png", img)
                intChar = cv2.waitKey(0)  # get key press

            follow_letter = max(follow_letters,key=lambda f:f[1])
            try:
                if not is_include(lines[follow_letter[2]][last_idx+1],letters[i]):
                    # last_rect_in_line[follow_letter[2]] = letters[i]
                    lines[follow_letter[2]].append(letters[i])
                else:
                    pass
            except Exception as e:
                pass
        #print_lines(lines)


    lines.sort(key=lambda b: b[0].rect[1])

    #mean_len_line = sum([len(l) for l in lines]) / len(lines)
    #lines = [l for l in lines if len(l) > mean_len_line]

    #add the number line for each letter
    [[c.set_line_nb(idx) for c in l] for idx, l in enumerate(lines)]

    flat_list = [item for sublist in lines for item in sublist]
    # return letters
    return flat_list,lines


def fix_issues_box(letters,img_src,WEIGHT_FILE):
    i = 0
    img = img_src.copy()
    while i < len(letters) - 1:
        #print('{} {}'.format(i, letters[i].real_chr))
        if i>5000:
            rect = letters[i].rect
            cv2.rectangle(img,(rect[0], rect[1]),(rect[0] + rect[2], rect[1] + rect[3]),(0, 255, 0),2)
            cv2.imshow("fix_issue.png", img)
            intChar = cv2.waitKey(0)  # get key press
        un = is_horizontal_include(letters, i, img_src)
        if un:
            continue
        i = i +1
    unpredicted_letters = [let for let in letters if let.unpredicted()]
    testData = [let.img for let in unpredicted_letters]
    testData = np.array(testData)
    predictions = lenet_stam_predict.predict(weight_file=WEIGHT_FILE, testData=testData)
    [let.set_prediction(pred) for let, pred in zip(unpredicted_letters, predictions)]

    pass


    #cv2.namedWindow("fix_issue.png", cv2.WINDOW_NORMAL)
    i=0
    while i<len(letters)-1:
            #print('{} {}'.format(i, letters[i].real_chr))
            # rect = letters[i].rect
            # cv2.rectangle(img,(rect[0], rect[1]),(rect[0] + rect[2], rect[1] + rect[3]),(0, 255, 0),2)
            # cv2.imshow("fix_issue.png", img)
            # intChar = cv2.waitKey(0)  # get key press


        # try:
        #     kuf = is_kuf(letters, img_src,i,WEIGHT_FILE)
        #     if kuf:
        #         continue

            if aleph_youd(letters,i): #aleph-youd = aleph
                continue

            if he_youd(letters,i): #he-youd = he
                continue

            if tav_youd(letters,i):
                continue

            if teit_youd(letters, i):
                continue

            if ain_youd(letters,i,img_src,WEIGHT_FILE): #ain-youd = chin
                continue


        # except Exception as e:
        #     print('Exception')


            i=i+1

def aleph_youd(letters,i):
    # aleph qui ressemble a aleph et youd
    idx=None
    if letters[i]._chr == 0 and letters[i + 1]._chr == 9:  # aleph and youd
        aleph = letters[i]
        youd = letters[i + 1]
        idx = i + 1
    elif letters[i]._chr == 9 and letters[i + 1]._chr == 0:
        aleph = letters[i + 1]
        youd = letters[i]
        idx = i

    if idx is not None:
        if aleph.rect[0] < youd.rect[0] < aleph.rect[0] + aleph.rect[2] or \
                aleph.rect[0] < youd.rect[0] + youd.rect[2] < aleph.rect[0] + aleph.rect[2]:  # remove youd
            del letters[idx]
            return True
    return False

def he_youd(letters,i):
    # he qui ressemble a he et youd ou he et vav
    if letters[i]._chr == 4 and (letters[i + 1]._chr in [2, 5, 6, 9, 16]):  # he and youd
        he = letters[i]
        youd = letters[i + 1]
        idx = i + 1
        if he.rect[0] < youd.rect[0] + youd.rect[2] < he.rect[0] + he.rect[2] and he.rect[1] < youd.rect[1]:
            del letters[idx]
            return True
    return False

def tav_youd(letters,i):
    # he qui ressemble a he et youd ou he et vav
    if letters[i]._chr == 26 and (letters[i + 1]._chr in [2, 5, 6, 9, 16]):  # he and youd
        tav = letters[i]
        youd = letters[i + 1]
        idx = i + 1
        if tav.rect[0] < youd.rect[0] + youd.rect[2] < tav.rect[0] + tav.rect[2] and tav.rect[1] < youd.rect[1]:
            del letters[idx]
            return True
    return False

def teit_youd(letters,i):
    # he qui ressemble a he et youd ou he et vav
    if letters[i]._chr == 8 and (letters[i + 1]._chr in [9]):  # he and youd
        teit = letters[i]
        youd = letters[i + 1]
        idx = i + 1
        if teit.rect[0] < youd.rect[0] + youd.rect[2] < teit.rect[0] + teit.rect[2] and teit.rect[1] < youd.rect[1]+youd.rect[3]:
            del letters[idx]
            return True
    return False


def ain_youd(letters,i,img_src,WEIGHT_FILE):
    # chin qui ressemble a ain et youd
    if letters[i]._chr == 18 and letters[i + 1]._chr == 9:  # ain and youd
        ain = letters[i]
        youd = letters[i + 1]

        if ain.rect[0] < youd.rect[0] + youd.rect[2] < ain.rect[0] + ain.rect[2]:  # remove youd
            new_letter = letter_union(ain.rect,youd.rect, img_src, WEIGHT_FILE)
            if (new_letter._chr + 1488) in [ord('ש')]:
                letters[i] = new_letter
                del letters[i + 1]
                return True
    return False




def fix_issues_box_after_comparison(cmp_result,letters,img_src,WEIGHT_FILE):
    letters_to_delete=[] #list of indexes to delete from letters
    i = 0
    idx = 0
    while i < len(cmp_result):
        try:
            st = cmp_result[i]
            if st[0] == 0:
                idx = idx + len(st[1])
            elif st[0] == -1 and i + 1 < len(cmp_result) and cmp_result[i + 1][0] == 1:
                let_err = letters[idx]
                err_msg = "error: {} instead of {} at {}".format(cmp_result[i + 1][1], st[1], idx)
                print(err_msg)
                if len(cmp_result[i + 1][1]) == 2:
                    un = letter_union(letters[idx].rect,letters[idx+1].rect, img_src, WEIGHT_FILE)
                    if un.real_chr == st[1]:
                        letters_to_delete.append(idx+1)
                        letters[idx] = un
                        print('{}: unify {} to {}'.format(idx,cmp_result[i + 1][1],un.real_chr))
                elif len(cmp_result[i + 1][1]) == 1 and len(st[1]) == 1:
                    un = letter_union(letters[idx].rect, letters[idx].rect, img_src, WEIGHT_FILE_1)
                    if un.real_chr == st[1]:
                        letters[idx] = un
                        print('{}: new prediction of {} using {}: {}'.format(idx,cmp_result[i + 1][1],WEIGHT_FILE_1, un.real_chr))
                    else:
                        un = letter_union(letters[idx].rect, letters[idx].rect, img_src, WEIGHT_FILE_2)
                        if un.real_chr == st[1]:
                            letters[idx] = un
                            print('{}: new prediction of {} using {}: {}'.format(idx, cmp_result[i + 1][1], WEIGHT_FILE_2,
                                                                               un.real_chr))
                        else:
                            new_letters = separate_letter(letters[idx].rect, img_src, WEIGHT_FILE)
                            letters[idx].set_separate_letters(new_letters)
                            print('{}: {} is in fact {}'.format(idx, cmp_result[i + 1][1], ''.joins([let.real_chr for let in new_letters])))
                elif len(cmp_result[i + 1][1]) == 1 and len(st[1]) > 1:
                    new_letters = separate_letter(letters[idx].rect,img_src,WEIGHT_FILE)
                    letters[idx].set_separate_letters(new_letters)
                    print('{}: {} is in fact {}'.format(idx, cmp_result[i + 1][1],
                                                        ''.joins([let.real_chr for let in new_letters])))


                idx = idx + len(cmp_result[i + 1][1])
                i = i + 1

            elif st[0] == -1:
                let_err = letters[idx]
                err_msg = "missing {} at {}".format(st[1], idx)
                print(err_msg)
                # new_letters = separate_letter(letters[idx].rect, img_src, WEIGHT_FILE)
                # letters[idx].set_separate_letters(new_letters)

                idx = idx
            elif st[0] == 1:
                for let_err in letters[idx:idx + len(st[1])]:
                    err_msg = "superflus {} at {}".format(let_err.real_chr, idx)
                    print(err_msg)
                    idx = idx + 1
        except Exception as e:
            print("error in fix_issues_box_after_comparison")
        i = i + 1

    for idx in reversed(letters_to_delete):
        del letters[idx]


    letters_2=[]
    for let in letters:
        if let.separate_letters is None:
            letters_2.append(let)
        else:
            for slet in let.separate_letters:
                letters_2.append(slet)
    return letters_2

def sort_contour_top_to_bottom(letters,img_src):
    # sort all rect by their y
    height_mean = sum(l.rect[3] for l in letters)/len(letters)
    letters.sort(key=lambda b: b.rect[1])
    columns=[[letters[0]]]
    # last_rect_in_line = [letters[0]]
    for i in range(1,len(letters)):
        follow_letters = []
        last_idx=-1
        while len(follow_letters)==0 and last_idx > -2:# this loop is for the case 2 letters are on same line, \
            #but they have no height in common (for example, yud and the bar of the kuf
            col = 0
            for current_col in columns:
                if len(current_col) < abs(last_idx):
                    continue
                last_rect = current_col[last_idx]
                h = letters[i].follow_top_to_bottom(last_rect,height_mean)
                if h:
                    follow_letters.append( (letters[i],h,col,last_rect) )
                col = col + 1
            last_idx = last_idx -1
        if len(follow_letters)==0:
            # last_rect_in_line.append(letters[i])
            columns.append([letters[i]])

            if i > 1127:
                cv2.destroyAllWindows()
                img = img_src.copy()
                cv2.namedWindow("training_numbers.png", cv2.WINDOW_NORMAL)
                rect = letters[i].rect
                cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (255, 0, 0), 5)
                cv2.imshow("training_numbers.png", img)
                cv2.waitKey(0)

        else:
            if i>125   :
                cv2.destroyAllWindows()
                img = img_src.copy()
                cv2.namedWindow("training_numbers.png", cv2.WINDOW_NORMAL)
                rect = letters[i].rect
                cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (0, 255, 0), 5)
                cv2.imshow("training_numbers.png", img)
                cv2.waitKey(0)

                for f in follow_letters:
                    cv2.rectangle(img, (f[3].rect[0], f[3].rect[1]), (f[3].rect[0] + f[3].rect[2], f[3].rect[1] + f[3].rect[3]), (255, 0, 0), 5)
                    cv2.imshow("training_numbers.png", img)
                f = max(follow_letters, key=lambda f: f[1])
                for f in follow_letters:
                    cv2.rectangle(img, (f[3].rect[0], f[3].rect[1]),
                                  (f[3].rect[0] + f[3].rect[2], f[3].rect[1] + f[3].rect[3]), (0, 0, 255), 5)
                    cv2.imshow("training_numbers.png", img)
                    intChar = cv2.waitKey(0)  # get key press


            try:
                for follow_letter in follow_letters:
                    columns[follow_letter[2]].append(letters[i])
                else:
                    pass
            except Exception as e:
                pass

            # follow_letter = max(follow_letters,key=lambda f:f[1])
            # try:
            #     if not is_include(columns[follow_letter[2]][last_idx+1],letters[i]):
            #         # last_rect_in_line[follow_letter[2]] = letters[i]
            #         columns[follow_letter[2]].append(letters[i])
            #     else:
            #         pass
            # except Exception as e:
            #     pass

        columns.sort(key=lambda b: b[0].rect[0]+b[0].rect[2],reverse=True)
        #letters.sort(key=lambda b: b.rect[0] + b.rect[2], reverse=True)

    flat_list = [item for sublist in columns for item in sublist]
    # return letters
    return flat_list,columns


def fix_issues_box_from_col(letters,img_src,WEIGHT_FILE):
    i = 0
    cv2.namedWindow("fix_issue.png", cv2.WINDOW_NORMAL)
    img = img_src.copy()
    rect = letters[i].rect
    cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (0, 255, 0), 2)
    cv2.imshow("fix_issue.png", img)

    while i < len(letters) - 1:
        #print('{} {}'.format(i, letters[i].real_chr))
        if i>0:
            rect = letters[i+1].rect
            cv2.rectangle(img,(rect[0], rect[1]),(rect[0] + rect[2], rect[1] + rect[3]),(0, 255, 0),2)
            cv2.imshow("fix_issue.png", img)
            intChar = cv2.waitKey(0)  # get key press
        flag,un = is_horizontal_include_from_col(letters, i, img_src)
        if flag:
            print('XXXXXXXX {}'.format(i))
            rect=un.rect
            cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (255, 0, 0), 2)
            cv2.imshow("fix_issue.png", img)
            intChar = cv2.waitKey(0)  # get key press
            continue
        i = i +1

    testData = [let.img for let in letters]
    testData = np.array(testData)
    predictions = lenet_stam_predict.predict(weight_file=WEIGHT_FILE, testData=testData)
    [let.set_prediction(pred) for let, pred in zip(letters, predictions)]


def get_image_result(letters,img):
    img=img.copy()

    i=0
    for letter in letters:  # for each contour
        rect = letter.rect
        if letter.status!="OKK":
            cv2.rectangle(img,  # draw rectangle on original training image
                          (rect[0], rect[1]),  # upper left corner
                          (rect[0] + rect[2], rect[1] + rect[3]),  # lower right corner
                          #(0, 0, 255) if letter.error else (255,0,0) if letter.missing else (0,255,0),  # red
                          (0, 0, 255) if letter.status in ['wrong','superflus'] else (255, 0, 0) if letter.status=='missing' else (0, 255, 0),
                          2)  # thickness

    return image_to_b64(img)


def image_to_b64(img):
    npimg2 = cv2.imencode('.jpg', img)[1]
    npimg_after = npimg2.flatten()
    img_after = npimg_after.tobytes()
    b64_after = base64.b64encode(img_after)
    return b64_after

    # cv2.imshow("test64.png", img_src)
    # cv2.waitKey(0)


