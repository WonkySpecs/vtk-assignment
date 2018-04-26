import argparse
import os

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

	return max_val // 10

def main(image_width, image_height, filenames_list):
	thresh = find_threshold(filenames_list)

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
	reader.SetDataScalarTypeToUnsignedShort()
	reader.SetDataByteOrderToBigEndian()
	#Spacing is 1:1:2 as specified
	reader.SetDataSpacing(1, 1, 2)
	#Size of images
	reader.SetDataExtent(0, image_width - 1, 0, image_height - 1, 0, 0)

	surface_extractor = vtk.vtkMarchingCubes()
	surface_extractor.SetInputConnection(reader.GetOutputPort())
	surface_extractor.SetValue(0, thresh)

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
		#We expect images in format name.id with id from 1 to num_images
		#Sort filenames by prefix	
		sorted_filenames = sorted(filenames_list, key = lambda f : int(f.split(".")[-1]))

		main(args.x, args.y, sorted_filenames[:args.n])
	else:
		raise Exception("imageSource argument must be a list with length equal to numberOfImages OR the name of a folder holding images")
		exit()

	