import argparse
import os
import re
import math

import vtk
from numpy import fromfile

#Builds the sliders and buttons
def build_UI(pipeline, inital_thresh, min_thresh, max_thresh, filename_list):
	print("Building UI")
	#Values define sizes of sliders
	tube_width = 0.022
	slider_width = 0.04
	endcap_width = 0.06
	endcap_height = 0.003

	#Slider to control the threshold value used by MarchingCubes
	slider_thresh = vtk.vtkSliderRepresentation2D()
	slider_thresh.SetMinimumValue(min_thresh)
	slider_thresh.SetMaximumValue(max_thresh)
	slider_thresh.SetValue(inital_thresh)
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
	slider_thresh_widget.SetInteractor(pipeline["interactor"])
	slider_thresh_widget.SetRepresentation(slider_thresh)
	slider_thresh_widget.SetAnimationModeToAnimate()
	slider_thresh_widget.EnabledOn()
	slider_thresh_widget.SetNumberOfAnimationSteps(10)

	#EndInteracitonEvent means the change occurs when the slider is released - this is necessary on larger datasets
	slider_thresh_widget.AddObserver(vtk.vtkCommand.EndInteractionEvent, SliderThreshCallback(pipeline["contour"]))
	#------------------------------------------------------------------------------

	#Slider to control the number of images which are used too build the model
	#Defaults to all images, reducing this creates a slicing effect
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
	slider_cutoff_widget.SetInteractor(pipeline["interactor"])
	slider_cutoff_widget.SetRepresentation(slider_cutoff)
	slider_cutoff_widget.SetAnimationModeToAnimate()
	slider_cutoff_widget.EnabledOn()
	slider_cutoff_widget.SetNumberOfAnimationSteps(10)

	slider_cutoff_widget.AddObserver(vtk.vtkCommand.EndInteractionEvent, SliderCutoffCallback(filename_list, pipeline["source"]))

	return slider_thresh, slider_thresh_widget, slider_cutoff, slider_cutoff_widget

#Callbacks for sliders
#Map slider_thresh value changes to marchingcubes threshold
class SliderThreshCallback():
	def __init__(self, surface_extractor):
		self.surface_extractor = surface_extractor

	def __call__(self, caller, event):
		slider_widget = caller
		new_thresh = slider_widget.GetRepresentation().GetValue()
		self.surface_extractor.SetValue(0, new_thresh)

#Map slider_cutoff value changes to number of images from filename_list read in
class SliderCutoffCallback():
	def __init__(self, filename_list, reader):
		self.filename_list = filename_list
		self.reader = reader

	def __call__(self, caller, event):
		slider_widget = caller
		#Values must be integers
		slice_val = math.floor(slider_widget.GetRepresentation().GetValue())
		caller.GetRepresentation().SetValue(slice_val)

		self.filename_array = vtk.vtkStringArray()
		self.filename_array.Initialize()
		for filename in self.filename_list[:slice_val]:
			self.filename_array.InsertNextValue(filename)
		self.reader.SetFileNames(self.filename_array)
		#Must implicitly state read has been modified in order to reread the data (with new set of images)
		self.reader.Modified()

#Determine value for isosurface automatically, along with max and min values in image for slider scales
#Good values (found manually) for 3 test datasets are included
def find_thresholds(filenames):
	print("Determining contour threshold")

	#Use good values for the 3 test datasets which were found manually
	#Otherwise return 10% of the maximum voxel value, as recommended
	max_val = 0
	min_val = 65536
	for filename in filenames:
		#Create an array of unsigned short ints from the binary files, then search for min/max
		val_array = fromfile(filename, dtype = ">u2")
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
		iso_val = (max_val - min_val) // 10

	return min_val, max_val, iso_val

#Build and execute pipeline, from reading image files through to rendering model
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
	#to bunny. Could add option to change this with another slider?
	if "CThead" in filename_list[0]:
		reader.SetDataSpacing(1, 1, 2)
	else:
		reader.SetDataSpacing(1, 1, 1.48)
	#Size of images
	reader.SetDataExtent(0, image_width - 1, 0, image_height - 1, 0, 0)

	#Smooth noise in images (before building mesh)
	pre_smoother = vtk.vtkImageGaussianSmooth()
	pre_smoother.SetInputConnection(reader.GetOutputPort())

	#Create isosurface from voxel grid
	surface_extractor = vtk.vtkMarchingCubes()
	#surface_extractor = vtk.vtkContourFilter()
	surface_extractor.SetInputConnection(pre_smoother.GetOutputPort())
	surface_extractor.SetValue(0, thresh)

	#Map polygon mesh to graphics primitives
	surface_mapper = vtk.vtkPolyDataMapper()
	surface_mapper.SetInputConnection(surface_extractor.GetOutputPort())
	#Scalar visibility sets the isosurface to a value related to the image scalars
	#(maybe average? Documentation unclear) which we don't want.
	surface_mapper.ScalarVisibilityOff()

	#Create actor for rendering
	surface = vtk.vtkActor()
	surface.SetMapper(surface_mapper)
	#Set colour and lighting for model
	surface.GetProperty().SetColor(0.7, 0.7, 0.7)
	surface.GetProperty().SetSpecular(0.25)
	surface.GetProperty().SetSpecularPower(0.2)

	#Render and display actor(s)
	renderer = vtk.vtkRenderer()
	renderer.AddActor(surface)

	#Set to True to produce 2 isosurface models.
	#This code is specifically suited to the CThead dataset
	#Could be extended to any number of surfaces (ContourFilter can easily handle multiple threshold values, for instance)
	two_surface_models = False
	if two_surface_models:
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

	#Small data dict containing references to all the parts of the pipeline for convenience
	pipeline = {"source"	:	reader,
				"filter"	:	pre_smoother,
				"contour"	:	surface_extractor,
				"mapper"	:	surface_mapper,
				"actor"		:	surface,
				"renderer"	:	renderer,
				"window"	:	window,
				"interactor":	interactor}

	#Build sliders for UI. Lots of boilerplatey code, moved to separate function for clarity
	slider_thresh, slider_thresh_widget, slider_cutoff, slider_cutoff_widget = build_UI(pipeline, thresh, min_image_val, max_image_val, filename_list)

	interactor.Initialize()
	interactor.Start()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description = 'Visualise models of 3D scans from 2D images. Images must be rectangular binary images' + 
													' (of the same size), with each voxel value specified by a big endian 2 byte value.\n\n' + 
													'Image files can be given as a space separated list, or as a folder name which contains ONLY' + 
													' the images. Images must be numbered from 1 to numberOfImages somewhere in the filename',
									formatter_class = argparse.RawDescriptionHelpFormatter)
	parser.add_argument('x', metavar = 'xPixelsPerImage', type = int, help = 'Width of images')
	parser.add_argument('y', metavar = 'yPixelsPerImage', type = int, help = 'Height of images')
	parser.add_argument('n', metavar = 'numberOfImages', type = int, help = 'Number of images (Which defines the depth of the model)')
	parser.add_argument('images', metavar = 'imageSource', nargs = "+", type = str, help = 'List of image names OR name of folder containing (only) images')
	
	args = parser.parse_args()
	#Program designed to accept name of folder to iterate over, or the n individual images format which was specified
	if len(args.images) == 1 or len(args.images) == args.n:
		#args.images is a folder name
		if len(args.images) == 1:
			filename_list = [os.path.join(os.curdir, args.images[0], filename) for filename in os.listdir(args.images[0])]

		#args.images is a list of files
		else:
			filename_list = args.images
		
		#Each file is numbered somehow and images are in numbered order
		#For each filename find the number, then sort the names by number
		regex = re.compile("\d+")
		sorted_filenames = sorted(filename_list, key = lambda filename : int(regex.findall(filename)[0]))

		main(args.x, args.y, sorted_filenames[:args.n])
	else:
		raise Exception("imageSource argument must be a list with length equal to numberOfImages OR the name of a folder holding images.\n{} images specified, expected {}".format(len(args.images), args.n))
		exit()