#name:			segyreader.py
#created:		Jan 2019
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to read a SEGY file

import struct
import os.path
import time
import re
import math
import pprint

from datetime import datetime
from datetime import timedelta

from encoding import guess_encoding, is_supported_encoding, UnsupportedEncodingError

UNSET = object()
HEADER_NEWLINE = '\r\n'

CARD_LENGTH 				= 80
CARDS_PER_HEADER 			= 40
TEXTUAL_HEADER_NUM_BYTES 	= CARD_LENGTH * CARDS_PER_HEADER
BINARY_HEADER_NUM_BYTES 	= 400
REEL_HEADER_NUM_BYTES 		= TEXTUAL_HEADER_NUM_BYTES + BINARY_HEADER_NUM_BYTES
TRACE_HEADER_NUM_BYTES 		= 240
# END_TEXT_STANZA = "((SEG: EndText))"

###############################################################################################
def main():
	#open the file for reading by creating a new Reader class and passing in the filename to open.
	filename	 = "Z:/Subsea-Cloud/OceanInfinity/IslandPride/F12/WideArea/20191207_6100_126_P11_S10_A14_144/2_post_dive_48h/6-1-2-18_SEG-Y/Envelope/SBP-0174-m028-20191208-085427_P.E.sgy"
	# filename	 = "C:/infinitytool/GGTools/segy/20140614082310.seg"
	# filename	 = "C:/infinitytool/GGTools/segy/SBP-0016-hsas_180-20190507-194247-CH1_I.seg"
	#filename	 = "X:/projects/KrakenVigoTrialsMay2019/RAW/20190507_6100_001_P09_S01_A01_005(Hisas)\\DELIVERABLES\\6-1-2-18_SEG-Y\\Imaginary\\SBP-0016-hsas_180-20190507-194247-CH1_I.seg"
	# report_segy(filename)

	reader = segyreader(filename)
		# now read the header TEXT part of the file header...
	reader.readHeader()

	reader.loadNavigation()
	print(reader.navigation)
	recordCount = 0
	start_time = time.time() # time the process

	reader.rewind()
	reader.readHeader()
	while reader.moreData() > 0:
		if not reader.readDatagram():
			break
		print(reader.sourceX, reader.sourceY)
		recordCount += 1

	print("Read Duration: %.3f seconds, recordCount %d" % (time.time() - start_time, recordCount)) # print the processing time. It is handy to keep an eye on processing performance.
	print("Complete reading file :-)")



###############################################################################
class field:
	name = ""
	fieldtype = ""
	matlabtype = ""
	datasize = 0
	arraycount = 1

	def __init__(self, idx=0, name="", fieldtype="", matlabtype="", datasize=0, arraycount=1):
		self.idx = idx
		self.name = name
		self.fieldtype = fieldtype
		self.matlabtype = matlabtype
		self.datasize = datasize
		self.arraycount = arraycount
		self.value = 0

class segyreader:
	'''class to read a segy file'''
	PacketHeader_fmt = '>' #< == little endian, > == big endian
	reccount = 0
	def __init__(self, fileName):
		if not os.path.isfile(fileName):
			print ("file not found:", fileName)

		self.fileName 			= fileName
		self.fileptr 			= open(fileName, 'rb')
		self.fileSize 			= os.path.getsize(fileName)
		self.fields 			= []
		self.record 			= []
		self.navigation 		= []
		self.header 			= ""
		self.sampleformatsize 	= 0
		self.sampleformat 		= 0
		self.timestamp			= 0
		self.shotpoint			= 0
		self.crs 				= 0
		self.sourceX 			= 0
		self.sourceY 			= 0
		self.groupX 			= 0
		self.groupY 			= 0

		self.encoding = self.guess_textual_header_encoding()

	def printHeader(self):
		print("name,fieldtype,matlabtype,datasize,arraycount")
		for f in self.fields:
			print("%s,%s,%s,%s,%s" % (f.name, f.fieldtype, f.matlabtype, f.datasize, f.arraycount))

	def __str__(self):
		return pprint.pformat(vars(self))

	def loadNavigation(self):
		'''load the navigation from the data trace headers so we can use it for all sorts of things '''
		while self.moreData() > 0:
			if not self.readDatagram():
				break
			ts 				= self.timestamp
			longitude 		= self.sourceX
			latitude 		= self.sourceY
			if (longitude != 0) and (latitude != 0):
				self.navigation.append([ts, longitude, latitude])
			else:
				print ("skipping zero latitude, longitude coordinates")
		return self.navigation

#################################################################################################
#################################################################################################
#################################################################################################
	def readTextHeader(self):
		'''read 3200 bytes of text data '''
		lines = []
		self.rewind()
		self.header = self.fileptr.read(TEXTUAL_HEADER_NUM_BYTES)
		num_bytes_read = len(self.header)
		if num_bytes_read < TEXTUAL_HEADER_NUM_BYTES:
			raise EOFError("Only {} bytes of {} byte textual reel header could be read"
						.format(num_bytes_read, TEXTUAL_HEADER_NUM_BYTES))
		# self.encoding = "ASCII"
		# lines = tuple(bytes(raw_line).decode(self.encoding) for raw_line in self.batched(self.header,CARD_LENGTH))
		return lines
#################################################################################################
	def readsegyversion(self):
		'''read the segy version'''
		SEGYVERSIONBYTEOFFSET = 3500
		original = self.fileptr.tell() #remeber the start point

		ver_fmt 			= '>BB'
		ver_len 			= struct.calcsize(ver_fmt)
		ver_unpack 			= struct.Struct(ver_fmt).unpack
		self.fileptr.seek(SEGYVERSIONBYTEOFFSET, 0) #goto the segy revision and read the version
		s = ver_unpack(self.fileptr.read(ver_len))
		self.majorversion 	= s[0]
		self.minorversion 	= s[1]
		self.fileptr.seek(original, 0) #goto back to start point
		return

#################################################################################################
	def readcoordinatereferencesystem(self):
		'''read the segy version'''
		original = self.fileptr.tell() #remeber the start point

		self.rewind()
		self.readHeader()
		#read a trace which will set the crs property
		if not self.readDatagram():
			return
		self.fileptr.seek(original, 0) #goto back to start point
		return

#################################################################################################
	def readBinaryHeader(self):
		'''read 400 bytes of binary data '''
		self.readsegyversion() #read the segy version so we decode correctly.
		if self.majorversion == 0:
			rec_fmt = '>4s2l8h 12h 4h240s 3h 94s'
		elif self.majorversion == 1:
			rec_fmt = '>4s2l8h 12h 4h240s 3h 94s'
		elif self.majorversion == 2:
			rec_fmt = '>4s2L6H 7H 10HLL 2d4L200s BB3HQ84s' #not yet tested.
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack

		if (self.fileSize - self.fileptr.tell()) >= rec_len:
			s = rec_unpack(self.fileptr.read(rec_len))
			self.samplespertrace 			= s[7]
			self.fixedlengthtraceflag 		= s[29]
			self.extendedtextheaderrecords 	= s[30]
			self.sampleformat 				= s[9]
			if self.sampleformatsize == 1:
				self.sampleformatsize = 4
			elif self.sampleformat == 2:
				self.sampleformatsize = 4
			elif self.sampleformat == 3:
				self.sampleformatsize = 2
			elif self.sampleformat == 4:
				self.sampleformatsize = 4
			elif self.sampleformat == 5:
				self.sampleformatsize = 4
			elif self.sampleformat == 6:
				self.sampleformatsize = 4
			elif self.sampleformat == 7:
				self.sampleformatsize = 4
			elif self.sampleformat == 8:
				self.sampleformatsize = 1
		return

#################################################################################################
	def readTrace(self):
		'''read the trace, skipping the trace data'''
		bytestoread = self.samplesintrace * self.sampleformatsize
		if bytestoread < 0:
			return False
		if (self.fileSize - self.fileptr.tell()) >= bytestoread:
			self.fileptr.read(bytestoread)
			return True

#################################################################################################
	def readTraceHeader(self):
		'''trace header is 240 bytes '''
		rec_fmt = '>4l 3l4hl 7l2h4l5h 10h 20h 11h5l 2h6s2h 2h6s6s h8s'
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack

		if (self.fileSize - self.fileptr.tell()) >= rec_len:
			s = rec_unpack(self.fileptr.read(rec_len))
			self.depthscalar	= s[19]
			self.coordscalar	= s[20]
			if self.coordscalar < 0:
				self.coordscalar = 1/abs(self.coordscalar)
			else:
				self.coordscalar = abs(self.coordscalar)

			tracedate = datetime(s[59], 1, 1) + timedelta(days=s[60] - 1, hours=s[61], minutes=s[62],seconds=s[63])
			self.timestamp = self.to_timestamp(tracedate)
			self.coordunits		= s[25]
			self.samplesintrace	= s[38]
			self.shotpoint		= s[75]
			if self.coordunits == 1:
				self.crs = 1 #metres or feet, so convert accordingly
				self.sourceX 		= s[21] * self.coordscalar * self.crs
				self.sourceY 		= s[22] * self.coordscalar * self.crs
				self.groupX 		= s[23] * self.coordscalar * self.crs
				self.groupY 		= s[24] * self.coordscalar * self.crs
			elif self.coordunits == 2:
				self.crs 			= 1/(60*60) #seconds of arc, so convert to decimal degrees accordingly
				self.sourceX 		= s[21] * self.coordscalar * self.crs
				self.sourceY 		= s[22] * self.coordscalar * self.crs
				self.groupX 		= s[23] * self.coordscalar * self.crs
				self.groupY 		= s[24] * self.coordscalar * self.crs
			elif self.coordunits == 3:
				self.crs 			= 1 #degrees, so convert accordingly
				self.sourceX 		= s[21] * self.coordscalar * self.crs
				self.sourceY 		= s[22] * self.coordscalar * self.crs
				self.groupX 		= s[23] * self.coordscalar * self.crs
				self.groupY 		= s[24] * self.coordscalar * self.crs
			elif self.coordunits == 4:
				self.crs 			= 1 #DDDMMSS, so convert accordingly
				self.sourceX 		= (float(str(s[21])[0:3]) * 10000 * self.coordscalar) + (float(str(s[21])[3:5]) * 100 * self.coordscalar) + (float(str(s[21])[0:3]) * 1 * self.coordscalar)
				self.sourceY 		= (float(str(s[22])[0:3]) * 10000 * self.coordscalar) + (float(str(s[22])[3:5]) * 100 * self.coordscalar) + (float(str(s[22])[0:3]) * 1 * self.coordscalar)
				self.groupX 		= (float(str(s[23])[0:3]) * 10000 * self.coordscalar) + (float(str(s[23])[3:5]) * 100 * self.coordscalar) + (float(str(s[23])[0:3]) * 1 * self.coordscalar)
				self.groupY 		= (float(str(s[24])[0:3]) * 10000 * self.coordscalar) + (float(str(s[24])[3:5]) * 100 * self.coordscalar) + (float(str(s[24])[0:3]) * 1 * self.coordscalar)

		return True
#################################################################################################
	def readExtendedTextHeader(self):
			for i in range(self.extendedtextheaderrecords):
				self.fileptr.read(3200)

#################################################################################################
	def guess_textual_header_encoding(self):
		"""Read the SEG Y card image header, also known as the textual header

		Args:
			fh: A file-like object open in binary mode positioned such that the
				beginning of the textual header will be the next byte to read.

		Returns:
			Either 'cp037' for EBCDIC, 'ascii' for ASCII, or `None` if the encoding
				can not be determined.

		"""
		original = self.fileptr.tell()

		raw_header = self.fileptr.read(TEXTUAL_HEADER_NUM_BYTES)
		encoding = guess_encoding(raw_header)
		self.fileptr.seek(original, 0)

		return encoding


	#################################################################################################
	def _batched(self, batch_size, iterable, padding):
		pending = []
		for item in iterable:
			pending.append(item)
			if len(pending) == batch_size:
				batch = pending
				pending = []
				yield batch
		num_left_over = len(pending)
		if num_left_over > 0:
			if padding is not UNSET:
				pending.extend([padding] * (batch_size - num_left_over))
			yield pending

	#################################################################################################
	def batched(self, iterable, batch_size, padding=UNSET):
		"""Batch an iterable series into equal sized batches.

		Args:
			iterable: The series to be batched.

			batch_size: The size of the batch. Must be at least one.

			padding: Optional value used to pad the final batch to batch_size. If
				omitted, the final batch may be smaller than batch_size.

		Yields:
			A series of lists, each containing batch_size items from iterable.

		Raises:
			ValueError: If batch_size is less than one.
		"""
		if batch_size < 1:
			raise ValueError("Batch size {} is not at least one.".format(batch_size))
		return self._batched(batch_size, iterable, padding)

###############################################################################
	def from_timestamp(self, unixtime):
		return datetime(1970, 1 ,1) + timedelta(seconds=unixtime)

###############################################################################
	def to_timestamp(self, recordDate):
		return (recordDate - datetime(1970, 1, 1)).total_seconds()

###############################################################################
	def close(self):
		'''close the current file'''
		self.fileptr.close()

###############################################################################
	def rewind(self):
		'''go back to start of file'''
		self.fileptr.seek(0, 0)

###############################################################################
	def readHeader(self):
		self.readTextHeader()
		self.readBinaryHeader()
		self.readExtendedTextHeader()

###############################################################################
	def currentPtr(self):
		'''report where we are in the file reading process'''
		return self.fileptr.tell()

###############################################################################
	def moreData(self):
		'''report how many more bytes there are to read from the file'''
		return self.fileSize - self.fileptr.tell()

###############################################################################
	def readDatagram(self):
		if (self.fileSize - self.fileptr.tell()) >= 0:
			if not self.readTraceHeader():
				return False
			if not self.readTrace():
				return False
			self.record = [self.timestamp, self.sourceX, self.sourceY]
			return True
		else:
			return False

###############################################################################
###############################################################################
if __name__ == "__main__":
		main()
