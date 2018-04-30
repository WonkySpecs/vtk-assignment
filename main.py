import argparse
import os
import re

import vtk
from numpy import fromfile

def find_threshold(filenames):
	#Good that ive found:
	# CThead 710 (head)/1150 (skull)
	# MRBrain 1300
	# bunny 1500
	print("Determining contour threshold")

	#Good values for the 3 test images have been found manually
	#Otherwise return 10% of the maximum voxel value, as recommended
	if "CThead" in filenames[0]:
		return 710
	elif "MRbrain" in filenames[0]:
		return 1300
	elif "bunny" in filenames[0] or filenames[0] == "1":
		return 1500
	else:
		max_val = 0
		for filename in filenames:
			#We create an array of unsigned short ints from the binary files
			val_array = fromfile(filename, dtype = ">u2")
			m = max(val_array)
			if m > max_val:
				max_val = m

		return max_val // 10

def main(image_width, image_height, filename_list):
	thresh = find_threshold(filename_list)

	print("{} contour value".format(thresh))

	filename_array = vtk.vtkStringArray()

	for filename in filename_list:
		filename_array.InsertNextValue(filename)

	#Set reader attributes
	#Designed to read in len(filename_list) image_width x image_height images
	#Each voxel value is represented by a big endian short (2 bytes)
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

	surface = vtk.vtkActor()
	surface.SetMapper(surface_mapper)
	surface.GetProperty().SetColor(0.7, 0.7, 0.7)
	
	surface.GetProperty().SetSpecular(0.25)
	surface.GetProperty().SetSpecularPower(0.2)
	surface.GetProperty().SetOpacity(0.35)
	#surface.GetProperty().Set

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

	renderer = vtk.vtkRenderer()
	renderer.AddActor(surface)
	renderer.AddActor(skull)

	window = vtk.vtkRenderWindow()
	window.AddRenderer(renderer)
	window.SetSize(640, 480)

	interactor = vtk.vtkRenderWindowInteractor()
	interactor.SetRenderWindow(window)
	interactor.Initialize()
	interactor.Start()

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