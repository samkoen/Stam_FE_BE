# GenData.py

import base64
import os
from os import listdir

import cv2
import diff_match_patch as dmp_module
import imutils
import numpy as np

from ocr.image_to_np import init_letter_to_code
from ocr.letter_separation import img_to_letters, get_npa_contour, show_img_with_rect, sort_contour, fix_issues_box ,fix_issues_box_after_comparison, get_image_result

RESIZED_IMAGE_WIDTH = 20
RESIZED_IMAGE_HEIGHT = 30

#WEIGHT_FILE = 'model/output/Nadam_beta_1_256_30.hdf5'
WEIGHT_FILE = 'model/output/Nadam_beta_1_256_30.hdf5'
#WEIGHT_FILE = 'model/output/Adagrad_2_decay_128_20.hdf5'
#WEIGHT_FILE = 'model/output/Adadelta_decay_256_30.hdf5'
#WEIGHT_FILE = 'model/output/Adamax_decay_256_20.hdf5'


###################################################################################################
import string
import random

def randomword(length):
   letters = string.ascii_lowercase
   return ''.join(random.choice(letters) for i in range(length))

def read_source_text(src):
    src_txt = []
    import io
    with io.open(src, 'r', encoding='UTF-16') as file:
        for line in file:
            src_txt.append(line.rstrip())
    return src_txt





def manual_filter(letters,img,print_letter_flag=False):

    wrong_letters=[]
    def d(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y
            for let in letters:
                if let.rect[0] < x < let.rect[0] + let.rect[2] and let.rect[1] < y < let.rect[1] + let.rect[3]:
                    letters.remove(let)
                    wrong_letters.append(let)
                    break
            #cv2.destroyAllWindows()

    cv2.namedWindow("training_numbers.png", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("training_numbers.png", d, )  # [npaContour, intX, intY, intW, intH])
    while True:
        img_2 = img.copy()
        show_img_with_rect(letters, img_2,False,print_letter_flag)
        key = cv2.waitKey(1000)   & 0xFF
        #key = ord('c')
        if key == ord(' ') or key == ord('c') or key == ord('-') or key == ord('+') or key==ord('s'):
            break

    return letters,key,wrong_letters


def preprocessing(img):
    # resizing using aspect ratio intact and finding the circle
    # reduce size retain aspect ratio intact
    # invert BGR 2 RGB
    #RGB = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    RGB = img
    Ig = RGB[:, :, 2]
    [w,h] = np.shape(Ig)
    r=1200.0/Ig.shape[1]
    dim=(1200,int(Ig.shape[0]*r))
    rz = cv2.resize(Ig,dim,interpolation=cv2.INTER_AREA)
    #  convert in to float and get log trasform for contrast streching
    g = 0.2 * (np.log(1 + np.float32(rz)))
    # change into uint8
    cvuint = cv2.convertScaleAbs(g)
    # cvuint8.dtype
    ret, th = cv2.threshold(cvuint, 0, 255, cv2.THRESH_OTSU)
    ret1,th1 = cv2.threshold(Ig,0,255,cv2.THRESH_OTSU)
    # closeing operation
    # from skimage.morphology import disk
    # from skimage.morphology import erosion, dilation, opening, closing, white_tophat
    # selem = disk(30)
    # cls = opening(th, selem)
    # plot_comparison(orig_phantom, eroded, 'erosion')
    # in case using opencv
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    cls = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)
    Im = cls*rz # the mask with resize image
    # cv2.imwrite('mynew.jpg', mask)
    cv2.imshow("Im",Im)
    cv2.imshow("th", th)
    cv2.imshow("th1", th1)
    cv2.imshow("cls", cls)
    cv2.imshow("g", g)
    cv2.imshow("RGB", RGB)
    cv2.waitKey(0)
    return (Im,th,th1,cls,g,RGB)


def compare_with_right_paracha(letters_after):
    text_hebrew = [chr(let._chr + 1488) for let in letters_after]
    current = ''.join(text_hebrew)
    dmp = dmp_module.diff_match_patch()

    src_txt =[''.join(read_source_text('chema.txt')), ''.join(read_source_text('chamoa.txt')), \
              ''.join(read_source_text('kadesh.txt')), ''.join(read_source_text('kiyeviaha.txt')), \
              ''.join(read_source_text('mezuza.txt'))]
    #src_txt = [''.join(read_source_text('kadesh.txt'))]

    x = [dmp.diff_main(src, current) for src in src_txt]
    return min(x, key=lambda k: len(k))


def remove_wrong_line(lines,letters):
    # reduce(lambda ex, c: ex and c.error, lines[15], True)
    # [l.set_line_nb(0) for l in lines[0] if reduce(lambda ex, c: ex and c.error, lines[0], True)]
    from functools import reduce
    [[letter.set_status('XXX') for letter in line if reduce(lambda ex, c: ex and c.error, line, True)] for line in
     lines]
    letters_to_return = [let for let in letters if let.status != 'XXX']




    return letters_to_return

def print_result(x,letters_after):
    if len(x)==0:
        print('success')
        return

    i = 0
    idx = 0
    while i < len(x):
        try:
            st = x[i]
            if st[0] == 0:
                idx = idx + len(st[1])
            elif st[0] == -1 and i + 1 < len(x) and x[i + 1][0] == 1:
                let_err = letters_after[idx]
                let_err.status = "wrong"
                let_err.error = True
                let_err.err_msg = "error: {} instead of {} at {}".format(x[i + 1][1], st[1], idx)
                print(let_err.err_msg)
                idx = idx + len(x[i + 1][1])
                i = i + 1

            elif st[0] == -1:
                let_err = letters_after[idx]
                let_err.status = "missing"
                let_err.missing = True
                let_err.err_msg = "missing {} at {}".format(st[1], idx)
                print(let_err.err_msg)
                idx = idx
            elif st[0] == 1:
                for let_err in letters_after[idx:idx + len(st[1])]:
                    # let_err = letters_after[idx]
                    let_err.status = "superflus"
                    let_err.error = True
                    let_err.err_msg = "superflus {} at {}".format(let_err.real_chr, idx)
                    print(let_err.err_msg)
                    idx = idx + 1
        except Exception as e:
            pass
        i = i + 1

# def second_preprocessing(letters,img_src):
#     for let in letters:
#         img_rect = img_src[let.rect[1]:let.rect[1] + let.rect[3], let.rect[0]:let.rect[0] + let.rect[2]]
#         imgTraining = img_rect.copy()
#         (imgContours, npaContours, npaHierarchy) = get_npa_contour(imgTraining)
#         if len(npaContours)>1:
#             letters = img_to_letters((imgContours, npaContours, npaHierarchy), img_rect)
#             show_img_with_rect(letters, imgTraining, False, True)
#         # cv2.destroyAllWindows()

def print_stat(letters,img_src):
    print(img_src.shape)
    all_npa_aera = [cv2.contourArea(l.npa_contour) for l in letters]
    print("aera:")
    print("min: {}".format(min(all_npa_aera)))
    print("max: {}".format(max(all_npa_aera)))
    print("mean: {}".format(sum(all_npa_aera)/len(all_npa_aera)))

    widths = [l.rect[2] for l in letters]
    height = [l.rect[3] for l in letters]
    print("widths")
    print("min: {}".format(min(widths)))
    print("max: {}".format(max(widths)))
    print("mean: {}".format(sum(widths)/len(widths)))
    print("heights")
    print("min: {}".format(min(height)))
    print("max: {}".format(max(height)))
    print("mean: {}".format(sum(height) / len(height)))

    ra = [w*h for w,h in zip(widths,height)]
    r = [a/p for a,p in zip(all_npa_aera,ra)]

    print("relative")
    print("min: {}".format(min(r)))
    print("max: {}".format(max(r)))
    print("mean: {}".format(sum(r) / len(r)))

def print_lines(lines):
    print('=====================================')
    i=0
    for line in lines:
        a = [let.real_chr for let in line]
        print('{} - {}'.format(i,''.join(a)))
        i=i+1

def check_image(img_src):
    global MIN_CONTOUR_AREA

    if img_src is None:  # if image was not read successfully
        print("error: image not read from file \n\n")  # print error message to std out
        os.system("pause")  # pause so user can see error message
        return  # and exit function (which exits program)
        # end if

    # cv2.imshow("src",img_src)
    # cv2.waitKey(0)

    # img_src = cv2.resize(img_src, (0,0), fx=5, fy=5)


    imgTraining = img_src.copy()

    if imutils.is_cv3():
        (imgContours, npaContours, npaHierarchy) = get_npa_contour(imgTraining, 9)
        letters = img_to_letters((imgContours, npaContours, npaHierarchy), img_src, WEIGHT_FILE)
    elif imutils.is_cv2() or imutils.is_cv4():
        (imgContours, npaContours) = get_npa_contour(imgTraining, 9)
        letters = img_to_letters((imgContours, npaContours), img_src, WEIGHT_FILE)



    # second_preprocessing(letters,img_src)

    if len(letters) == 0:
        exit(0)
    # for l in letters:
    #     l.show(img_src)

    letters_after = letters

    intChar = ord('c')
    #letters_after, intChar,wrong = manual_filter(letters_after, imgTraining)

    print_stat(letters_after, img_src)
    # print_stat(wrong, img_src)

    # letters_after, _ = sort_contour_top_to_bottom(letters_after, img_src)
    # show_img_with_rect(letters_after, img_src, print_letter_flag=False)
    # cv2.waitKey(0)
    # fix_issues_box_from_col(letters_after, img_src, WEIGHT_FILE)
    # show_img_with_rect(letters_after, img_src, print_letter_flag=True)
    # cv2.waitKey(0)

    letters_after, lines = sort_contour(letters_after, img_src)
    print_lines(lines)
    show_img_with_rect(letters_after, img_src,print_letter_flag=True)

    print('remove superfluous rect')
    fix_issues_box(letters_after, img_src, WEIGHT_FILE)
    cv2.destroyAllWindows()
    show_img_with_rect(letters_after, img_src, print_letter_flag=True)
    cv2.waitKey(0)

    print('compare 1')
    x = compare_with_right_paracha(letters_after)
    # print_result(x, letters_after)
    # remove_wrong_line(lines,letters_after)
    cv2.destroyAllWindows()
    show_img_with_rect(letters_after, img_src, True, False)
    cv2.waitKey(0)
    print('fix after comparison 1')
    letters_after = fix_issues_box_after_comparison(x, letters_after, img_src, WEIGHT_FILE)

    print('compare 2')
    x = compare_with_right_paracha(letters_after)
    print_result(x, letters_after)

    print('remove wrong lines')
    letters_after = remove_wrong_line(lines, letters_after)
    # _, lines_after_remove = sort_contour(letters_after, img_src)
    # print_lines(lines_after_remove)

    print('fix after comparison 2')
    letters_after = fix_issues_box_after_comparison(x, letters_after, img_src, WEIGHT_FILE)

    if intChar == ord(' '):  # save all new images in all_letters_sorted_by_prediction
        (_, code_to_letter) = init_letter_to_code()
        flag = False
        for letter in letters_after:
            rect = letter.rect
            img_to_save = img_src[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]
            # final_dst_dir = '{}/{}/{}'.format(f.split('.')[0],'all_letters_sorted_by_prediction', code_to_letter[letter._chr+1488])
            final_dst_dir = '{}{}/{}'.format('', 'all_letters_sorted_by_prediction',
                                             code_to_letter[letter._chr + 1488])
            if not os.path.exists(final_dst_dir):
                os.makedirs(final_dst_dir)
            cv2.imwrite('{}/{}.png'.format(final_dst_dir, randomword(20)), img_to_save)

    elif intChar == ord('+'):
        MIN_CONTOUR_AREA = MIN_CONTOUR_AREA + 10
    elif intChar == ord('-'):
        MIN_CONTOUR_AREA = MIN_CONTOUR_AREA - 10
    elif intChar == 27:
        flag = False
    # elif intChar == ord('s'):
    #     flag = False
    #     text_hebrew = [chr(let._chr + 1488) for let in letters_after]
    #     text_code = [let._chr for let in letters_after]
    #     a=''.join(text_hebrew)
    #
    #     import io
    #     with io.open('kiyeviaha.txt', 'w', encoding='UTF-16') as file:
    #         for c in a:
    #             print(c,file=file)
    elif intChar == ord('c'):  # compare with original text

        x = compare_with_right_paracha(letters_after)
        print('=================================== comparison result =======================================')
        print_result(x, letters_after)

        cv2.destroyAllWindows()
        show_img_with_rect(letters_after, img_src, True, False)
        cv2.waitKey(0)

        img_res = get_image_result(letters_after, img_src)
        json_res = "{{'img':'{}'}}".format(img_res)
        return json_res

        #flag = False

    cv2.destroyAllWindows()  # remove windows from memory


def check_imsage64(b64):
    img = base64.b64decode(b64)
    npimg = np.fromstring(img, dtype=np.uint8)
    img_src = cv2.imdecode(npimg, 1)

    return check_image(img_src)


def check(uploaded_file_url):
    img = cv2.imread(uploaded_file_url)
    return check_image(img)






def test():
    print("TEST - SUCCESS")

def main():

    src='../images/a'
    files = listdir(src)
    for f in files:
        print('========================{}====================================='.format(f))
        img_src = cv2.imread('{}/{}'.format(src, f))
        check_image(img_src)

    return


###################################################################################################
if __name__ == "__main__":
    # import base64
    # f = open('images/a/20190409_222150.jpg', "rb")
    # data = bytearray(f.read())
    # b64 =  base64.b64encode(data)
    # check_imsage64(b64)


    main()
# end if




#20190227_150140.jpg -- 10 resize:0.5
#20190303_163738.jpg -- 9
#20190226_182655.jpg --9 error on pe - la barre du kuf a ete prise avec le lamded de la ligne en dessous
#20190226_134828.jpg -- 9 youd en plus. c'est le haut du lamed qui a ete pris avec la ligne du dessus
######################