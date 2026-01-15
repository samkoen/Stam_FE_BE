import base64
import gc
import os
from os import listdir

import cv2
import numpy as np

from first_processing import get_contour,resize
from ocr.Letter import image_to_letters,show_img_with_rect,sort_contour,fix_issues_box
from rect_util import union_many

WEIGHT_FILE = 'ocr/model/output/Nadam_beta_1_256_30.hdf5'
WEIGHT_FILE_1 = 'ocr/model/output/Adadelta_decay_256_30.hdf5'
WEIGHT_FILE_2 = 'ocr/model/output/Adamax_beta_1_256_30.hdf5'




def print_lines(lines):
    print('=====================================')
    i=0
    for line in lines:
        a = [let.real_chr for let in line]
        print('{} - {}'.format(i,''.join(a)))
        i=i+1

import diff_match_patch as dmp_module

def read_source_text(src):
    src_txt = []
    import io
    with io.open(src, 'r', encoding='UTF-16') as file:
        for line in file:
            src_txt.append(line.rstrip())
    return src_txt


def compare_with_right_paracha(letters_after):
    text_hebrew = [chr(let._chr + 1488) for let in letters_after]
    current = ''.join(text_hebrew)
    dmp = dmp_module.diff_match_patch()

    # Utiliser le chemin vers overflow/ pour les fichiers texte
    base_path = os.path.join(os.path.dirname(__file__), 'overflow')
    paracha_files = ['chema.txt', 'chamoa.txt', 'kadesh.txt', 'kiyeviaha.txt', 'mezuza.txt']
    paracha_names = ['Chema', 'Chamoa', 'Kadesh', 'Kiyeviaha', 'Mezuza']
    
    src_txt = [''.join(read_source_text(os.path.join(base_path, f))) for f in paracha_files]

    x = [dmp.diff_main(src, current) for src in src_txt]
    best_match = min(enumerate(x), key=lambda k: len(k[1]))
    paracha_index = best_match[0]
    paracha_name = paracha_names[paracha_index]
    
    return best_match[1], paracha_name

def print_result(x, letters):
    if len(x)==0:
        print('success')
        return

    [x.reset_status() for x in letters]
    i = 0
    idx = 0
    while i < len(x):
        try:
            st = x[i]
            if st[0] == 0:
                idx = idx + len(st[1])
            elif st[0] == -1 and i + 1 < len(x) and x[i + 1][0] == 1:
                for let_err in letters[idx:idx+len(x[i + 1][1])]:
                    let_err.status = "wrong"
                    let_err.error = True
                    let_err.err_msg = "error: {} instead of {} at {}".format(x[i + 1][1], st[1], idx)
                    print(let_err.err_msg)
                    idx = idx+1
                #idx = idx + len(x[i + 1][1])
                i = i + 1

            elif st[0] == -1:
                let_err = letters[idx]
                let_err.status = "missing"
                let_err.missing = True
                let_err.err_msg = "missing {} at {}".format(st[1], idx)
                print(let_err.err_msg)
                idx = idx
            elif st[0] == 1:
                for let_err in letters[idx:idx + len(st[1])]:
                    # let_err = letters_after[idx]
                    let_err.status = "superflus"
                    let_err.error = True
                    let_err.err_msg = "superflus {} at {}".format(let_err.real_chr, idx)
                    print(let_err.err_msg)
                    idx = idx + 1
        except Exception as e:
            pass
        i = i + 1

def get_reference_letter(letters,idx):
    if letters[idx - 1].in_same_line(letters[idx]):
        reference_letter = letters[idx - 1]
    elif letters[idx + 1].in_same_line(letters[idx]):
        reference_letter = letters[idx + 1]
    else:
        reference_letter = None
    return reference_letter

def minusone_one_case(letters, idx, i, cmp_result, img_src, letters_to_delete,show=False): # -1 and next is 1

    current_cmp = cmp_result[i]
    next_cmp = cmp_result[i+1]
    missing_letters = current_cmp[1]
    missing_letters_nb = len(missing_letters)
    unncecessary_letters = next_cmp[1]
    unncecessary_letters_nb = len(unncecessary_letters)

    a = letters[idx].rect
    un = (a[0]-10, a[1] - 15, a[2]+10, a[3] + 40)

    err_msg = "error: {} instead of {} at {}".format(unncecessary_letters, missing_letters, idx)
    print(err_msg)
    if missing_letters_nb == unncecessary_letters_nb:
        #reference_letter = get_reference_letter(letters,idx)
        new_letters = separate_letter(un, img_src,WEIGHT_FILE_1,show=show)
        n = ''.join([x.real_chr for x in new_letters])
        if n != missing_letters:
            new_letters = separate_letter(un, img_src, WEIGHT_FILE_2,show=show)
            n = ''.join([x.real_chr for x in new_letters])
        if n == missing_letters:
            [n.set_line_nb(letters[idx].line_nb) for n in new_letters]
            for i in range(0, len(missing_letters)):
                letters[idx] = new_letters[i]
                idx = idx + 1
            return (idx ,True)
        else:
            return (idx, False)

    elif missing_letters_nb > unncecessary_letters_nb:
        un = union_many([x.rect for x in letters[idx:idx + unncecessary_letters_nb]])
        new_letters = separate_letter(un, img_src, WEIGHT_FILE,action_on_img='erose',show=show)
        n = ''.join([x.real_chr for x in new_letters])
        if n == missing_letters:
            [n.set_line_nb(letters[idx].line_nb) for n in new_letters]
            letters[idx] = new_letters[0]
            [letters.insert(idx+i, x) for x, i in zip(new_letters[1:], range(1, len(new_letters)))]
            idx= idx+len(new_letters)
            return (idx,True)
        else:
            return (idx,False)

    elif missing_letters_nb < unncecessary_letters_nb:
        un = union_many([x.rect for x in letters[idx:idx + unncecessary_letters_nb]])
        new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='dilate',show=show)
        n = ''.join([x.real_chr for x in new_letters])
        if n == missing_letters:
            [n.set_line_nb(letters[idx].line_nb) for n in new_letters]
            for i in range(0,len(missing_letters)):
                letters[idx] = new_letters[i]
                idx=idx+1
            for i in range(idx, idx + unncecessary_letters_nb - missing_letters_nb):
                letters_to_delete.append(i)
                idx=idx+1
            #[letters.insert(idx + i, x) for x, i in zip(new_letters[1:], range(1, len(new_letters)))]
            #idx = idx + len(new_letters)
            return (idx,True)
        else:
            return (idx,False)


def zero_minusone_case(letters, idx, i, cmp_result, img_src, letters_to_delete,show=False): # 0,-1

    current_cmp = cmp_result[i]
    next_cmp = cmp_result[i + 1]
    missing_letters = next_cmp[1]
    missing_letters_nb = len(missing_letters)
    last_good_letters = current_cmp[1]
    last_good_letters_nb = len(last_good_letters)

    a = letters[idx+last_good_letters_nb-1].rect
    un = (a[0] - 10, a[1] - 15, a[2] + 10, a[3] + 40)

    new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='erose',show=show)
    n = ''.join([x.real_chr for x in new_letters])
    m = letters[idx + last_good_letters_nb-1].real_chr + missing_letters
    if n == m:
        [n.set_line_nb(letters[idx+last_good_letters_nb-1].line_nb) for n in new_letters]
        letters[idx+last_good_letters_nb-1] = new_letters[0]
        [letters.insert(idx + i + last_good_letters_nb -1, x) for x, i in zip(new_letters[1:], range(1, len(new_letters)))]
        idx = idx + len(new_letters) + last_good_letters_nb -1
        return (idx,True)
    else:
        return (idx + last_good_letters_nb,False)

def minusone_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete,show=False): # -1,0

    current_cmp = cmp_result[i]
    next_cmp = cmp_result[i + 1]
    missing_letters = current_cmp[1]
    missing_letters_nb = len(missing_letters)
    next_good_letters = next_cmp[1]
    next_good_letters_nb = len(next_good_letters)

    a = letters[idx].rect
    un = (a[0] - 10, a[1] - 15, a[2] + 10, a[3] + 40)

    new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='erose',show=show)
    n = ''.join([x.real_chr for x in new_letters])
    m = missing_letters + letters[idx + next_good_letters_nb-1].real_chr
    if n!=m and len(m) == len(n):
        new_letters = separate_letter(un, img_src, WEIGHT_FILE_1, action_on_img='erose',show=show)
        n = ''.join([x.real_chr for x in new_letters])
        if n != m:
            new_letters = separate_letter(un, img_src, WEIGHT_FILE_2, action_on_img='erose',show=show)
            n = ''.join([x.real_chr for x in new_letters])

    if n == m:
        [n.set_line_nb(letters[idx+next_good_letters_nb-1].line_nb) for n in new_letters]
        letters[idx+next_good_letters_nb-1] = new_letters[0]
        [letters.insert(idx + i + next_good_letters_nb -1, x) for x, i in zip(new_letters[1:], range(1, len(new_letters)))]
        idx = idx + len(new_letters) + next_good_letters_nb -1
        return (idx,True)
    else:
        #return (idx + next_good_letters_nb,False)
        return (idx, False)

def zero_minusone_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete, show=False): # -1,0

    prev_cmp = cmp_result[i-1]
    next_cmp = cmp_result[i + 1]
    last_good_letters = prev_cmp[1]
    last_good_letters_nb_letters_nb = len(last_good_letters)
    next_good_letters = next_cmp[1]
    next_good_letters_nb = len(next_good_letters)

    current_cmp = cmp_result[i]
    missing_letters = current_cmp[1]
    missing_letters_nb = len(missing_letters)

    a = union_many([x.rect for x in letters[idx-1:idx+1]])
    un = (a[0], a[1] -  15, a[2], a[3] + 40)
    new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='erose',show=show)
    new_letters = new_letters[1:len(new_letters) - 1]
    n = ''.join([x.real_chr for x in new_letters])
    m = missing_letters
    if n == m:
        [n.set_line_nb(letters[idx].line_nb) for n in new_letters]
        [letters.insert(idx , x) for x, i in zip(new_letters, range(0, len(new_letters)))]
        idx = idx + len(new_letters) + next_good_letters_nb
        return (idx,True)
    else:
        #return (idx + next_good_letters_nb,False)
        return (idx, False)


def zero_minusone_one_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete, show=False): # -1,0

    prev_cmp = cmp_result[i-1]
    last_good_letters = prev_cmp[1]
    last_good_letters_nb_letters_nb = len(last_good_letters)

    current_cmp = cmp_result[i]
    missing_letters = current_cmp[1]
    missing_letters_nb = len(missing_letters)

    next_cmp = cmp_result[i + 1]
    uncessary_letters = next_cmp[1]
    uncessary_letters_nb = len(uncessary_letters)

    next_next_cmp = cmp_result[i + 2]
    next_good_letters = next_next_cmp[1]
    next_good_letters_nb = len(next_good_letters)


    a = union_many([x.rect for x in letters[idx-1:idx+1+uncessary_letters_nb]])
    un = (a[0], a[1] -  15, a[2], a[3] + 40)

    # if missing_letters_nb == uncessary_letters_nb:
    #     new_letters = separate_letter(letters[idx].rect, img_src,WEIGHT_FILE_1,show=show)
    #     n = ''.join([x.real_chr for x in new_letters])
    #     if n != missing_letters:
    #         new_letters = separate_letter(letters[idx].rect, img_src, WEIGHT_FILE_2)
    #     if n == missing_letters:
    #         [n.set_line_nb(letters[idx].line_nb) for n in new_letters]
    #         for i in range(0, len(missing_letters)):
    #             letters[idx] = new_letters[i]
    #             idx = idx + 1
    #         return (idx ,True)
    #     else:
    #         return (idx, False)

    if missing_letters_nb == uncessary_letters_nb:
        new_letters = separate_letter(un, img_src,WEIGHT_FILE_1,show=show)
        new_letters_a = new_letters[1:len(new_letters) - 1]
        n = ''.join([x.real_chr for x in new_letters_a])
        if n != missing_letters:
            new_letters = separate_letter(un, img_src, WEIGHT_FILE_2)

    if missing_letters_nb < uncessary_letters_nb:
        new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='dilate',show=False)
    elif missing_letters_nb > uncessary_letters_nb:
        new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='erose', show=False)

    new_letters = new_letters[1:len(new_letters) - 1]
    n = ''.join([x.real_chr for x in new_letters])
    m = missing_letters
    if n == m:
        [n.set_line_nb(letters[idx].line_nb) for n in new_letters]
        #[letters.insert(idx , x) for x, i in zip(new_letters, range(0, len(new_letters)))]
        for i in range(0, len(new_letters)):
            letters.insert(idx,new_letters[i])
            idx = idx + 1
        for i in range(0,uncessary_letters_nb):
            letters_to_delete.append(idx)
            idx=idx+1
        return (idx,True)
    else:
        #return (idx + next_good_letters_nb,False)
        return (idx, False)

def zero_one_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete, show=False): # -1,0


    prev_cmp = cmp_result[i-1]
    last_good_letters = prev_cmp[1]
    last_good_letters_nb_letters_nb = len(last_good_letters)

    current_cmp = cmp_result[i]
    uncessary_letters = current_cmp[1]
    uncessary_letters_nb = len(uncessary_letters)

    next_cmp = cmp_result[i + 1]
    next_good_letters = next_cmp[1]
    next_good_letters_nb = len(next_good_letters)

    if not letters[idx - 1].in_same_line(letters[idx + 1 + uncessary_letters_nb]):
        return (idx, False)

    a = union_many([x.rect for x in letters[idx-1:idx+1+uncessary_letters_nb]])
    un = (a[0], a[1] -  15, a[2], a[3] + 40)
    new_letters = separate_letter(un, img_src, WEIGHT_FILE, action_on_img='dilate',show=show)
    #new_letters = new_letters[1:len(new_letters) - 1]
    n = ''.join([x.real_chr for x in new_letters])
    if len(n)==2:
        for i in range(0,uncessary_letters_nb):
            letters_to_delete.append(idx)
            idx=idx+1
        return (idx,True)
    else:
        #return (idx + next_good_letters_nb,False)
        return (idx, False)

def fix_issues_box_after_comparison(cmp_result,letters,img_src,show = False):

    letters_to_delete=[] #list of indexes to delete from letters
    i = 0
    idx = 0
    while i < len(cmp_result):
        try:
            st = cmp_result[i]
            if st[0] == 0:
                if letters[idx].real_chr!=cmp_result[i][1][0]:
                    print("error in idx")

                if i + 1 < len(cmp_result) and cmp_result[i + 1][0] == -1:#(0,-1)
                    if i + 1 >=  len(cmp_result) or (i + 2 < len(cmp_result) and cmp_result[i + 2][0] != 1):
                        (idx, success) = zero_minusone_case(letters, idx, i, cmp_result, img_src, letters_to_delete,show=show)
                        if success:
                            i=i+1
                    else:
                        idx = idx + len(st[1])
                else:
                    idx = idx + len(st[1])
            elif st[0] == -1:
                if i + 1 < len(cmp_result) and cmp_result[i + 1][0] == 1:#few letters were read not correctly (-1,1)
                    (idx,success) = minusone_one_case(letters, idx, i, cmp_result, img_src, letters_to_delete,show=show)
                    if not success and i > 0 and cmp_result[i - 1][0] == 0 \
                        and i + 2 < len(cmp_result) and cmp_result[i + 2][0] == 0 and letters[idx-1].in_same_line(letters[idx+1]): #(0,-1,1,0)
                        (idx, success) = zero_minusone_one_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete, show=show)
                    if success:
                        i = i + 1
                    else:
                         i=i
                elif i + 1 < len(cmp_result) and cmp_result[i + 1][0] == 0:  # few letters were read not correctly (-1,0)
                    (idx, success) = minusone_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete,show=show)
                    if not success and i > 0 and cmp_result[i - 1][0] == 0 and letters[idx-1].in_same_line(letters[idx+1]): #(0,-1,0)
                        (idx, success) = zero_minusone_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete, show=show)
                    if success:
                        i=i+1
                    else:
                        i=i
            # elif st[0] == -1 and i > 0 and cmp_result[i-1][0]==0: #(0,-1)
            #     (idx, success) = second_case(letters, idx, i, cmp_result, img_src, letters_to_delete)

            elif st[0] == 1:
                success=False
                if i > 0 and cmp_result[i - 1][0] == 0:
                    (idx, success) = zero_one_zero_case(letters, idx, i, cmp_result, img_src, letters_to_delete, show=show)
                if not success:
                    for let_err in letters[idx:idx + len(st[1])]:
                        err_msg = "superflus {} at {}".format(let_err.real_chr, idx)
                        print(err_msg)
                        idx = idx + 1
                # fixed = False
                # if len(st[1])==1:
                #     if i>0 and cmp_result[i - 1][0]==0: #the previous letter + the current letter is the same letter as previous letter
                #         un1 = letter_union(letters[idx-1].rect,letters[idx].rect, img_src, WEIGHT_FILE)
                #         if un1.real_chr == letters[idx-1].real_chr:
                #             letters_to_delete.append(idx)
                #             letters[idx-1] = un1
                #             fixed=True
                #
                #     if not fixed and i < len(cmp_result) - 1 and cmp_result[i + 1][0] == 0:  # the next letter + the current letter is the same letter as previous letter
                #         un2 = letter_union(letters[idx + 1].rect, letters[idx].rect, img_src, WEIGHT_FILE)
                #         if un2.real_chr == letters[idx + 1].real_chr:
                #             letters_to_delete.append(idx)
                #             letters[idx + 1] = un2
                #
                #             fixed=True
                #
                # if True: #not fixed:
                #     for let_err in letters[idx:idx + len(st[1])]:
                #         err_msg = "superflus {} at {}".format(let_err.real_chr, idx)
                #         print(err_msg)
                #         idx = idx + 1
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

def remove_wrong_line(lines,letters):
    # reduce(lambda ex, c: ex and c.error, lines[15], True)
    # [l.set_line_nb(0) for l in lines[0] if reduce(lambda ex, c: ex and c.error, lines[0], True)]
    from functools import reduce
    [[letter.set_status('XXX') for letter in line if reduce(lambda ex, c: ex and c.error, line, True)] for line in
     lines]
    letters_to_return = [let for let in letters if let.status != 'XXX']
    return letters_to_return


def separate_letter(rect, img, model,same_line_as='first', action_on_img='',show=False):

    #from forX import get_npa_contour

    z = np.ones(img.shape, dtype=np.uint8) * 255
    img_s = img[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]
    z[rect[1]: rect[1] + rect[3], rect[0]: rect[0] + rect[2]] = img_s

    imgTraining = z.copy()
    #(x,npaContours,y) = get_npa_contour(imgTraining,6)
    if action_on_img=='erose':
        npaContours = get_contour(imgTraining, erose=True,gshow = show)
    elif action_on_img=='dilate':
        npaContours = get_contour(imgTraining, dilate=True,gshow = show)
    else:
        npaContours = get_contour(imgTraining,gshow = show)
    letters = image_to_letters(npaContours, imgTraining, model)

    letters, lines = sort_contour(letters,img)
    # show_img_with_rect(None, letters, img, print_letter_flag=True)
    # cv2.waitKey(0)

    if same_line_as == 'first':
        letters = [let for let in letters if letters[0].in_same_line(let)]
    elif same_line_as == 'last':
        letters = [let for let in letters if letters[len(letters)-1].in_same_line(let)]
    #sort_contour_one_line(letters)

    # show_img_with_rect(letters, imgTraining, print_letter_flag=True)
    # cv2.destroyAllWindows()

    fix_issues_box(letters, z, model)
    # show_img_with_rect(letters, z, print_letter_flag=True)
    return letters

def get_image_result(letters,img):
    img=img.copy()

    i=0
    for letter in letters:  # for each contour
        rect = letter.rect
        # Dessiner tous les rectangles avec les bonnes couleurs :
        # Vert (0, 255, 0) pour les lettres justes (status="OK")
        # Rouge (0, 0, 255) pour les lettres manquantes (status="missing")
        # Bleu (255, 0, 0) pour les lettres en trop (status="superflus" ou "wrong")
        if letter.status == "OK" or letter.status == "OKK":
            color = (0, 255, 0)  # Vert pour les lettres justes
        elif letter.status == "missing":
            color = (0, 0, 255)  # Rouge pour les lettres manquantes
        elif letter.status in ['wrong', 'superflus']:
            color = (255, 0, 0)  # Bleu pour les lettres en trop
        else:
            color = (0, 255, 0)  # Par défaut vert
        
        cv2.rectangle(img,  # draw rectangle on original training image
                      (rect[0], rect[1]),  # upper left corner
                      (rect[0] + rect[2], rect[1] + rect[3]),  # lower right corner
                      color,
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


def check_image(img_src,f):
    if img_src is None:  # if image was not read successfully
        print("error: image not read from file \n\n")  # print error message to std out
        os.system("pause")  # pause so user can see error message
        return  # and exit function (which exits program)
        # end if

    img_src = resize(img_src)
    imgTraining = img_src.copy()

    npaContours = get_contour(imgTraining,gshow=True,name=f)
    letters = image_to_letters(npaContours, img_src, WEIGHT_FILE)
    if len(letters) == 0:
        exit(0)
    intChar = ord('c')
    #letters_after, intChar,wrong = manual_filter(letters_after, imgTraining)
    show_img_with_rect(f,letters, img_src,mouse_flag=True, print_letter_flag=False)
    cv2.waitKey(0)

    #width_mean = sum(l.rect[2] for l in letters) / len(letters)
    letters, lines = sort_contour(letters, img_src)
    show_img_with_rect(f, letters, img_src, print_letter_flag=True)
    cv2.waitKey(0)


    print_lines(lines)
    print('remove superfluous rect')
    fix_issues_box(letters, img_src, WEIGHT_FILE)
    cv2.destroyAllWindows()
    # show_img_with_rect(f,letters, img_src, print_letter_flag=False)
    # cv2.waitKey(0)

    print('compare 1')
    x, _ = compare_with_right_paracha(letters)
    print_result(x, letters)
    # remove_wrong_line(lines,letters_after)
    # cv2.destroyAllWindows()
    # show_img_with_rect(letters_after, img_src, True, False)
    # cv2.waitKey(0)
    print('remove wrong lines')
    letters = remove_wrong_line(lines, letters)

    x, _ = compare_with_right_paracha(letters)
    print_result(x, letters)

    print('fix after comparison 1')
    letters = fix_issues_box_after_comparison(x, letters, img_src,show=False)

    print('compare 2')


    # _, lines_after_remove = sort_contour(letters_after, img_src)
    # print_lines(lines_after_remove)

    x, _ = compare_with_right_paracha(letters)
    print_result(x, letters)
    print('fix after comparison 2')
    letters = fix_issues_box_after_comparison(x, letters, img_src,show=False)

    #print_stat(letters,img_src)
    intChar = ord('c')

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

        x, _ = compare_with_right_paracha(letters)
        print('=================================== comparison result =======================================')
        print_result(x, letters)

        cv2.destroyAllWindows()
        show_img_with_rect(f,letters, img_src, True, False)
        cv2.waitKey(0)

        img_res = get_image_result(letters, img_src)
        json_res = "{{'img':'{}'}}".format(img_res)
        return json_res

        #flag = False

    cv2.destroyAllWindows()  # remove windows from memory


def main():
    # src = 'images/for aviad/1.jpg'
    # img_src = cv2.imread(src)
    # check_image(img_src,None)


    src='images/a'
    files = listdir(src)
    for f in files:
        gc.collect()
        print('========================{}====================================='.format(f))
        img_src = cv2.imread('{}/{}'.format(src, f))
        if not f.__contains__('result'):
            check_image(img_src,f)



if __name__ == "__main__":
    main()





# def first_case(letters,idx,i,cmp_result,img_src,letters_to_delete):
#     st = cmp_result[i]
#     let_err = letters[idx]
#     err_msg = "error: {} instead of {} at {}".format(cmp_result[i + 1][1], st[1], idx)
#     print(err_msg)
#     if len(cmp_result[i + 1][1]) == 2:
#         un = letter_union(letters[idx].rect, letters[idx + 1].rect, img_src, WEIGHT_FILE)
#         if un.real_chr == st[1]:
#             letters_to_delete.append(idx + 1)
#             letters[idx] = un
#             print('{}: unify {} to {}'.format(idx, cmp_result[i + 1][1], un.real_chr))
#     elif len(cmp_result[i + 1][1]) == 1 and len(st[1]) == 1:
#         un = letter_union(letters[idx].rect, letters[idx].rect, img_src, WEIGHT_FILE_1)
#         if un.real_chr == st[1]:
#             letters[idx] = un
#             print('{}: new prediction of {} using {}: {}'.format(idx, cmp_result[i + 1][1], WEIGHT_FILE_1, un.real_chr))
#         else:
#             un = letter_union(letters[idx].rect, letters[idx].rect, img_src, WEIGHT_FILE_2)
#             if un.real_chr == st[1]:
#                 letters[idx] = un
#                 print('{}: new prediction of {} using {}: {}'.format(idx, cmp_result[i + 1][1], WEIGHT_FILE_2,
#                                                                      un.real_chr))
#             else:
#                 new_letters = separate_letter(letters[idx].rect, img_src)
#                 letters[idx].set_separate_letters(new_letters)
#                 print('{}: {} is in fact {}'.format(idx, cmp_result[i + 1][1],
#                                                     ''.join([let.real_chr for let in new_letters])))
#     elif len(cmp_result[i + 1][1]) == 1 and len(st[1]) > 1:
#         new_letters = separate_letter(letters[idx].rect, img_src)
#         letters[idx].set_separate_letters(new_letters)
#         print('{}: {} is in fact {}'.format(idx, cmp_result[i + 1][1],
#                                             ''.join([let.real_chr for let in new_letters])))
