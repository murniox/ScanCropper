import numpy as np
import cv2, os, argparse, datetime, errno, math, multiprocessing
from concurrent.futures import ThreadPoolExecutor
from arg_parse import ArgParser
from settings import Settings


class ScanCropper:

	def __init__(self, settings: Settings):
		self.settings = settings
		self.errors = 0 # Total number of errors encountered.
		self.images = 0 # Total number of image files processed.
		self.scans = 0 # Total number of images found in all scans.

		# Try making the output directory.
		try:
			os.makedirs(settings.output_dir)
		except OSError as e:
			if e.errno != errno.EEXIST:
				raise


	def get_datetime(self):
		return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

	def open_image(self, file_name):
		path = os.path.join(self.settings.input_dir, file_name)
		img = cv2.imread(path)
		if img is None:
			print("Error: Failed to open image at path: "+path)
			self.errors += 1
		return img

	def write_image(self, file_name, img):
		path = os.path.join(self.settings.output_dir, file_name)
		success = cv2.imwrite(path, img)
		if not success:
			print("Error: Failed to write image "+file_name+" to file.")
			self.errors += 1
			return False
		print("Wrote image to: " + path)
		return True

	def write_scans(self, file_name, scans):
		if len(scans) == 0:
			print("Warning: No scans were found in this image: "+file_name)
			self.errors += 1
			return
		name, ext = os.path.splitext(file_name)
		if self.settings.output_file_name_prefix:
			name = "{}_{}".format(self.settings.output_file_name_prefix, name)
		num = 0
		for scan in scans:
			f = "{}_{}{}".format(name, num, ext)
			self.write_image(f, scan)
			num += 1
		
	# Find regions of interest in the form [rect, box-contour].
	# Attempts to find however many scans we're looking for in the image.
	def get_candidate_regions(self, img, contours):
		roi = []
		for contour in contours:
			rect = cv2.minAreaRect(contour)
			box = cv2.boxPoints(rect)
			roi.append([box, rect, cv2.contourArea(box)])
		roi = sorted(roi, key=lambda b: b[2], reverse=True)
		
		img_shape = img.shape
		img_area = img_shape[0] * img_shape[1]
		candidates = []
		for b in roi:
			if (b[2] / img_area) > 0.05:
				candidates.append(b)
		return candidates

	def rotate_image(self, img, angle, center):
		(h, w) = img.shape[:2]
		mat = cv2.getRotationMatrix2D(center, angle, 1.0)
		return cv2.warpAffine(img, mat, (w,h), flags=cv2.INTER_LINEAR)

	def rotate_box(self, box, angle, center):
		rad = -angle * self.settings.deg_to_rad
		sine = math.sin(rad)
		cosine = math.cos(rad)
		rotBox = []
		for p in box:
			p[0] -= center[0]
			p[1] -= center[1]
			rot_x = p[0] * cosine - p[1] * sine
			rot_y = p[0] * sine   + p[1] * cosine
			p[0] = rot_x + center[0]
			p[1] = rot_y + center[1]
			rotBox.append(p)
		return np.array(rotBox)

	def get_center(self, box):
		x_vals = [i[0] for i in box]; y_vals = [i[1] for i in box]
		cen_x = (max(x_vals) + min(x_vals)) / 2
		cen_y = (max(y_vals) + min(y_vals)) / 2
		return (cen_x, cen_y)

	# Rotate and crop the candidates.
	def clip_scans(self, img, candidates):
		scans = []
		for roi in candidates:
			rect = roi[1]
			box = np.intp(roi[0])
			angle = rect[2]
			if angle < -45:
				angle += 90
			center = self.get_center(box)
			rotIm = self.rotate_image(img, angle, center)
			rotBox = self.rotate_box(box, angle, center)
			x_vals = [i[0] for i in rotBox]; y_vals = [i[1] for i in rotBox]
			try:
				scans.append(rotIm[min(y_vals):max(y_vals), min(x_vals):max(x_vals)])
			except IndexError as e:
				print("Error: Rotated image is out of bounds!\n" +
					"Try straightening the picture, and moving it away from the scanner's edge.", e)
				self.errors += 1
		return scans
		
	def find_scans(self, img):
		blur = cv2.medianBlur(img, self.settings.blur)
		grey = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)
		_, thr = cv2.threshold(grey, self.settings.thresh, self.settings.max, cv2.THRESH_BINARY_INV)
		contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		roi = self.get_candidate_regions(img, contours)
		scans = self.clip_scans(img, roi)
		return scans

	def process_file(self, file_name):
		print(file_name)
		img = self.open_image(file_name)
		scans = self.find_scans(img)
		self.write_scans(file_name, scans)
		self.images += 1
		self.scans += len(scans)
		

	def autocrop_images(self):
		for file in [f for f in os.listdir(self.settings.input_dir) if f.endswith(tuple(self.settings.image_extensions))]:
			self.process_file(file)

		print("\n-----------------------------------------------------")
		if self.errors > 0:
			print("ERROR: While cropping scan files occurred {} errors and warnings.".format(self.errors))
		else:
			print("Successfully cropped all the images from the scan files.")
		print("Cropped {} pictures from {} scan files.".format(self.scans, self.images))

#--------------------------------------------------------------------

if __name__ == '__main__':
	settings = ArgParser.parse()
	cropper = ScanCropper(settings)
	cropper.autocrop_images()