import os
import sys
import csv
import urllib
import re

from PIL import Image # http://www.pythonware.com/products/pil/
import ImageFilter

import enchant # http://www.rfk.id.au/software/pyenchant/
# for MacOS 10.5 I used http://www.rfk.id.au/software/pyenchant/download.html
# with pyenchant-1.6.3-py2.5-macosx-10.4-universal.dmg

# This recognition system depends on:
# http://code.google.com/p/tesseract-ocr/
# version 2.04, it must be installed and compiled already

# plaque_transcribe_test5.py
# run it with 'cmdline> python plaque_transcribe_test5.py easy_blue_plaques.csv'
# and it'll:
# 1) send images to tesseract
# 2) read in the transcribed text file
# 3) convert the text to lowercase
# 4) use a Levenshtein error metric to compare the recognised text with the
# human supplied transcription (in the plaques list below)
# 5) write error to file

# For more details see:
# http://aicookbook.com/wiki/Automatic_plaque_transcription

def load_csv(filename):
    """build plaques structure from CSV file"""
    plaques = []
    plqs = csv.reader(open(filename, 'rb'))#, delimiter=',')
    for row in plqs:
        image_url = row[1]
        text = row[2]
        # ignore id (0) and plaque url (3) for now
        last_slash = image_url.rfind('/')
        filename = image_url[last_slash+1:]
        filename_base = os.path.splitext(filename)[0] # turn 'abc.jpg' into 'abc'
        filename = filename_base + '.tif'        
        root_url = image_url[:last_slash+1]
        plaque = [root_url, filename, text]
        plaques.append(plaque)
    return plaques

def levenshtein(a,b):
    """Calculates the Levenshtein distance between a and b
       Taken from: http://hetland.org/coding/python/levenshtein.py"""
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n
        
    current = range(n+1)
    for i in range(1,m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
            
    return current[n]

def transcribe_simple(filename):
    """Convert image to TIF, send to tesseract, read the file back, clean and
    return"""
    # read in original image, save as .tif for tesseract
    im = Image.open(filename)
    filename_base = os.path.splitext(filename)[0] # turn 'abc.jpg' into 'abc'
    
    #Enhance contrast
    #contraster = ImageEnhance.Contrast(im)
    #im = contraster.enhance(3.0)
    im = crop_to_plaque(im)
    im = convert_to_bandl(im)
    
    filename_tif = 'processed' + filename_base + '.tif'
    im.save(filename_tif, 'TIFF')

    # call tesseract, read the resulting .txt file back in
    cmd = 'tesseract %s %s -l eng nobatch goodchars' % (filename_tif, filename_base)
    print "Executing:", cmd
    os.system(cmd)
    input_filename = filename_base + '.txt'
    input_file = open(input_filename)
    lines = input_file.readlines()
    line = " ".join([x.strip() for x in lines])
    input_file.close()
    # delete the output from tesseract
    os.remove(input_filename)

    # convert line to lowercase
    transcription = line.lower()
    
    #Remove gaps in year ranges
    transcription = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1-\2", transcription)
    transcription = re.sub(r"([0-9il\)]{4})", clean_years, transcription)
    
    #Separate words
    d = enchant.Dict("en_GB")
    newtokens = []
    print 'Prior to post-processing: ', transcription
    tokens = transcription.split(" ")
    for token in tokens:
        if (token == 'i') or (token == 'l') or (token == '-'):
            pass
        elif token == '""':
            newtokens.append('"')
        elif token == '--':
            newtokens.append('-')
        elif len(token) > 2:
            if d.check(token):
                #Token is a valid word
                newtokens.append(token)
            else:
                #Token is not a valid word
                suggestions = d.suggest(token)
                if len(suggestions) > 0:
                    #If the spell check has suggestions take the first one
                    newtokens.append(suggestions[0])
                else:
                    newtokens.append(token)
        else:
            newtokens.append(token)
            
    transcription = ' '.join(newtokens)

    return transcription
    
def clean_years (m):
    digits = m.group(1)
    year = []
    for digit in digits:
        if digit == 'l':
            year.append('1')
        elif digit == 'i':
            year.append('1')
        elif digit == ')':
            year.append('3')
        else:
            year.append(digit)
    return ''.join(year)
    
def crop_to_plaque (srcim):
    
    scale = 0.25
    wkim = srcim.resize((int(srcim.size[0] * scale), int(srcim.size[1] * scale)))
    wkim = wkim.filter(ImageFilter.BLUR)
    #wkim.show()
    
    width = wkim.size[0]
    height = wkim.size[1]
    
    #result = wkim.copy();
    highlight_color = (255, 128, 128)
    R,G,B = 0,1,2
    lrrange = {}
    for x in range(width):
        lrrange[x] = 0
    tbrange = {}
    for y in range(height):
        tbrange[y] = 0
    
    for x in range(width):    
        for y in range(height):
            point = (x,y)
            pixel = wkim.getpixel(point)
            if (pixel[B] > pixel[R] * 1.2) and (pixel[B] > pixel[G] * 1.2):
                lrrange[x] += 1
                tbrange[y] += 1
                #result.putpixel(point, highlight_color)
    
        
    #result.show();
    
    left = 0
    right = 0 
    cutoff = 0.15      
    for x in range(width):
        if (lrrange[x] > cutoff * height) and (left == 0):
            left = x
        if lrrange[x] > cutoff * height:
            right = x

    top = 0
    bottom = 0
    for y in range(height):
        if (tbrange[y] > cutoff * width) and (top == 0):
            top = y
        if tbrange[y] > cutoff * width:
            bottom = y
    
    left = int(left / scale)
    right = int(right / scale)
    top = int(top / scale)
    bottom = int(bottom / scale)
    
    box = (left, top, right, bottom)
    region = srcim.crop(box)
    #region.show()
    
    return region
    
def convert_to_bandl (im):
    width = im.size[0]
    height = im.size[1]
    
    white = (255, 255, 255)
    black = (0, 0, 0)
    R,G,B = 0,1,2
    
    for x in range(width):
        for y in range(height):
            point = (x,y)
            pixel = im.getpixel(point)
            if (pixel[B] > pixel[R] * 1.2) and (pixel[B] > pixel[G] * 1.2):
                im.putpixel(point, white)
            else:
                im.putpixel(point, black)
    #im.show()
    return im
    

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 2:
        print "Usage: python plaque_transcribe_demo.py plaques.csv (e.g. \
easy_blue_plaques.csv)"
    else:
        plaques = load_csv(sys.argv[1])

        results = open('results.csv', 'w')

        for root_url, filename, text in plaques:
            print "----"
            print "Working on:", filename
            transcription = transcribe_simple(filename)
            print "Transcription: ", transcription
            print "Text: ", text
            error = levenshtein(text, transcription)
            assert isinstance(error, int)
            print "Error metric:", error
            results.write('%s,%d\n' % (filename, error))
            results.flush()
        results.close()

