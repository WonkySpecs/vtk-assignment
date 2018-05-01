import argparse
import os
import re
import math

import vtk
from numpy import fromfile




#	TO DO:
#	-Colours?




def find_thresholds(filenames):
	#Good values for test datasets:
	# CThead 710 (head)/1150 (skull)
	# MRBrain 1300
	# bunny 1500
	print("Determining contour threshold")

	#Use good values for the 3 test datasets which were found manually
	#Otherwise return 10% of the maximum voxel value, as recommended
	max_val = 0
	min_val = 70000
	for filename in filenames:
		#We create an array of unsigned short ints from the binary files
		val_array = fromfile(filename, dtype = ">u2")
		#Search for max, check if higher than max across all files (so far)
		image_max = max(val_array)
		if image_max > max_val:
			max_val = image_max

		image_min = min(val_array)
		if image_min < min_val:
			min_val = image_min
	
	if "CThead" in filenames[0]:
		iso_val = 710
	elif "MRbrain" in filenames[0]:
		iso_val = 1300
	elif "bunny" in filenames[0] or filenames[0] == "1":
		iso_val = 1500
	else:
		iso_val = max_val // 10

	return min_val, max_val, iso_val

def main(image_width, image_height, filename_list):
	min_image_val, max_image_val, thresh = find_thresholds(filename_list)

	print("{} contour value".format(thresh))

	#Set up reader which reads the given input images
	#Designed to read in len(filename_list) images of image_width x image_height scalars
	#Each voxel value is represented by a big endian short (2 bytes)
	filename_array = vtk.vtkStringArray()

	for filename in filename_list:
		filename_array.InsertNextValue(filename)
		
	reader = vtk.vtkImageReader2()
	reader.SetFileNames(filename_array)
	#Images are 2D with a single scalar per cell
	reader.SetFileDimensionality(2)
	reader.SetNumberOfScalarComponents(1)
	#Data held as unsigned big endian shorts, as specified
	reader.SetDataScalarTypeToShort()
	reader.SetDataByteOrderToBigEndian()	
	#Set spacing - the spacing between images is generally different to the spacing between pixels
	#Spacing for bunny is 1:1:1.48, CThead is approximately 1:1:2, MRbrain appears to be similar
	#to bunny.
	if "CThead" in filename_list[0]:
		reader.SetDataSpacing(1, 1, 2)
	else:
		reader.SetDataSpacing(1, 1, 1.48)
	#Size of images
	reader.SetDataExtent(0, image_width - 1, 0, image_height - 1, 0, 0)

	#Smooth noise in images (before building mesh)
	pre_smoother = vtk.vtkImageGaussianSmooth()
	pre_smoother.SetInputConnection(reader.GetOutputPort())

	#Things we've tried, mention in report thne delete THIS OK ASDFASDFASDFASDFASDFASDFKAEDROGIMRO read me
	#smoother.SetStandardDeviations(1.5, 1.5, 1.5)
	#smoother.SetRadiusFactors(1.0, 1.0, 1.0)
	# print(smoother.GetStandardDeviations())
	# print(smoother.GetRadiusFactors())
	#smoother = vtk.vtkImageMedian3D()
	#smoother.SetInputConnection(reader.GetOutputPort())

	#Create isosurface from voxel grid
	#surface_extractor = vtk.vtkMarchingCubes()
	surface_extractor = vtk.vtkContourFilter()
	surface_extractor.SetInputConnection(pre_smoother.GetOutputPort())
	surface_extractor.SetValue(0, thresh)

	#post_smoother = vtk.vtkSmoothPolyDataFilter()
	#post_smoother.SetInputConnection(surface_extractor.GetOutputPort())

	#Map polygon mesh to graphics primitives
	surface_mapper = vtk.vtkPolyDataMapper()
	surface_mapper.SetInputConnection(surface_extractor.GetOutputPort())
	surface_mapper.ScalarVisibilityOff()

	#Create actor for rendering
	surface = vtk.vtkActor()
	surface.SetMapper(surface_mapper)
	surface.GetProperty().SetColor(0.7, 0.7, 0.7)
	
	surface.GetProperty().SetSpecular(0.25)
	surface.GetProperty().SetSpecularPower(0.2)
	#surface.GetProperty().Set

	#Render and display actor(s)
	renderer = vtk.vtkRenderer()
	renderer.AddActor(surface)

	two_surface_model = False
	if two_surface_model:
		skull_extractor = vtk.vtkContourFilter()
		skull_extractor.SetInputConnection(pre_smoother.GetOutputPort())
		skull_extractor.SetValue(0, 1200)

		skull_mapper = vtk.vtkPolyDataMapper()
		skull_mapper.SetInputConnection(skull_extractor.GetOutputPort())
		skull_mapper.ScalarVisibilityOff()

		skull = vtk.vtkActor()
		skull.SetMapper(skull_mapper)
		skull.GetProperty().SetColor(0.6, 0.6, 0.6)
		
		skull.GetProperty().SetSpecular(0.2)
		skull.GetProperty().SetSpecularPower(0.3)
		skull.GetProperty().SetOpacity(1.0)

		surface.GetProperty().SetOpacity(0.35)

		renderer.AddActor(skull)

	window = vtk.vtkRenderWindow()
	window.AddRenderer(renderer)
	window.SetSize(640, 480)

	interactor = vtk.vtkRenderWindowInteractor()
	interactor.SetRenderWindow(window)

	tube_width = 0.022
	slider_width = 0.04
	endcap_width = 0.06
	endcap_height = 0.003

	slider_thresh = vtk.vtkSliderRepresentation2D()
	slider_thresh.SetMinimumValue(min_image_val)
	slider_thresh.SetMaximumValue(max_image_val)
	slider_thresh.SetValue(thresh)
	slider_thresh.SetTitleText("Isosurface threshold")

	slider_thresh.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
	slider_thresh.GetPoint1Coordinate().SetValue(.1, .9)
	slider_thresh.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
	slider_thresh.GetPoint2Coordinate().SetValue(.45, .9)

	slider_thresh.SetTubeWidth(tube_width)
	slider_thresh.SetSliderWidth(slider_width)
	slider_thresh.SetEndCapWidth(endcap_width)
	slider_thresh.SetEndCapLength(endcap_height)

	slider_thresh_widget = vtk.vtkSliderWidget()
	slider_thresh_widget.SetInteractor(interactor)
	slider_thresh_widget.SetRepresentation(slider_thresh)
	slider_thresh_widget.SetAnimationModeToAnimate()
	slider_thresh_widget.EnabledOn()
	slider_thresh_widget.SetNumberOfAnimationSteps(10)

	slider_thresh_widget.AddObserver(vtk.vtkCommand.EndInteractionEvent, slider_thresh_callback(surface_extractor))

	slider_cutoff = vtk.vtkSliderRepresentation2D()
	slider_cutoff.SetMinimumValue(1)
	slider_cutoff.SetMaximumValue(len(filename_list))
	slider_cutoff.SetValue(len(filename_list))
	slider_cutoff.SetTitleText("Slice")

	slider_cutoff.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
	slider_cutoff.GetPoint1Coordinate().SetValue(.55, .9)
	slider_cutoff.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
	slider_cutoff.GetPoint2Coordinate().SetValue(.95, .9)

	slider_cutoff.SetTubeWidth(tube_width)
	slider_cutoff.SetSliderWidth(slider_width)
	slider_cutoff.SetEndCapWidth(endcap_width)
	slider_cutoff.SetEndCapLength(endcap_height)

	slider_cutoff_widget = vtk.vtkSliderWidget()
	slider_cutoff_widget.SetInteractor(interactor)
	slider_cutoff_widget.SetRepresentation(slider_cutoff)
	slider_cutoff_widget.SetAnimationModeToAnimate()
	slider_cutoff_widget.EnabledOn()
	slider_cutoff_widget.SetNumberOfAnimationSteps(10)

	slider_cutoff_widget.AddObserver(vtk.vtkCommand.EndInteractionEvent, slider_cutoff_callback(filename_list, filename_array, reader))

	interactor.Initialize()
	interactor.Start()

class slider_thresh_callback():
	def __init__(self, surface_extractor):
		self.surface_extractor = surface_extractor

	def __call__(self, caller, event):
		slider_widget = caller
		new_thresh = slider_widget.GetRepresentation().GetValue()
		self.surface_extractor.SetValue(0, new_thresh)

class slider_cutoff_callback():
	def __init__(self, filename_list, filename_array, reader):
		self.filename_list = filename_list
		self.filename_array = filename_array
		self.reader = reader

	def __call__(self, caller, event):
		slider_widget = caller
		slice_val = math.floor(slider_widget.GetRepresentation().GetValue())
		caller.GetRepresentation().SetValue(slice_val)

		self.filename_array.Initialize()
		for filename in self.filename_list[:slice_val]:
			self.filename_array.InsertNextValue(filename)

		self.reader.SetFileNames(self.filename_array)
		self.reader.Modified()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = 'Visualise images of 3D scans given as ')
	parser.add_argument('x', metavar = 'xPixelsPerImage', type = int, help = 'Width of images')
	parser.add_argument('y', metavar = 'yPixelsPerImage', type = int, help = 'Height of images')
	parser.add_argument('n', metavar = 'numberOfImages', type = int, help = 'Number of images / Depth of model')

	parser.add_argument('images', metavar = 'imageSource', nargs = "+", type = str, help = 'List of image names OR name of folder containing (only) images')
	
	args = parser.parse_args()
	if len(args.images) == 1 or len(args.images) == args.n:
		if len(args.images) == 1:
			filename_list = [os.path.join(os.curdir, args.images[0], filename) for filename in os.listdir(args.images[0])]
		else:
			filename_list = args.images
		
		#Each file is numbered somehow and images are in numbered order
		#For each filename find the number, then sort the names by number
		regex = re.compile("\d+")
		sorted_filenames = sorted(filename_list, key = lambda filename : int(regex.findall(filename)[0]))

		main(args.x, args.y, sorted_filenames[:args.n])
	else:
		raise Exception("imageSource argument must be a list with length equal to numberOfImages OR the name of a folder holding images.\n{} images given, expected {}".format(len(args.images), args.n))
		exit()