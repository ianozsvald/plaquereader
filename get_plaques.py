import os
import sys
import csv
import urllib
from PIL import Image # http://www.pythonware.com/products/pil/

# get_plaques.py - downloads plaque images and converts to TIFF files
# cmdline> python get_plaques.py easy_blue_plaques.csv
# it will download images and conver them to TIFF files for tesseract

# For more details see:
# http://aicookbook.com/wiki/Automatic_plaque_transcription

def get_plaques(plaques):
    """download plaque images if we don't already have them"""
    for root_url, filename, text in plaques:
        filename_base = os.path.splitext(filename)[0] # turn 'abc.jpg' into 'abc'
        filename_tif = filename_base + '.tif'
        if not os.path.exists(filename_tif):
            print "Downloading", filename
            urllib.urlretrieve(root_url+filename, filename)
            im = Image.open(filename)
            im.save(filename_tif, 'TIFF')
            if filename.rfind('.tif') == -1:
                os.remove(filename) # delete the original file

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
        root_url = image_url[:last_slash+1]
        plaque = [root_url, filename, text]
        plaques.append(plaque)
    return plaques

if __name__ == '__main__':
    argc = len(sys.argv)
    if argc != 2:
        print "Usage: python get_plaques.py plaques.csv (e.g. \
easy_blue_plaques.csv)"
    else:
        plaques = load_csv(sys.argv[1])
        get_plaques(plaques)

