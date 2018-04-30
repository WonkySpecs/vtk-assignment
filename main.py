import argparse
import os
import re

import vtk
from numpy import fromfile

def find_threshold(filenames):
	print("Determining contour threshold")
	max_val = 0
	for filename in filenames:
		#We create an array of unsigned short ints from the binary files
		val_array = fromfile(filename, dtype = ">u2")
		m = max(val_array)
		if m > max_val:
			max_val = m

	return max_val // 4

def main(image_width, image_height, filenames_list):
	#thresh = find_threshold(filenames_list)
	#Good that ive found:
	# CThead 710 (head)/1150 (skull)
	# MRBrain 1300
	# bunny 1500
	thresh = 1300

	print("{} contour value".format(thresh))

	filename_array = vtk.vtkStringArray()

	for filename in filenames_list:
		filename_array.InsertNextValue(filename)

	#Set reader attributes
	reader = vtk.vtkImageReader2()
	reader.SetFileNames(filename_array)
	#Images are 2D with a single scalar per cell
	reader.SetFileDimensionality(2)
	reader.SetNumberOfScalarComponents(1)
	#Data held as unsigned big endian shorts, as specified
	reader.SetDataScalarTypeToShort()
	reader.SetDataByteOrderToBigEndian()
	
	#Set spacing - the spacing between images is generally different to the spacing between pixels
	# reader.SetDataSpacing(1, 1, 2)
	#Bunny spacing
	reader.SetDataSpacing(1, 1, 1.48)

	#Size of images
	reader.SetDataExtent(0, image_width - 1, 0, image_height - 1, 0, 0)

	smoother = vtk.vtkImageGaussianSmooth()
	smoother.SetInputConnection(reader.GetOutputPort())
	#smoother = vtk.vtkImageMedian3D()
	#smoother.SetInputConnection(reader.GetOutputPort())
	#print(smoother.GetStandardDeviations())
	#print(smoother.GetRadiusFactors())

	surface_extractor = vtk.vtkMarchingCubes()
	surface_extractor.SetInputConnection(smoother.GetOutputPort())
	surface_extractor.SetValue(0, thresh)

	#largest_component_filter = vtk.vtkConnectivityFilter()
	#largest_component_filter.SetInputConnection(surface_extractor.GetOutputPort())
	#largest_component_filter.SetExtractionModeToAllRegions()
	#largest_component_filter.ColorRegionsOn()

	surface_mapper = vtk.vtkPolyDataMapper()
	surface_mapper.SetInputConnection(surface_extractor.GetOutputPort())
	surface_mapper.ScalarVisibilityOff()

	surface = vtk.vtkActor()
	surface.SetMapper(surface_mapper)
	#set colour

	renderer = vtk.vtkRenderer()
	renderer.AddActor(surface)

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
			filenames_list = [os.path.join(os.curdir, args.images[0], filename) for filename in os.listdir(args.images[0])]
		else:
			filenames_list = args.images
		
		#Each file is numbered somehow and images are in numbered order
		#For each filename find the number, then sort the names by number
		regex = re.compile("\d+")
		sorted_filenames = sorted(filenames_list, key = lambda filename : int(regex.findall(filename)[0]))

		main(args.x, args.y, sorted_filenames[:args.n])
	else:
		for i in args.images:
			num = i.split("\\")[-1]
			print(num)
		raise Exception("imageSource argument must be a list with length equal to numberOfImages OR the name of a folder holding images")
		exit()