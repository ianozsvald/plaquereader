import os
import sys
import csv
import urllib
import re

from PIL import Image # http://www.pythonware.com/products/pil/
from PIL import ImageOps, ImageDraw, ImageFilter

import enchant # http://www.rfk.id.au/software/pyenchant/
# Ian notes - for MacOS 10.5 I used http://www.rfk.id.au/software/pyenchant/download.html
# with pyenchant-1.6.3-py2.5-macosx-10.4-universal.dmg

# This recognition system depends on:
# http://code.google.com/p/tesseract-ocr/
# version 2.04, it must be installed and compiled already
# tesseract 3 (compiled from source) works but has worse recognition that 2.04

# Significant contributors:
# Ian Ozsvald 
# Jonathan Street

# Some notes:
# http://blog.aicookbook.com/2010/08/automatic-plaque-transcription-pytesseract-average-error-down-to-33-4/
# http://jonathanstreet.com/blog/ai-cookbook-competition
# http://ianozsvald.com/2010/04/04/tesseract-optical-character-recognition-to-read-plaques/

# For more details see:
# http://aicookbook.com/wiki/Automatic_plaque_transcription

# run it with 'cmdline> python transcribe_plaques.py easy_blue_plaques.csv'
# and it'll:
# 1) send images to tesseract
# 2) read in the transcribed text file
# 3) convert the text to lowercase
# 4) use a Levenshtein error metric to compare the recognised text with the
# human supplied transcription (in the plaques list below)
# 5) write error to file


PROGRESS_FILENAME = "progress.txt" # progress log

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

def clean_image(im):
    #Enhance contrast
    #contraster = ImageEnhance.Contrast(im)
    #im = contraster.enhance(3.0)
    im = crop_to_plaque(im) # cut to a box around the blue circle of the plaque
    #im = mask_with_circle(im) # mask around plaque to remove noisy backgrounds
    im = convert_to_bandl(im) # convert to black and white
    #im = ImageOps.grayscale(im) # convert to greyscale - doesn't improve results
    #im = ImageOps.posterize(im, 2) # convert to 2 colours (grey and black) - not useful
    return im

def transcribe_simple(filename, progress_file):
    """Convert image to TIF, send to tesseract, read the file back, clean and
    return"""
    # read in original image, save as .tif for tesseract
    im = Image.open(filename)
    filename_base = os.path.splitext(filename)[0] # turn 'abc.jpg' into 'abc'

    progress_file.write('----\n')
    progress_file.write(filename + '\n')
    
    im = clean_image(im)
    
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

    progress_file.write("raw  :" + line + '\n') 
    print "raw  :", line

    # convert line to lowercase
    transcription = line.lower()
    
    #Remove gaps in year ranges
    transcription = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1-\2", transcription)
    transcription = re.sub(r"([0-9il\)]{4})", clean_years, transcription)
    
    #Separate words
    d = enchant.Dict("en_GB")
    newtokens = []
    print 'cln1 :', transcription
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

    progress_file.write('trans:'+transcription+"\n")

    return transcription
    
def clean_years(m):
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
    
def crop_to_plaque(srcim):
    
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
    
    # hack by Ian, if image is bw then the above detection won't work
    # and left/right/top/bottom are each set to 0
    if left == 0 and right == 0 and top == 0 and bottom == 0:
        assert False # we shouldn't get here unless we have a bw input image?
        right = int(width / scale)
        bottom = int(height / scale)

    box = (left, top, right, bottom)
    print "crop box:", box

    region = srcim.crop(box)
    #region.show()
    
    return region

def mask_with_circle(im):
    """use a mask to blank outside the plaque (e.g. to get rid of
    speckles/lines from brickwork), leaving the plaque untouched"""
    # taken from http://stackoverflow.com/questions/890051/how-do-i-generate-circuar-thumbnails-with-pil/890114#890114
    size = im.size
    mask = Image.new('L', size, 255) # define a white image mask
    draw = ImageDraw.Draw(mask) # turn the mask into a new Image (bw)
     # fill with a black circle that touches the sides of the box
    draw.ellipse((0, 0) + size, fill=0)
    # fit the mask over the original image
    output = ImageOps.fit(im, mask.size, centering=(0.5, 0.5))
    # paste mask over image, black border (outside of circle) is pasted 
    # over the original image but white centre (inside circle) is unchanged
    output.paste(0, mask=mask)
    return output
    
    
def convert_to_bandl(im):
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

if __name__ == '__main__':# and False:
    argc = len(sys.argv)
    if argc != 2:
        print "Usage: python plaque_transcribe_demo.py plaques.csv (e.g. \
easy_blue_plaques.csv)"
    else:
        plaques = load_csv(sys.argv[1])

        results = open('results.csv', 'w')
        progress_file = open(PROGRESS_FILENAME, 'w')

        for root_url, filename, text in plaques:
            print "----"
            print "Working on:", filename
            transcription = transcribe_simple(filename, progress_file)
            progress_file.write("orig :" + text + "\n")
            print "trans:", transcription
            print "orig :", text.lower()
            error = levenshtein(text.lower(), transcription.lower())
            progress_file.write("error:" + str(error) + "\n")
            assert isinstance(error, int)
            print "Error metric:", error
            results.write('%s,%d\n' % (filename, error))
            results.flush()
        results.close()
        progress_file.close()

