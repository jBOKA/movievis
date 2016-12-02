# movievis

*movievis* is a python cli tool, to create still visualizations of movies (displaying color/time evolution) dimension and multi-color abstractions from images. 

I tried to optimize for performance a little using multiprocessing pools, but there's plenty of room for optimization. The *k*-means is pretty hungry, the rest is up to the image generation done by ffmpeg.

## Usage

Receive the options by calling `mv.py --help`

```
movievis [-t TYPE] [--force] imagefile|imagedir
movievis [-t TYPE] [--framecount=400] [--keep] moviefile
blockwidth, blockheight, and tilewidth are additional options for the according type of visualization

Options:
  -h, --help            show this help message and exit
  -t TYPE, --type=TYPE  Type of the visualization - blocks (default), pie,
                        tiles (only moviefiles)
  --blockheight=BLOCKHEIGHT
                        Block height (default: 150)
  --blockwidth=BLOCKWIDTH
                        Block width (default: 1)
  --tilewidth=TILEWIDTH
                        Tile width (default: 1)
  -c FRAMECOUNT, --framecount=FRAMECOUNT
                        Number of frames extracted from moviefile (default:
                        400)
  -f, --force           Force new calculation of colors for target (obsolete
                        for type=tiles)
  -k, --keep            Keep generated thumbs
```

## Credits and dependencies

*movievis* uses

+ some python libs: matplotlib, PIL, multiprocessing, cPickle (make sure these are installed)
+ [*k*-means clustering](https://en.wikipedia.org/wiki/K-means_clustering "Wikipedia") to identify key colors. The *k*-means implementation for images is taken from Ze'ev Gilovitz [blog post](http://blog.zeevgilovitz.com/detecting-dominant-colours-in-python/) and [on github](https://github.com/ZeevG/python-dominant-image-colour). (included)
+ an ffmpeg wrapper by Senko Rasic et.al. found [here](https://github.com/senko/python-video-converter) (included)
