
import sys
import numpy as np
import cv2
import os
from os import listdir


WIDTH = 28
HEIGHT = 28

def init_letter_to_code():
    letter_to_code = {
        'aleph': ord('א'),
        'beth': ord('ב'),
        'guimel':ord('ג'),
        'daleth': ord('ד'),
        'he': ord('ה'),
        'vav': ord('ו'),
        'zain': ord('ז'),
        'heth': ord('ח'),
        'teth': ord('ט'),
        'youd': ord('י'),
        'caf': ord('כ'),
        'caf_sofit': ord('ך'),
        'lamed': ord('ל'),
        'mem': ord('מ'),
        'mem_sofit': ord('ם'),
        'noun': ord('נ'),
        'noun_sofit': ord('ן'),
        'sameh': ord('ס'),
        'ain': ord('ע'),
        'pe': ord('פ'),
        'pe_sofit': ord('ף'),
        'tsadik': ord('צ'),
        'tsadik_sofit': ord('ץ'),
        'kouf': ord('ק'),
        'rech': ord('ר'),
        'chin': ord('ש'),
        'tav': ord('ת'),
        'zevel':ord('ת')+1,
        'zevel2': ord('ת') + 2,
        'vavyoud': ord('ת') + 3

    }
    return letter_to_code
###################################################################################################

def load_data(file_name='all_letters',letter=None):
    letter_to_code = init_letter_to_code()

    dir = file_name
    folders = listdir(dir)
    arr_img = []
    arr_letter =[]

    for folder in folders:
        #if folder=='unknown' or folder == 'kouf - Copy':
        if folder not in letter_to_code.keys():
            continue
        if letter and folder!=letter:
            continue
        files = listdir('{}/{}'.format(dir,folder))
        for f in files:
            img_ori = cv2.imread('{}/{}/{}'.format(dir,folder,f))
            img = cv2.cvtColor(img_ori, cv2.COLOR_BGR2GRAY)
            # img = cv2.adaptiveThreshold(img,  # input image
            #     255,  # make pixels that pass the threshold full white
            #     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # use gaussian rather than mean, seems to give better results
            #     cv2.THRESH_BINARY_INV,# invert so foreground will be white, background will be black
            #     5,# size of a pixel neighborhood used to calculate threshold value
            #     2)  # constant subtracted from the mean or weighted mean

            # cv2.imshow("img", img)
            # cv2.waitKey(0)
            img2828 = cv2.resize(img, (WIDTH,HEIGHT))
            #cv2.imshow("img2828 ", img2828)
            #cv2.waitKey(0)
            #cv2.destroyWindow("img")
            arr_img.append(img2828)
            arr_letter.append(letter_to_code[folder]-1488)
            #npas = np.append(npas, img2828,0)

    from random import shuffle
    x = [i for i in range(len(arr_img))]
    shuffle(x)
    arr_img = [arr_img[ix] for ix in x]
    arr_letter = [arr_letter[ix] for ix in x]

    trainData = np.array(arr_img)
    trainLabels = np.array(arr_letter)
    return (trainData,trainLabels)


def load_data_in_folder_to_predict(file_name='all_letters/mixed'):
    letter_to_code = init_letter_to_code()

    dir = file_name
    files = listdir(dir)
    arr_img = []
    img_src_file = []
    for f in files:
        src_file = '{}/{}'.format(dir,f)
        img_ori = cv2.imread('{}/{}'.format(dir,f))
        img = cv2.cvtColor(img_ori, cv2.COLOR_BGR2GRAY)
        img2828 = cv2.resize(img, (WIDTH,HEIGHT))
        #cv2.imshow("img2828 ", img2828)
        #cv2.waitKey(0)
        arr_img.append(img2828)
        img_src_file.append(f)

    trainData = np.array(arr_img)
    return (trainData,img_src_file)


def load_image_to_predict(img):
    ar=[]
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img2828 = cv2.resize(img, (WIDTH,HEIGHT))
    #cv2.imshow("img2828 ", img2828)
    #cv2.waitKey(0)
    ar.append(img2828)
    return np.array(ar)


def copy_image_to_folder(testDataFile, letter_code):
    src_dir = '../OpenCV_3_KNN_Character_Recognition_Python/all_letters/mixed'
    src_file = '{}/{}'.format(src_dir, testDataFile)
    img_ori = cv2.imread(src_file)

    dst_dir = '../OpenCV_3_KNN_Character_Recognition_Python/all_letters_sorted_by_prediction'
    letter_to_code = init_letter_to_code()
    code_to_letter = {key: value for (value, key) in letter_to_code.items()}
    final_dst_dir = '{}/{}'.format(dst_dir,code_to_letter[letter_code])
    if not os.path.exists(final_dst_dir):
        os.makedirs(final_dst_dir)
    cv2.imwrite('{}/{}'.format(final_dst_dir,testDataFile),img_ori)


def main():
    load_data()
###################################################################################################
if __name__ == "__main__":
    main()
# end if




