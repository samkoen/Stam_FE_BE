
import sys
import numpy as np
import cv2
import os
from os import listdir

def init_letter_to_code():
    letter_to_code = {
        'aleph': ord('א'),
        'beth': ord('ב'),
        'guimel': ord('ג'),
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
        'zevel': ord('ת') + 1,
        'zevel2': ord('ת') + 2,
        'vavyoud': ord('ת') + 3

    }

    code_to_letter = {key: value for (value, key) in letter_to_code.items()}
    return (letter_to_code,code_to_letter)
###################################################################################################

def load_data():
    (letter_to_code,code_to_letter) = init_letter_to_code()

    folders = listdir('all_letters')
    arr_img = []
    arr_letter =[]

    for folder in folders:
        files = listdir('all_letters/{}'.format(folder))
        for f in files:
            img_ori = cv2.imread('all_letters/{}/{}'.format(folder,f))
            img = cv2.cvtColor(img_ori, cv2.COLOR_BGR2GRAY)
            # cv2.imshow("img", img)
            # cv2.waitKey(0)
            img2828 = cv2.resize(img, (28,28))
            #cv2.imshow("img2828 ", img2828)
            #cv2.waitKey(0)
            #cv2.destroyWindow("img")
            arr_img.append(img2828)
            arr_letter.append(letter_to_code[folder])
            #npas = np.append(npas, img2828,0)
    trainData = np.array(arr_img)
    trainLabels = np.array(arr_letter)
    return (trainData,trainLabels)

def main():
    load_data()
###################################################################################################
if __name__ == "__main__":
    main()
# end if




