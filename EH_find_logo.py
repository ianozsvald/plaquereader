import os
import csv
import math
import pickle
import subprocess
from PIL import Image, ImageDraw # http://www.pythonware.com/products/pil/

# reads our plaques (using easy_blue_plaques.csv)
# and builds
# eh_logo_points_dict.pickle
# which show all the locations where the English Heritage logo
# might exist
# It uses the English Heritage logos found in /EH_logos
# The output is used by EH_logo_regionblank.py
# to identify regions to blank

# directory containing our sample logos
DIR = "EH_logos"

EH_LOGO_POINTS_FILE = "eh_logo_points_dict.pickle"

def logos():
    """generator that builds the list of logo filenames"""
    for n in range(12):
        yield "eh_logo_%d.tiff" % (n + 1)
       
def load_csv(filename):
    """build plaques structure from CSV file"""
    plaques = []
    plqs = csv.reader(open(filename, 'rb'))
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

plaque_logo_positions = {}
plaques = load_csv('easy_blue_plaques.csv')
plaques = plaques#[:10]
for root_url, filename, text in plaques:
    img = Image.open(filename)
    print filename, " - ", img.size
    imgd = ImageDraw.Draw(img)

    points = []
    for logo in logos():
        img_name = os.path.join(DIR, logo)

        cmd = "./engher_find_obj" + " EH_logos/%s %s" % (logo, filename)
        print "----"
        print cmd
        p = subprocess.Popen(cmd, shell=True, bufsize=500, stdout=subprocess.PIPE)
        sts = os.waitpid(p.pid, 0)[1]
        print "status", sts

        print "output:"
        lines = p.stdout.readlines()
        for line in lines:
            l = line.strip().split(',')
            x = int(float(l[0]))
            y = int(float(l[1]))
            points.append((x,y))

            # print a black circle for each point
            #radius = 40 # radius for drawing circles
            #c1 = (x-radius,y-radius,x+radius,y+radius)
            #imgd.ellipse(c1,fill=0)

    # build a dict of filenames->size and list of points info
    plaque_logo_positions[filename] = (img.size, points)
    print "---"
    #img.show()
    #raw_input("Hit return to do next plaque...")

pickle.dump(plaque_logo_positions, file(EH_LOGO_POINTS_FILE, 'w'))
    
