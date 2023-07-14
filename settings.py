import math as m

class Settings:
    def __init__(self, threads, thresh, blur, scale, input_dir, output_dir, output_file_name_prefix, manual_name, manual_metadata, output_format):
        self.threads = threads
        self.thresh = thresh
        self.blur = blur
        self.scale = scale
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_file_name_prefix = output_file_name_prefix
        self.manual_name = manual_name
        self.manual_metadata = manual_metadata
        self.output_format = output_format
        self.image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
        self.deg_to_rad = m.pi / 180
        self.max = 255  # Thresholded max value (white).
