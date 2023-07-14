import numpy as np
import cv2, os, argparse, datetime, time, errno, math, multiprocessing, pyexiv2, fitz
from concurrent.futures import ThreadPoolExecutor
from arg_parse import ArgParser
from settings import Settings

os.environ['QT_QPA_PLATFORM'] = 'xcb'

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

	def convert_pdf_to_png(self, pdf_path):
		dpi = 600
		doc = fitz.open(pdf_path)
		png_paths = []

		for i in range(len(doc)):
			# Rendering options.
			zoom = dpi / 72
			mat = fitz.Matrix(zoom, zoom)
			# Render page to an image
			pix = doc.get_page_pixmap(i, matrix=mat)
			os.makedirs("./pdfTopng", exist_ok=True)
			# Create a unique filename for each page image.
			base_name = os.path.basename(pdf_path)
			name_without_ext = os.path.splitext(base_name)[0]
			png_path = os.path.join("./pdfTopng", f"{name_without_ext}.png")
			# Save the image
			pix.save(png_path)
			print(f"Saved PNG file: {png_path}")
			png_paths.append(png_path)
		
		return png_paths




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

	def process_file(self, file):
		self.images += 1
		img = cv2.imread(file, cv2.IMREAD_COLOR)
		if img is None:
			print(f'Error opening image file {file}')
			return
		scans = self.find_scans(img)
		if len(scans) > 0:
			i = 0
			for scan in scans:
				# Get the filename and metadata from the user
				new_filename = f"{os.path.splitext(os.path.basename(file))[0]}_{i}"

				if self.settings.manual_name:
					# Display the image
					cv2.imshow('Image', scan)
					cv2.waitKey(0)
					cv2.destroyAllWindows()

					new_filename = input("Please enter a filename for this image: ")


				# Saving the image
				if self.settings.output_format == 'jpg':
					if not scan.size:  # Checking if the image is not empty.
						print("Skipping empty image: " + str(os.path.join(self.settings.output_dir, f"{new_filename}.jpg")))
						print("Possible problem with image alignment on the scan. Rescan and try again.")
						return
					cv2.imwrite(os.path.join(self.settings.output_dir, f"{new_filename}.jpg"), scan, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
				elif self.settings.output_format == 'png' and self.settings.manual_metadata == False:
					if not scan.size:  # Checking if the image is not empty.
						print("Skipping empty image: " + str(os.path.join(self.settings.output_dir, f"{new_filename}.png")))
						print("Possible problem with image alignment on the scan. Rescan and try again.")
						return
					cv2.imwrite(os.path.join(self.settings.output_dir, f"{new_filename}.png"), scan)
				elif self.settings.output_format == 'png' and self.settings.manual_metadata == True:
					print('png does not support exif metadata - changing output format to jpg')
					if not scan.size:  # Checking if the image is not empty.
						print("Skipping empty image: " + str(os.path.join(self.settings.output_dir, f"{new_filename}.jpg")))
						print("Possible problem with image alignment on the scan. Rescan and try again.")
						return
					cv2.imwrite(os.path.join(self.settings.output_dir, f"{new_filename}.jpg"), scan, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
				else:
					print('This output image type is not supported. Only jpg and png. Taking jpg.')
					if not scan.size:  # Checking if the image is not empty.
						print("Skipping empty image: " + str(os.path.join(self.settings.output_dir, f"{new_filename}.jpg")))
						print("Possible problem with image alignment on the scan. Rescan and try again.")
						return
					cv2.imwrite(os.path.join(self.settings.output_dir, f"{new_filename}.jpg"), scan, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

				self.scans += 1

				if self.settings.manual_metadata:
					# Display the image
					cv2.imshow('Image', scan)
					cv2.waitKey(0)
					cv2.destroyAllWindows()

					metadata = input("Please enter metadata for this image: ")
					
					# Saving the image
					img_metadata = pyexiv2.ImageMetadata(os.path.join(self.settings.output_dir, f"{new_filename}.jpg"))
					
					img_metadata.read()
					img_metadata["Exif.Image.ImageDescription"] = metadata
					img_metadata.write()

				if self.settings.output_format == 'jpg':
					print(f'Saved scan {i} to {self.settings.output_dir}/{new_filename}.jpg')
				elif self.settings.output_format == 'png':
					print(f'Saved scan {i} to {self.settings.output_dir}/{new_filename}.png')
				else:
					print(f'Saved scan {i} to {self.settings.output_dir}/{new_filename}.jpg')
				
				i += 1

				if self.settings.manual_metadata:
					img_metadata = pyexiv2.ImageMetadata(os.path.join(self.settings.output_dir, f"{new_filename}.jpg"))
					img_metadata.read()
					print('Metadata in image:  ' + str(img_metadata['Exif.Image.ImageDescription'].value))

				print('--------')

		else:
			print(f'No scans found in file {file}')




	def autocrop_images(self):
		for file in os.listdir(self.settings.input_dir):
			file = os.path.join(self.settings.input_dir, file)
			if file.endswith('.pdf') or file.endswith('PDF'):
				# Convert PDF to PNG and then process each PNG.
				png_paths = self.convert_pdf_to_png(file)
				for png_path in png_paths:
					print('=============')
					self.process_file(png_path)
			elif file.endswith(tuple(self.settings.image_extensions)):
				print('=============')
				self.process_file(file)

		#for file in [f for f in os.listdir(self.settings.input_dir) if f.endswith(tuple(self.settings.image_extensions))]:
		#	self.process_file(file)

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