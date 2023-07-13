import argparse
from settings import Settings

class ArgParser:

    @staticmethod
    def parse():
        parser = argparse.ArgumentParser(description="Scanned image cropper." +
			"\nProcess scanned images to find photos inside them." +
			"\nOrients and crops photos found in the image scan." +
			"\nProcesses all images found in the input directory, and" +
			"\nwrites all found and processed photos in the output directory." +
			"\nCan process multiple photos in a single scan.",
			formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--dir', '-d', type=str,
                            help="Specify the location of the pictures to process.")
                            
        parser.add_argument('--odir', '-o', type=str,
                            help="Specify where to save the processed scans.")
                            
        parser.add_argument('--num-threads', '-n', dest='threads', type=int, default=0,
                            help="Number of threads to use." +
                            "\n0 = system number of cores.")
                            
        parser.add_argument('--pic-size-diff', '-s', type=float, dest='scale', default=0.80,
                            help="The approximate size difference between scanned images, as a percent." +
                            "\nSet lower if images are of varying sizes." +
                            "\nRange: [0.0,1.0]" )
                            
        parser.add_argument('--thresh', '-t', type=int, dest='thresh', default=230,
                            help="Sets the threshold value when determining photo edges." +
                            "\nUse higher values for brighter images. Lower for tighter cropping." +
                            "\nRange [0,255]")
                            
        parser.add_argument('--photos-per-scan', '-i', type=int, dest='num_scans', default=1,
                            help="Number of photos to look for per scanned image.")
                            
        parser.add_argument('--blur', '-b', type=int, dest='blur', default=9,
                            help="How much blur to apply when processing." +
                            "\nDifferent values may effect how well scans are found and cropped." +
                            "\nMust be odd number greater than 1.")
        parser.add_argument('--output-file-name-prefix', '-p', dest='output_file_name_prefix', type=str, default='',
                            help="Append the prefix string to the start of output image file names.")
        args = parser.parse_args()

        # Check if input and output directories are specified.
        if args.dir is None or args.odir is None:
            raise Exception("Input and Output directory must be specified")
        
        return Settings(args.threads, args.thresh, args.blur, args.scale, args.dir, args.odir, args.output_file_name_prefix)