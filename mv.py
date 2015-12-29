#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
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

        print ''

        start_time = time.time()

        self.init_parser()
        self.init_attributes()

        try:

            if (self.mode == 'imagedir'):
                self.calc_colors_from_folder()
            elif (self.mode == 'image'):
                self.calc_colors_from_file()
            if (self.mode == 'video'):
                self.generate_thumbs_from_video()
                if (self.options.type != 'tiles'):
                    self.calc_colors_from_folder()

            if (self.options.type == 'blocks'):
                self.write_colors_to_blocks()
            elif (self.options.type == 'pie'):
                self.write_colors_to_pie()
            elif (self.options.type == 'tiles'):
                self.write_colors_to_tiles()

            if (self.mode == 'video'):
                self.remove_generated_thumbs()

            print ''
            print 'Calculated in: '+str(round(time.time()-start_time,2))+'s'
            print ''


        except:

            print "Unknown error occurred\n"
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
            help="Block height (default: 150)")

        self.parser.add_option("--blockwidth",
            action="store", type="int", dest="blockwidth", default='1',
            help="Block width (default: 1)")

        self.parser.add_option("--tilewidth",
            action="store", type="int", dest="tilewidth", default='320',
            help="Tile width (default: 1)")

        self.parser.add_option("-c", "--framecount",
            action="store", type="int", dest="framecount", default='400',
            help="Frame count (default: 400)")

        self.parser.add_option("-f", "--force",
            action="store_true", dest="force", default=False,
            help="Set to force new calculation of colors for target")

        self.parser.add_option("-k", "--keep",
            action="store_true", dest="keep", default=False,
            help="Keep generated thumbs")

        (self.options, self.args) = self.parser.parse_args()

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
        else:
            is_file = False

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
            self.result_image_filename = self.target_directory+'-'+self.options.type+'.'+(self.result_image_type.lower())
            self.color_filename = self.target_directory+'.color-list'
        elif (self.mode == 'image' or self.mode == 'video'):
            tmp_result_filename = [os.path.splitext(self.target_file)[0]]
            tmp_result_filename.append(os.path.splitext(self.target_file)[1].replace('.','-'))
            tmp_result_filename.append('-'+self.options.type)
            tmp_result_filename.append('.')
            tmp_result_filename.append(self.result_image_type.lower())
            self.result_image_filename = ''.join(tmp_result_filename)
            self.color_filename = self.target_file+'.color-list'
        if (self.mode == 'video'):
            self.thumb_folder = self.target_file.replace('.','_')+'_tmp_'+str(random.randint(10000,99999))
            self.target_directory = self.thumb_folder
            self.set_video_stream()
            if (self.options.type == 'tiles'):
                self.make_frame_count_square()
            self.calc_frame_distance()
            self.calc_seconds_distance()
            self.calc_thumb_size()
            self.fps = 1/self.seconds_distance_float
            self.ffmpeg_exec_args = [
                "ffmpeg",
                '-i',
                self.target_file,
                '-vf',
                'fps='+str(self.fps)+',scale='+str(self.options.tilewidth)+':-1',
                self.thumb_folder+os.path.sep+self.target_file+'_tmp_%05d.png'
                ]
            self.thumbs_generated = False


#~  Programmlogik ----------------------------------------------

    def generate_thumbs_from_video(self):

        if (self.options.force or not self.read_colorfile() or self.options.type == 'tiles'):

            self.thumbs_generated = True

            print 'Generating '+str(self.options.framecount)+' thumbs (size: '+str(self.thumb_width)+'x'+str(self.thumb_height)+') in folder: '+self.thumb_folder

            if (not os.path.isdir(self.thumb_folder)):
                os.mkdir(self.thumb_folder)

            # print self.total_frames, self.options.framecount, self.frame_distance_float

            # thumb_list_args = []
            # for i in range(self.options.framecount):
            #     thumb_list_args.append((
            #         round(i*self.frame_distance_float)/self.video_stream.video_fps, # in seconds
            #         self.thumb_folder+os.path.sep+'{:08d}'.format(i)+'.png',
            #         str(self.thumb_width)+'x'+str(self.thumb_height)
            #         ))

            # video_converter = VideoConverter()
            # video_converter.thumbnails(self.target_file,thumb_list_args)

            generate_thumbs_process = Popen(self.ffmpeg_exec_args, cwd=self.cwd, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE,
                     close_fds=True)
            generate_thumbs_process.wait()

            # might have produced framecount+1 images
            files = sorted(os.listdir(self.target_directory))
            if (len(files) > self.options.framecount):
                for i in range(self.options.framecount,len(files)):
                    os.remove(os.path.join(self.target_directory,files[i]))



    def calc_frame_distance(self):

        framecorrection = 5 # to compensate fps flaws...
        self.total_frames = int(self.video_stream.video_fps*self.video_info.format.duration)-framecorrection
        if (self.options.framecount > self.total_frames):
            self.parser.error("Not enough frames in video")
        self.frame_distance_float = float(self.total_frames)/float(self.options.framecount)


    def calc_seconds_distance(self):

        second_correction = 0 # to compensate fps flaws...
        self.seconds_distance_float = (self.video_info.format.duration-second_correction) / self.options.framecount

        print 'Calculated distance for given framecount: ~'+str(int(self.frame_distance_float))+' frames = '+str(round(self.seconds_distance_float,2))+'s'


    def make_frame_count_square(self):

        new_framecount = int(float(self.options.framecount)**(0.5))**2
        if (new_framecount != self.options.framecount):
            print "Framecount corrected to squarenumber: "+str(new_framecount)
            self.options.framecount = new_framecount


    def calc_thumb_size(self):

        aspect_ratio = float(self.video_stream.video_width)/float(self.video_stream.video_height)
        self.thumb_width = self.options.tilewidth
        self.thumb_height = int(round(self.thumb_width/aspect_ratio))

    def set_video_stream(self):

        self.video_stream = None
        for stream in self.video_info.streams:
            if stream.type == 'video':
                self.video_stream = stream
                break
        if self.video_stream is None:
            self.parser.error('Given file has no video stream')


    def remove_generated_thumbs(self):

        if (not self.options.keep and self.thumbs_generated):

            print 'Removing temporary thumb folder: '+self.thumb_folder
            shutil.rmtree(self.thumb_folder)

    def calc_colors_from_folder(self):

        if (self.options.force or not self.read_colorfile()):

            print 'Calculating colors from folder...'

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

            print 'Calculating colors from file...'

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

        print 'Saving '+self.options.type+' visualization to: '+self.result_image_filename
        
        im = Image.new('RGB', (len(self.colors)*self.result_image_blocks_width,self.result_image_blocks_height), (255,0,0))
        draw = ImageDraw.Draw(im)

        for index, color in enumerate(self.colors):

            draw.rectangle(
                (index*self.result_image_blocks_width, 0)+(((index+1)*self.result_image_blocks_width)-1,self.result_image_blocks_height),
                color)

        del draw
        im.save(self.result_image_filename,self.result_image_type)
    

    def write_colors_to_pie(self):

        print 'Saving '+self.options.type+' visualization to: '+self.result_image_filename

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



    def write_colors_to_tiles(self):

        print 'Saving '+self.options.type+' visualization to: '+self.result_image_filename

        files = sorted(os.listdir(self.target_directory))

        im = Image.new(
            'RGB',
            (
                int(float(self.options.framecount)**(0.5))*self.thumb_width,
                int(float(self.options.framecount)**(0.5))*self.thumb_height
            ),
            (0,0,0)
        )

        for index, file in enumerate(files):

            thumb_im = Image.open(os.path.join(self.thumb_folder, file))

            im.paste(thumb_im,((
                (index % int(float(self.options.framecount)**(0.5)))*self.thumb_width,
                (index / int(float(self.options.framecount)**(0.5)))*self.thumb_height
                ))
            )
            
            thumb_im.close()

        im.save(self.result_image_filename,self.result_image_type)
    


def get_color_from_image(filepath):

    # print 'processing '+filepath

    kmeans = Kmeans(1)
    im = Image.open(filepath)
    color = kmeans.run(im)[0]
    im.close()

    return color

def get_colors_from_image(filepath, number_of_colors):

    # print 'processing '+filepath

    kmeans = Kmeans(number_of_colors, 6, 5, 200) # default 6,5,200
    im = Image.open(filepath)
    colors = kmeans.run(im)
    im.close()

    return colors


if __name__ == '__main__':
    movie_visualizer = MovieVisualizer()
