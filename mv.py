#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import random
import shutil
import optparse
from converter import Converter as VideoConverter
from matplotlib import pyplot
from kmeans.kmeans import Kmeans
from PIL import Image, ImageDraw
from multiprocessing import Pool
from subprocess import Popen, PIPE
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

            if (self.mode == 'imagedir'):
                self.calc_colors_from_folder()
            elif (self.mode == 'image'):
                self.calc_colors_from_file()
            elif (self.mode == 'video'):
                self.generate_thumbs_from_video()
                self.calc_colors_from_folder()
                self.remove_generated_thumbs()

            if (self.vis_type == 'blocks'):
                self.write_colors_to_blocks()
            elif (self.vis_type == 'pie'):
                self.write_colors_to_pie()

        except:

            print "Unbekannter Fehler - Skript beendet\n"
            raise   
    
#~  Initialisierungszeugs ----------------------------------------------

    # optionen der executable
    def init_parser(self):

        self.parser = optparse.OptionParser('Usage: movievis [options] imagefolder|video [fps]|image [numberofcolors]')
        
        self.parser.add_option("-t", "--type",
            action="store", type="string", dest="type", default='blocks',
            help="Type of the visualization - blocks (default), pie")

        self.parser.add_option("--blockheight",
            action="store", type="int", dest="blockheight", default='150',
            help="Block (visualization type) height (default: 150)")

        self.parser.add_option("--blockwidth",
            action="store", type="int", dest="blockwidth", default='1',
            help="Block (visualization type) width (default: 1)")

        self.parser.add_option("-f", "--force",
            action="store_true", dest="force", default=False,
            help="Set to force new calculation of colors for target")

        self.parser.add_option("-k", "--keep",
            action="store_true", dest="keep", default=False,
            help="Keep generated thumbs")

        (self.options, self.args) = self.parser.parse_args()

        if not self.options.type:   # if type is not given
            self.parser.error('Type not given')
        else:
            self.vis_type = self.options.type
        
        if (len(self.args) < 1):
            self.parser.error("Please give a file or directory")

        if (os.path.isdir(self.args[0])):
            is_dir = True
            print 'IMAGE DIRECTORY MODE'
            self.mode = 'imagedir'
            self.target_directory = self.args[0].rstrip('/')
        else:
            is_dir = False

        if (not is_dir and os.path.isfile(self.args[0])):
            is_file = True
            # IMAGE ?
            try:
                im=Image.open(self.args[0])
                del im
                # YES
                is_image = True
                print 'SINGLE IMAGE MODE'
                self.mode = 'image'
                self.target_file = self.args[0]
                self.number_of_colors = int(self.args[1]) if (len(self.args) > 1) else 5
            except IOError:
                # NO
                is_image = False

            # IF NOT IMAGE: VIDEO ?
            if (not is_image):
                video_converter = VideoConverter()
                tmp_video_info = video_converter.probe(self.args[0])
                if (tmp_video_info):
                    is_video = True
                    print 'SINGLE VIDEO MODE'
                    self.mode = 'video'
                    self.video_info = tmp_video_info
                    self.target_file = self.args[0]
                else:
                    is_video = False

            if (not (is_image or is_video)):
                self.parser.error("Given file isn't a valid Image/Video")

        if (not (is_dir or is_file)):
            self.parser.error("File or directory not found")


    # feste attribute
    def init_attributes(self):

        self.script_location = os.path.dirname(os.path.realpath(__file__))
        self.cwd = os.getcwd()

        self.colors = []

        self.result_image_blocks_width = self.options.blockwidth
        self.result_image_blocks_height = self.options.blockheight

        self.result_image_type = "PNG"

        if (self.mode == 'imagedir'):
            self.result_image_filename = self.target_directory+'-'+self.vis_type+'.'+(self.result_image_type.lower())
            self.color_filename = self.target_directory+'.color-list'
        elif (self.mode == 'image' or self.mode == 'video'):
            tmp_result_filename = [os.path.splitext(self.target_file)[0]]
            tmp_result_filename.append(os.path.splitext(self.target_file)[1].replace('.','-'))
            tmp_result_filename.append('-'+self.vis_type)
            tmp_result_filename.append('.')
            tmp_result_filename.append(self.result_image_type.lower())
            self.result_image_filename = ''.join(tmp_result_filename)
            self.color_filename = self.target_file+'.color-list'
        if (self.mode == 'video'):
            self.thumb_folder = self.target_file+'_tmp_'+str(random.randint(10000,99999))
            self.target_directory = self.thumb_folder
            self.fps = float(self.args[1]) if (len(self.args) > 1) else float(0.1)
            self.ffmpeg_exec_args = [
                "ffmpeg",
                '-i',
                self.target_file,
                '-vf',
                'fps='+str(self.fps)+',scale=300:-1',
                self.thumb_folder+os.path.sep+self.target_file+'_tmp_%05d.png'
                ]
            self.thumbs_generated = False


#~  Programmlogik ----------------------------------------------

    def generate_thumbs_from_video(self):

        if (self.options.force or not self.read_colorfile()):

            self.thumbs_generated = True

            print 'Generating thumbs in folder: '+self.thumb_folder

            if (not os.path.isdir(self.thumb_folder)):
                os.mkdir(self.thumb_folder)

            generate_thumbs_process = Popen(self.ffmpeg_exec_args, cwd=self.cwd)
            # generate_thumbs_process = Popen(self.ffmpeg_exec_args, cwd=self.cwd, stdout=PIPE)
            generate_thumbs_process.wait()


    def remove_generated_thumbs(self):

        if (not self.options.keep and self.thumbs_generated):

            print 'Removing temporary thumb folder: '+self.thumb_folder
            shutil.rmtree(self.thumb_folder)

    def calc_colors_from_folder(self):

        if (self.options.force or not self.read_colorfile()):

            files = sorted(os.listdir(self.target_directory))

            # create filepaths from filenames for pickled function (see after Class)
            def getpath(filename):
                return os.path.join(self.target_directory,filename)
            files = map(getpath,files)

            p = Pool(4)

            colors = p.map(get_color_from_image, files)

            # save colors to file

            self.colors = colors

            self.save_colorfile()


    def calc_colors_from_file(self):

        if (self.options.force or not self.read_colorfile()):

            filename = self.target_file

            # create filepaths from filenames for pickled function (see after Class)

            colors = get_colors_from_image(filename, self.number_of_colors)

            # save colors to file

            self.colors = colors

            self.save_colorfile()


    def read_colorfile(self):

        if (not os.path.isfile(self.color_filename)):

            return False

        if (len(self.colors) < 1):

            print 'Reading colors from file: '+self.color_filename

            file = open(self.color_filename,'rb')
            colors = pickle.load(file)
            file.close()

            self.colors = colors

        return True

    def save_colorfile(self):

        print 'Saving colors to file: '+self.color_filename

        file = open(self.color_filename,'wb')
        pickle.dump(self.colors,file)
        file.close()


    def write_colors_to_blocks(self):

        print 'Saving '+self.vis_type+' visualization to: '+self.result_image_filename
        
        im = Image.new('RGB', (len(self.colors)*self.result_image_blocks_width,self.result_image_blocks_height), (255,0,0))
        draw = ImageDraw.Draw(im)

        for index, color in enumerate(self.colors):

            draw.rectangle(
                (index*self.result_image_blocks_width, 0)+(((index+1)*self.result_image_blocks_width)-1,self.result_image_blocks_height),
                color)

        del draw
        im.save(self.result_image_filename,self.result_image_type)
    

    def write_colors_to_pie(self):

        print 'Saving '+self.vis_type+' visualization to: '+self.result_image_filename

        sizes = []
        colors = []
        for index, color in enumerate(reversed(self.colors)):
            colors.append((color[0].astype(float)/255,color[1].astype(float)/255,color[2].astype(float)/255))
            sizes.append(1)

        pyplot.figure(num=1, figsize=(35, 35))

        wedges, texts = pyplot.pie(sizes,
            colors=colors,
            shadow=False,
            startangle=90
            )
        for w in wedges:
            w.set_linewidth(0)

        pyplot.axis('equal')
        
        pyplot.savefig(self.result_image_filename, bbox_inches='tight', transparent=True)

        # pyplot.show()




def get_color_from_image(filepath):

    print 'processing '+filepath

    kmeans = Kmeans(1)
    im = Image.open(filepath)
    color = kmeans.run(im)[0]
    im.close()

    return color

def get_colors_from_image(filepath, number_of_colors):

    print 'processing '+filepath

    kmeans = Kmeans(number_of_colors, 6, 5, 200) # default 6,5,200
    im = Image.open(filepath)
    colors = kmeans.run(im)
    im.close()

    return colors



if __name__ == '__main__':
    movie_visualizer = MovieVisualizer()
