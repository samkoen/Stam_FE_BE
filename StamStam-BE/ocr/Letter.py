class Letter:
    def __init__(self,rect,_chr,img,npa_contour=None):
        self.rect = rect
        self.img = img
        self.status="OK"
        self.error = False
        self.missing = False
        self.err_msg = None
        self.set_prediction(_chr)
        self.npa_contour = npa_contour
        self.separate_letters = None
        self.line_nb = None

    def follow(self,let,widht_mean):
        #return math.isclose(self.rect[1],let.rect[1],abs_tol=30)
        s = max(self.rect[1], let.rect[1])
        h = min(self.rect[1] + self.rect[3], let.rect[1] + let.rect[3]) - s
        if ((self._chr==12 and h > 5) or (self._chr!=12 and h > 1)) and \
                (let.rect[0] - (self.rect[0]+self.rect[2])) < widht_mean*8  : #if there is height in common and self.x is near let.x
            return h
        return None

    def follow_top_to_bottom(self,let,height_mean):
        #return math.isclose(self.rect[1],let.rect[1],abs_tol=30)
        s = max(self.rect[0], let.rect[0])
        h = min(self.rect[0] + self.rect[2], let.rect[0] + let.rect[2]) - s
        if h > 0 and (let.rect[1] - (self.rect[1]+self.rect[3])) < height_mean*1  : #if there is height in common and self.x is near let.x
            return h
        return None

    def set_line_nb(self,i):
        self.line_nb = i

    def set_status(self,st):
        self.status = st

    def show(self,img_src):
        print('current: {} {}'.format(self._chr,self.real_chr))
        cv2.rectangle(img_src,  # draw rectangle on original training image
                      (self.rect[0], self.rect[1]),  # upper left corner
                      (self.rect[0] + self.rect[2], self.rect[1] + self.rect[3]),  # lower right corner
                      (0, 0, 255),  # red
                      2)  # thickness

        cv2.namedWindow("image_letters.png", cv2.WINDOW_NORMAL)
        cv2.imshow("image_letters.png", img_src)
        intChar = cv2.waitKey(0)  # get key press

    def unpredicted(self):
        return self._chr is None

    def set_prediction(self,pred):
        self._chr = pred
        if self._chr is not None:
            self.real_chr = chr(self._chr+1488)
        else:
            self.real_chr = None

    def set_separate_letters(self,new_letters):
        self.separate_letters = new_letters

    def in_same_line(self,other):
        return self.line_nb == other.line_nb

    def reset_status(self):
        self.status = "OK"
        self.error = False
        self.missing = False
        self.err_msg = None


import cv2
import numpy as np

from ocr.model import lenet_stam_predict
from rect_util import is_horizontal_include


def image_to_letters(npa_contours,img_src,WEIGHT_FILE):
    rects = []
    arr_img = []
    for npaContour in npa_contours:  # for each contour
        rect = [intX, intY, intW, intH] = cv2.boundingRect(npaContour)  # get and break out bounding rect
        rects.append(rect)

        img_rect = img_src[rect[1]:rect[1] + rect[3], rect[0]:rect[0] + rect[2]]
        img_rect = cv2.cvtColor(img_rect, cv2.COLOR_BGR2GRAY)
        img2828 = cv2.resize(img_rect, (28, 28))
        arr_img.append(img2828)

    testData = np.array(arr_img)

    predictions = lenet_stam_predict.predict(weight_file=WEIGHT_FILE, testData=testData)

    letters_val = list(zip(rects, arr_img, predictions,npa_contours))


    letters = [Letter(x[0], x[2], x[1], x[3] ) for x in letters_val if x[2] != 27]  # 27 is zevel
    #letters = [Letter(x[0], x[2], x[1], x[3]) for x in letters_val]  # 27 is zevel
    return letters

def show_img_with_rect(f,letters,img,mouse_flag=False,print_letter_flag = False):
    img=img.copy()
    def d(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for let in letters:
                if let.rect[0] < x < let.rect[0] + let.rect[2] and let.rect[1] < y < let.rect[1] + let.rect[3]:
                    #print("{} - {},msg: {}".format(let._chr,let.real_chr, let.err_msg))
                    print("current: {} ----- err msg: {}".format(let.real_chr,let.err_msg))

                    #break

    cv2.namedWindow(f, cv2.WINDOW_NORMAL)
    if mouse_flag:
        cv2.setMouseCallback(f, d)
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

        cv2.imshow(f, img)

        if print_letter_flag:
            print("{} letter: {} --- {}, line: {}".format(i,letter.rect, chr(letter._chr + 1488),letter.line_nb))
            intChar = cv2.waitKey(0)  # get key press
        i=i+1

    #cv2.imwrite("images/a/{}_result.png".format(f), img);
    # if flag:
    #     #cv2.setMouseCallback("image_letters.png", d)
    #     cv2.waitKey(0)


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

        # img = img_src.copy()
        # cv2.namedWindow("image_letters.png", cv2.WINDOW_NORMAL)
        # rect = letters[i].rect
        # cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (0, 0, 0), 5)
        # cv2.imshow("image_letters.png", img)
        # cv2.waitKey(0)



        follow_letters = []
        last_idx=-1
        while len(follow_letters)==0 and last_idx > -3:# this loop is for the case 2 letters are on same line, \
            #but they have no height in common (for example, yud and the bar of the kuf
            line = 0
            for current_line in lines:
                if len(current_line) < abs(last_idx):
                    line = line + 1
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

            if i > 1000:
                cv2.destroyAllWindows()
                img = img_src.copy()
                cv2.namedWindow("image_letters.png", cv2.WINDOW_NORMAL)
                rect = letters[i].rect
                cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (255, 0, 0), 5)
                cv2.imshow("image_letters.png", img)
                cv2.waitKey(0)

        else:
            if i> 1000    :
                cv2.destroyAllWindows()
                img = img_src.copy()
                cv2.namedWindow("image_letters.png", cv2.WINDOW_NORMAL)
                rect = letters[i].rect
                cv2.rectangle(img, (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3]), (0, 255, 0), 5)
                cv2.imshow("image_letters.png", img)
                cv2.waitKey(0)

                for f in follow_letters:
                    cv2.rectangle(img, (f[3].rect[0], f[3].rect[1]), (f[3].rect[0] + f[3].rect[2], f[3].rect[1] + f[3].rect[3]), (255, 0, 0), 5)
                    cv2.imshow("image_letters.png", img)
                f = max(follow_letters, key=lambda f: f[1])
                cv2.rectangle(img, (f[3].rect[0], f[3].rect[1]),
                              (f[3].rect[0] + f[3].rect[2], f[3].rect[1] + f[3].rect[3]), (0, 0, 255), 5)
                cv2.imshow("image_letters.png", img)
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

def sort_contour_one_line(letters):
    letters.sort(key=lambda b: b.rect[0] + b.rect[2], reverse=True)

def fix_issues_box(letters,img_src,WEIGHT_FILE):
    i = 0
    img = img_src.copy()
    show=False
    #cv2.namedWindow("fix_issue.png", cv2.WINDOW_NORMAL)
    while i < len(letters) - 1:
        #print('{} {}'.format(i, letters[i].real_chr))
        if i>5000 or show:
            rect = letters[i].rect
            cv2.rectangle(img,(rect[0], rect[1]),(rect[0] + rect[2], rect[1] + rect[3]),(0, 255, 0),2)
            cv2.imshow("fix_issue.png", img)
            cv2.waitKey(0)  # get key press
        un = is_horizontal_include(letters, i, img_src)
        if un:
            continue
        i = i +1
    unpredicted_letters = [let for let in letters if let.unpredicted()]
    if len(unpredicted_letters)>0:
        testData = [let.img for let in unpredicted_letters]
        testData = np.array(testData)
        predictions = lenet_stam_predict.predict(weight_file=WEIGHT_FILE, testData=testData)
        [let.set_prediction(pred) for let, pred in zip(unpredicted_letters, predictions)]


