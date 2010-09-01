import os
import sys
import csv
import urllib
from PIL import Image # http://www.pythonware.com/products/pil/

# This recognition system depends on:
# http://code.google.com/p/tesseract-ocr/
# version 2.04, it must be installed and compiled already

# plaque_transcribe_demo.py
# run it with 'cmdline> python plaque_transcribe_demo.py easy_blue_plaques.csv'
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
    filename_tif = filename_base + '.tif'
    im.save(filename_tif, 'TIFF')

    # call tesseract, read the resulting .txt file back in
    cmd = 'tesseract %s %s -l eng' % (filename_tif, filename_base)
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

    return transcription
    

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
            print "Transcription:", transcription
            error = levenshtein(text, transcription)
            assert isinstance(error, int)
            print "Error metric:", error
            results.write('%s,%d\n' % (filename, error))
            results.flush()
        results.close()

