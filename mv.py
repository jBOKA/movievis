#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import optparse
from matplotlib import pyplot
from kmeans.kmeans import Kmeans
from PIL import Image, ImageDraw
from multiprocessing import Pool
try:
    import cPickle as pickle
except:
    import pickle

class MovieVisualizer:

#~  Konstructor und Destruktor -----------------------------------------

    def __init__(self):

        self.init_parser()
        self.init_attributes()

        try:
            self.get_colors_from_folder()
            if (self.vis_type == 'stripe'):
                self.write_colors_to_stripe()
            elif (self.vis_type == 'pie'):
                self.write_colors_to_pie()
        except:
            print "Unbekannter Fehler - Skript beendet\n"
            raise   
    
#~  Initialisierungszeugs ----------------------------------------------

    # optionen der executable
    def init_parser(self):

        self.parser = optparse.OptionParser('Usage: movievis [options] dirname')
        self.parser.add_option("-t", "--type",
            action="store", type="string", dest="type", default='stripe',
            help="Type of the visualization - default: stripe")

        (self.options, self.args) = self.parser.parse_args()

        if not self.options.type:   # if type is not given
            self.parser.error('Type name not given')
        else:
            self.vis_type = self.options.type
        
        if (len(self.args) != 1 or (not os.path.isdir(self.args[0])) ):
            self.parser.error("Please give a valid directory name")
        else:
            self.image_directory = self.args[0].rstrip('/')

    
    # feste attribute
    def init_attributes(self):

        self.result_image_stripe_height = 100
        self.result_image_type = "PNG"
        self.result_image_filename = self.image_directory+'-'+self.vis_type+'.'+(self.result_image_type.lower())
        self.color_filename = self.image_directory+'.color-list'


#~  Programmlogik ----------------------------------------------


    def get_colors_from_folder(self):

        if (not self.read_colors_from_file()):

            files = sorted(os.listdir(self.image_directory))

            # create filepaths from filenames for pickled function (see after Class)
            def getpath(filename):
                return os.path.join(self.image_directory,filename)
            files = map(getpath,files)

            p = Pool(4)

            colors = p.map(get_color_from_image, files)

            # save colors to file

            self.colors = colors

            self.save_colors_to_file()


    def read_colors_from_file(self):

        if (not os.path.isfile(self.color_filename)):

            return False

        print 'Reading colors from file: '+self.color_filename

        file = open(self.color_filename,'rb')
        colors = pickle.load(file)
        file.close()

        self.colors = colors

        return True

    def save_colors_to_file(self):

        print 'Saving colors to file: '+self.color_filename

        file = open(self.color_filename,'wb')
        pickle.dump(self.colors,file)
        file.close()

    def write_colors_to_stripe(self):

        print 'Saving visualization to: '+self.result_image_filename
        
        im = Image.new('RGB', (len(self.colors),self.result_image_stripe_height), (0,0,0))
        draw = ImageDraw.Draw(im)

        for index, color in enumerate(self.colors):

            draw.line((index, 0)+(index,self.result_image_stripe_height),color,1)

        del draw
        im.save(self.result_image_filename,self.result_image_type)

    def write_colors_to_pie(self):

        sizes = []
        colors = []
        for index, color in enumerate(self.colors):
            colors.append((color[0].astype(float)/255,color[1].astype(float)/255,color[2].astype(float)/255))
            sizes.append(index)

        pyplot.pie(sizes,              # data
            colors=colors,      # array of colours
            shadow=False,        # enable shadow
            startangle=70       # starting angle
            )
        pyplot.axis('equal')

        pyplot.show()

        fig = pyplot.figure()

        pyplot.savefig(self.result_image_filename, bbox_inches='tight')


    # def create_color_picture(self, target_filename, image_size, color):

    #     filename, file_extension = os.path.splitext(target_filename)

    #     result_image = Image.new('RGB', image_size, color)

    #     result_image.save(filename+'.color.png','PNG')

    #     result_image.close()
    
    

def get_color_from_image(filepath):

    print 'processing '+filepath

    kmeans = Kmeans(1)
    im = Image.open(filepath)
    color = kmeans.run(im)[0]
    im.close()

    return color



if __name__ == '__main__':
    movie_visualizer = MovieVisualizer()
