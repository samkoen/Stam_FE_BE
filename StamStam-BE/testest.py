import pytesseract
import cv2
from pytesseract import Output
import difflib
from dateutil.parser import parse
import re
from statistics import mean



def close_match(text, answers, cache):
    print('\ntext: ', text)
    date = False
    email = False
    tel = False
    url = False
    for key, word_list in word_list_dict.items():
        if key == "DATE":
            date = True
        if key == "MAIL":
            email = True
        if key == "TEL":
            tel = True
        if key == "URL":
            url = True
        key_ratio = []
        num_list = []
        for word in word_list:
            for index, t in enumerate(text.split()):
                m = difflib.SequenceMatcher(None, word, t)
                r = round(m.quick_ratio(), 3)
                if r > 0.6:
                    num = closest_num(text, t, date, email, tel, url)
                    # print(word, ' - ', num, ' - ', r)
                    if num == None:
                        r = 0
                    else:
                        num_list.append(num)
                    key_ratio.append(r)
        if key_ratio != [] and num_list != []:
            avr = mean(key_ratio)
            common_num = most_common(num_list)
            print('\n key: ', key)
            print("common_num: ", common_num)
            print("avr: ", avr)
            if avr > cache[key]:
                answers[key] = (avr, common_num)
            cache[key] = avr
            # print(key, ' - ', avr, ' - ', text)
    # print('answers: ', answers)
    # return answers

# close_match(text)


def boxes():
    # https: // stackoverflow.com / questions / 20831612 / getting - the - bounding - box - of - the - recognized - words - using - python - tesseract
    img = cv2.imread('images/8.jpg')
    height = img.shape[0]
    width = img.shape[1]

    h, w = img.shape[:2]
    cv2.namedWindow('jpg', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('jpg', w, h)
    # cv2.imshow('jpg', c)

    # d = pytesseract.image_to_boxes(img, lang='heb', output_type=Output.DICT)
    d = pytesseract.image_to_boxes(img, lang='heb', output_type=Output.DICT)
    print(d.keys())
    n_boxes = len(d['char'])
    for i in range(n_boxes):
        (text, x1, y2, x2, y1) = (d['char'][i], d['left'][i], d['top'][i], d['right'][i], d['bottom'][i])
        print(text, ' - x1:{}, y2:{}, x2:{}, y1:{} - page:{}'.format(x1, y2, x2, y1, d['page'][i]))
        cv2.rectangle(img, (x1, height-y1), (x2, height-y2), (0, 255, 0), 2)
    cv2.imshow('jpg', img)
    cv2.waitKey(0)
# boxes()


def data():
    # https://stackoverflow.com/questions/20831612/getting-the-bounding-box-of-the-recognized-words-using-python-tesseract
    img = cv2.imread('images/8.jpg')
    d = pytesseract.image_to_data(img, lang='heb', output_type=Output.DICT)
    n_boxes = len(d['text'])
    # print(d.keys())
    line_dict = {key: [] for key in d['line_num']}
    # line_dict.fromkeys(d['line_num'])
    # line_list = []
    for i in range(n_boxes):
        block_num = d['block_num'][i]
        line_num = d['line_num'][i]
        text = d['text'][i]
        if text != '':
            line_dict[line_num].append(text)

        (x, y, w, h) = (d['left'][i], d['top'][i], d['width'][i], d['height'][i])
        # print('{} - x1:{}, y2:{}, x2:{}, y1:{} - level:{}, conf:{}, block_num:{}, par_num:{}, line_num:{}, word_num:{}'.
        #       format(d['text'][i], x, y, w, h, d['level'][i], d['conf'][i], block_num, d['par_num'][i],
        #              line_num, d['word_num'][i])
        #       )
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(img, str(line_num), (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (36, 255, 12), 2)
    # print(line_dict)
    answers = {}
    cache = dict.fromkeys(word_list_dict, 0)
    for line_num, line in line_dict.items():
        # print("line number: ", line_num)
        if line != []:
            close_match(' '.join(line), answers, cache)
    print('answers: ', answers)
    # height, width = img.shape[:2]
    # cv2.namedWindow('img', cv2.WINDOW_NORMAL)
    # cv2.resizeWindow('img', width, height)
    # cv2.imshow('img', img)
    # cv2.waitKey(0)

data()


def digits():
    img = cv2.imread('images/8.jpg')
    text = pytesseract.image_to_string(img, config='digits')
    print(text)

# digits()