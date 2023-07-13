import math as m

class Settings:
    def __init__(self, threads, thresh, blur, scale, input_dir, output_dir, output_file_name_prefix):
        self.threads = threads
        self.thresh = thresh
        self.blur = blur
        self.scale = scale
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_file_name_prefix = output_file_name_prefix
        self.image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
        self.deg_to_rad = m.pi / 180
        self.max = 255 # Thresholded max value (white).