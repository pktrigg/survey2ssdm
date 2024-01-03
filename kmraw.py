#name:			ea440rawreader.py
#created:		Jan 2019
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to read a Konsgberg EA440 file

from struct import Struct, calcsize
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime
from datetime import timedelta

# Each raw data file contains a set of datagrams. 
# The datagrams are in XML, binary or text (ASCII) format.The datagram sequence in the raw data file is not fixed. It depends
# on the number of installed frequency channels. In this context, the term channel is used
# as a common term to identify the combination of transceiver, transducer and operating
# frequency

# File header
# Each raw data file always starts with the following datagram types:
# 1 Configuration XML datagram
# This is an XML datagram. The type is XML0.
# The Configuration XML datagram is the first datagram in the raw data file. The
# Configuration XML datagram contains parameters that are not subject to change in
# the file and describes the system used for this recording.

# 2 Filter binary datagram
# This is a binary datagram. The type is FIL1
# The Filter binary datagrams contains filter coefficients used for filtering the received
# signal. The number of Filter datagrams depends on the number of filter stages
# in the transceiver.
# EA440 systems with the Wide Band Transceiver (WBT) (and similar) have two
# Filter datagrams. The first datagram contains the filter parameters from the
# transceiver, while the second datagram contains the filter parameters from the
# EA440 program. The two filter datagrams have the same structure. They are
# referred to as "Stage 1" and "Stage 2"



###############################################################################################
def main():

	# a = KMRAWreader(r'C:\Users\phpra\Downloads\D20221006-T130004.raw')

	# a = KMRAWreader(r"C:\sampledata\raw\D20221007-T162827.raw")

	# a = KMRAWreader(r"C:\sampledata\raw\D20221006-T181927.raw")

	# reader = KMRAWreader(r"C:\sampledata\raw\D20221006-T181926.raw")

	reader = KMRAWreader(r"C:\sampledata\raw\D20221009-T040620.raw")
###############################################################################################
class KMRAWreader:
	"""Class to read EA440 raw files."""

	###############################################################################################
	def __init__(self, file):
		self.file = Path(file)
		if not self.file.is_file():
			return 'The file provided was not found!'
		# Open the file
		self.fileptr = open(self.file, 'rb')
		# Get the size of the file
		self.filesize = self.file.stat().st_size
		self.navigation = []

		self.readHeader()
		# navigation = self.loadnavigation()


		# self.rewind()
		# self.readHeader()

		# Read, identify and store the datagrams
		# while self.moredata() > 0:
		# 	self.header.read()
		# 	self.readdatagram()
		# 	print(self.header.dgm_type)
			
		# 	if  'MRU1' in self.header.dgm_type:
		# 		self.decodeMRU1()

		# 	if self.header.dgm_type == 'NME0':
		# 		print(self.databytes)

	###############################################################################
	def rewind(self):
		'''go back to start of file'''
		self.fileptr.seek(0, 0)

	###############################################################################
	def readHeader(self):
		# Create the header instance class
		self.header = Header(self.fileptr)

		# Create XML class instance
		self.xml = XML(self.fileptr)

		self.databytes = None
		self.xmldata = None

	###############################################################################
	def moredata(self):
		'''report how many more bytes there are to read from the file'''
		return self.filesize - self.fileptr.tell()
	###############################################################################################
	def loadnavigation(self, step=0):
		'''load the navigation from the data trace headers so we can use it for all sorts of things '''

		lastimestamp = 0
		self.rewind()
		self.readHeader()

		while self.moredata() > 0:
			self.header.read()
			self.readdatagram()
			
			if  'MRU1' in self.header.dgm_type:
				self.decodeMRU1()

				ts 				= self.timestamp
				longitude 		= self.longitude
				latitude 		= self.latitude

				if (ts - lastimestamp) < step:
					# skip...  performance increase
					continue

				if (longitude != 0) and (latitude != 0):
					self.navigation.append([ts, longitude, latitude])
					lastimestamp = ts
				else:
					print ("skipping zero latitude, longitude coordinates")
		return self.navigation

	###############################################################################
	def close(self):
		'''close the current file'''
		self.fileptr.close()

	###############################################################################################
	def readdatagram(self):
		"""Read the file based on the datagram type."""
		# Get the XML datagrams
		if self.header.dgm_type == 'XML0':
			self.xmldata = self.xml.read(self.header.numbytes)
			# Skip the end of the datagram
			self.databytes = self.fileptr.read(calcsize('<I'))
		else:
			self.databytes = self.fileptr.read(self.header.numbytes - 8)

###############################################################################################
	def decodeMRU1(self):
		'''this is the KMBinary file format from the seapath'''
		datagramheader = '<'
		self.dgmMRUdef = '<4s2h3L 2df 4f 3f 3f 7f 3f 2Lf '

		self.dgm_size = calcsize(self.dgmMRUdef)
		self.unpack_MRU = Struct(self.dgmMRUdef).unpack_from
		s = self.unpack_MRU(self.databytes)


		# Start id #KMB char 4U
		self.startid						= s[0]
		# Dgm length uint16 2U
		self.dgmlength						= s[1]
		# Dgm version (=1) uint16 2U
		self.dgmversion						= s[2]
		# UTC seconds s uint32 4U
		self.utcseconds						= s[3]

		# UTC nanoseconds
		self.nanoseconds					= s[4]
		# Status uint32 4U
		self.status							= s[5]

		# Latitude deg double 8F
		self.latitude						= s[6]

		# Longitude deg double 8F
		self.longitude						= s[7]
		# Ellipsoid height m float 4F
		self.ellipsoidheight				= s[8]

		# Roll deg float 4F
		self.roll							= s[9]

		# Pitch deg float 4F
		self.pitch							= s[10]

		# Heading deg float 4F
		self.heading						= s[11]

		# Heave m float 4F
		self.heave							= s[12]
		# Roll rate deg/s float 4F
		self.rollrate						= s[13]
		# Pitch rate deg/s float 4F
		self.pitchrate						= s[14]
		# Yaw rate deg/s float 4F
		self.yawrate						= s[15]
		# North velocity m/s float 4F
		self.northvelocity					= s[16]
		# East velocity m/s float 4F
		self.eastvelocity					= s[17]
		# Down velocity m/s float 4F
		self.downvelocity					= s[18]
		# Latitude error m float 4F
		self.latituderror					= s[19]
		# Longitude error m float 4F
		self.longitudeerror					= s[20]
		# Height error m float 4F
		self.heighterror					= s[21]
		# Roll error deg float 4F
		self.rollerror						= s[22]
		# Pitch error deg float 4F
		self.pitcherror						= s[23]
		# Heading error deg float 4F
		self.headingerror					= s[24]
		# Heave error m float 4F
		self.heaveerror						= s[25]
		# North acceleration m/s2 float 4F
		self.northacceleration				= s[26]
		# East acceleration m/s2 float 4F
		self.eastacceleration				= s[27]
		# Down acceleration m/s2 float 4F
		self.downacceleration				= s[28]
		# Delayed heave:
		# UTC seconds s uint32 4U
		self.delayedheaveutcseconds			= s[29]
		# UTC nanoseconds ns uint32 4U
		self.delayedheaveutcnanoseconds		= s[30]
		# Delayed heave
		self.delayedheave					= s[31]

		self.timestamp  = self.utcseconds + (self.nanoseconds / 1000000000)

		return s
###############################################################################################
class Header:
	"""Reads the datagram header."""

	def __init__(self, fileptr):
		self.dgm_header_def = '<I4sff'

		self.fileptr = fileptr
		self.unpack_header = Struct(self.dgm_header_def).unpack_from
		self.dgm_size = calcsize(self.dgm_header_def)

	###############################################################################################
	def read(self):
		"""Read the datagram header."""
		self.header = self.unpack_header(self.fileptr.read(self.dgm_size))
		self.numbytes 	= self.header[0]
		self.dgm_type 	= self.header[1].decode('utf-8', errors='ignore')
		self.unknown 	= self.header[2]
		self.unknown2 	= self.header[3]

	###############################################################################################
	def __call__(self):
		"""Make the class callable."""
		return self.header

###############################################################################################
class XML:
	###############################################################################################
	def __init__(self, fileptr):
		
		self.fileptr = fileptr
		# Set the xml datagrams type
		self.environment = None
		self.configuration = None
		self.parameter = None

	###############################################################################################
	def read(self, dgm_size):
		"""Read the datagram header."""
		self.dgm_def = f'<{dgm_size-12}s'
		self.unpack_header = Struct(self.dgm_def).unpack_from
		self.dgm_size = calcsize(self.dgm_def)
		xml = self.unpack_header(self.fileptr.read(self.dgm_size))
		xml = xml[0].decode('utf-8').rstrip('\x00')
		### For some reason the xml has an undecode character at the end of the string
		## I will improve the fix for that
		# if '<Configuration>' in xml:
		# 	xml = xml[:-2] + '>'
		# elif '</InitialParameter>' in xml:
		# 	xml = xml[:-3]
		# elif '</Environment>' in xml:
		# 	xml = xml[:-3]
		# elif '<Sensor Type=' in xml:
		# 	xml = xml[:-2]
		# elif '</Parameter>' in xml:
		# 	xml = xml[:-2]
		# else:
		# 	xml = xml[:-3]

		xml = ET.fromstring(xml)

		if 'Configuration' == xml.tag:
			self.configuration = xml
		elif 'Environment' == xml.tag:
			self.environment = xml
		elif 'Parameter' == xml.tag:
			self.parameter = xml


###############################################################################
def from_timestamp(unixtime):
	return datetime(1970, 1 ,1) + timedelta(seconds=unixtime)

###############################################################################
def to_timestamp(recordDate):
	return (recordDate - datetime(1970, 1, 1)).total_seconds()

###############################################################################
###############################################################################
if __name__ == "__main__":
		main()

