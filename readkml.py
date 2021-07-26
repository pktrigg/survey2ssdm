#name:			readkml.py
#created:		Jan 2021
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to read basid information from a KML file wothut the need for an external module

import os
import xml.etree.ElementTree as ET
	
##############################################################################
def main():
	r = reader(".\demo1\SI_1006_Survey_Area_E_Main_Lines.kml")
	print (r.lines)
###############################################################################
class reader:
	'''# read a kml file and return the information as a list of survey lines, points
	# attitude = [[1,100],[2,200], [5,500], [10,1000]]
	# tsRoll = cTimeSeries(attitude)
	# print(tsRoll.getValueAt(6))'''
	# def __init__(self, list2D):
	# 	'''the time series requires a 2d series of [[timestamp, value],[timestamp, value]].  It then converts this into a numpy array ready for fast interpolation'''
	# 	self.name = "2D time series"

###############################################################################
	def __init__(self, kmlfilename):
		self.name = kmlfilename
		self.surveylines = []
		self.surveypoints = []

		tree = ET.parse(kmlfilename)
		root = tree.getroot()

		linename = ""
		for elem in tree.iter():
			# print (elem.tag, elem.attrib)
			if 'coordinates' in elem.tag:
				coords = elem.text
				coords = coords.replace(" ", ",")
				words = coords.split(",")
				if len(words) > 4:
					# now add to the line list
					pm = kmlline(float(words[0]), float(words[1]), float(words[2]), float(words[3]), float(words[4]), float(words[5]), linename)
					self.surveylines.append(pm)
				else:
					# now add to the point list
					pm = kmlline(float(words[0]), float(words[1]), float(words[2]), linename)
					self.surveypoints.append(pm)
			if 'name' in elem.tag:
				linename = elem.text

		return

###############################################################################
class kmlline:
	'''# definition of a survey line'''
###############################################################################
	def __init__(self, x1=0, y1=0, z1=0, x2=0, y2=0, z2=0, name="unnamed"):

		self.name = name
		self.x1 = x1
		self.y1 = y1
		self.z1 = z1
		self.x2 = x2
		self.y2 = y2
		self.z2 = z2
class kmlpoint:
	'''# definition of a survey line'''
###############################################################################
	def __init__(self, x1=0, y1=0, z1=0, name="unnamed"):

		self.name = name
		self.x1 = x1
		self.y1 = y1
		self.z1 = z1

###############################################################################
if __name__ == "__main__":
	main()
