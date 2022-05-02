#name:			geopackage.py
#created:		Jan 2019
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module create a OGC geopackage using native python.  this module works hand in hand with the SSDM schema (SSDM_Geopackage.py), and together they provide an open source OGP SSDM V2.0 implementation of SSDM, which can be opened by QGIS, ESRI.
#description:	An open source implementation the SSDM schema using the OGC geopackage file format unlocks SSDM from the existing restraints that SSDM ONLY works inside ESRI ArcGIS which has license restrictions.
import sqlite3
from sqlite3 import Error
import struct
import sys
import os.path
import fileutils
import datetime
import subprocess
import pyproj
import geodetic

# https://www.ibm.com/support/knowledgecenter/en/SSGU8G_12.1.0/com.ibm.spatial.doc/ids_spat_285.htm
# https://www.ibm.com/support/knowledgecenter/SSGU8G_12.1.0/com.ibm.spatial.doc/ids_spat_280.htm
# https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary
# https://www.tutorialspoint.com/sqlite/sqlite_update_query

###############################################################################
def main():
	'''test the creation of a geopackage using basic python without complex module installs '''

	filename = "C:/temp/geopackage.gpkg"
	con = creategeopackage(filename)

	addsrsrecord(con, "pkpk", 32650)

	createpoints(con)
	createlinestrings(con)
	createpolygons(con)

###############################################################################
class geopackage:
	'''a simple helper class to hold a pyproj geodesy object so we can transform with ease'''
	def __init__(self, filename, epsg = 4326):
		self.epsg = epsg #the epsg code is an integer number.  the name is found from the EPSG database
		self.connection = creategeopackage(filename)
		
	###############################################################################
	def addEPSG(self, epsg="4326" ):
		'''add an EPSG record to the geopackage'''
		self.epsg = epsg
		#load the python proj projection object library if the user has requested it
		self.geo = geodetic.geodesy(self.epsg)
		# extract the name from the epsg database.
		name = self.geo.projection.crs.name
		addsrsrecord(self.connection, name, int(self.epsg))

###############################################################################
###############################################################################
class vectortable:
	'''class to create and manage a vector table'''
	
	def __init__(self, connection, tablename="pointtable", epsg = "4326", type="POINTS", fields=["ID","INTEGER"]):
		self.name 		= tablename
		self.connection = connection
		self.epsg 	= epsg
		self.type		= type
		self.fields		= fields
		self.fieldcount	= len(fields)
		littlenumber 	= -999999999
		bignumber 		=  999999999
		self.envelope 	= [bignumber,littlenumber,bignumber,littlenumber] 	# we need an evelope of min, max X and Y so we can update the pkg_contents table so the data appears correclty in GIS
		
		self.connection = createvectortable(self.connection, self.name, self.envelope, self.type, self.fields, self.epsg) # create the table
	
		self.cursor = self.connection.cursor() 			# open a cursor so we ce use it repeatedly

	###############################################################################
	def addpointrecord(self, x, y, fielddata=[]):
		'''add a record to the table if it has the correct number of fields'''
		if len(fielddata) == self.fieldcount:
			addpointrecord(self.cursor, self.name, self.envelope, [x,y], fielddata)

	###############################################################################
	def addlinestringrecord(self, linestring=[], fielddata=[]):
		'''add a record to the table if it has the correct number of fields and some vector data'''
		if len(linestring) == 0:
			return
		if len(fielddata) == self.fieldcount:
			addlinestringrecord(self.cursor, self.name, self.envelope, linestring, fielddata)

	###############################################################################
	def addpolygonrecord(self, polygon=[], fielddata=[]):
		'''add a record to the table if it has the correct number of fields and some vector data'''
		if len(polygon) == 0:
			return
		if len(fielddata) == self.fieldcount:
			addpolygonrecord(self.cursor, self.name, self.envelope, polygon, fielddata)

	###############################################################################
	def close(self):
		'''close the table''' 	
		update_envelope(self.connection, self.name, self.envelope)
		self.connection.commit()
	
###############################################################################
def createpoints(con):
	'''create a sample point table'''
	tablename 	= "trackpoint" 	# the name of the layer 
	envelope 	= [0,0,0,0] 	# we need an evelope of min, max X and Y so we can update the pkg_contents table so the data appears correclty in GIS
	srsid 		= 4326			# the spatial reference
	type 		= "POINT"		# the point type.  POINT, LINESTRING, POLYGON etc as per OGC types
	fields 		= [["ID","INTEGER"],["NAME","STRING"]]
	
	con = createvectortable(con, tablename, envelope, type, fields, srsid) # create the table
	cur = con.cursor() 			# open a cursor so we ce use it repeatedly
	
	fielddata = []
	fielddata.append(123)
	fielddata.append("hello")
	for x in range(100,200):
		sys.stdout.write('.')
		sys.stdout.flush()
		for y in range (100,250):
			# now write the point to the table.
			addpointrecord(cur, tablename, envelope, [x,y], fielddata)
	con.commit()
	update_envelope(con, tablename, envelope)
	sys.stdout.write('\n')

###############################################################################
def createlinestrings(con):
	''' create a demo linestring table'''
	tablename 	= "trackline"	# the table and layer name
	envelope 	= [0,0,0,0] 	# we need an evelope of min, max X and Y so we can update the pkg_contents table so the data appears correclty in GIS
	srsid 		= 4326			# the coordinate reference system.  EPSG codes
	type 		= "LINESTRING"	# the OGC geopetry type
	fields 		= [["ID","INTEGER"],["NAME","STRING"],["Date","DATE"]]
	
	createvectortable(con, tablename, envelope, type, fields, srsid)
	cur = con.cursor()

	# create some dummy field data.
	fielddata = []
	fielddata.append(123)
	fielddata.append("LineName")
	fielddata.append(datetime.datetime.now())

	# add some sample linestrings, a box:-)
	addlinestringrecord(cur, tablename, envelope, [0,0,0,10], fielddata)
	addlinestringrecord(cur, tablename, envelope, [0,10,10,10], fielddata)
	addlinestringrecord(cur, tablename, envelope, [10,10,10,0], fielddata)
	addlinestringrecord(cur, tablename, envelope, [10,0,0,0], fielddata)
	con.commit()

	#now update the contents table which has the envelope
	update_envelope(con, tablename, envelope)
	
	sys.stdout.write('.')
	sys.stdout.write('\n')
	sys.stdout.flush()

###############################################################################
def createpolygons(con):
	''' create a demo polygon table'''
	tablename 	= "coverage"	# the table and layer name
	envelope 	= [0,0,0,0] 	# we need an evelope of min, max X and Y so we can update the pkg_contents table so the data appears correclty in GIS
	srsid 		= 4326			# the coordinate reference system.  EPSG codes
	type 		= "POLYGON"		# the OGC geopetry type
	fields 		= [["ID","INTEGER"],["NAME","STRING"],["Date","DATE"]]
	
	createvectortable(con, tablename, envelope, type, fields, srsid)
	cur = con.cursor()

	# create some dummy field data.
	fielddata = []
	fielddata.append(123)
	fielddata.append("LineName")
	fielddata.append(datetime.datetime.now())

	# add some sample linestrings, a box:-)
	vectors = []

	# add an inner polygon
	vectors += makebox(0,0,100,50)
	addpolygonrecord(cur, tablename, envelope, vectors, fielddata)

	vectors += makebox(10,10,10,5)
	addpolygonrecord(cur, tablename, envelope, vectors, fielddata)

	con.commit()

	#now update the contents table which has the envelope
	update_envelope(con, tablename, envelope)
	
	sys.stdout.write('.')
	sys.stdout.write('\n')
	sys.stdout.flush()

###############################################################################
def makebox(x,y,length,height):
	vector = []
	vector.append(x)
	vector.append(y)

	vector.append(x)
	vector.append(y + height)
	
	vector.append(x + length)
	vector.append(y + height)
	
	vector.append(x + length)
	vector.append(y)

	vector.append(x)
	vector.append(y)

	return vector

###############################################################################
def creategeopackage(filename):
	'''highest level geopackage creatiopn method.  call this first!'''

	contentstable 		= """CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY NOT NULL , data_type TEXT NOT NULL,identifier TEXT UNIQUE, description TEXT DEFAULT '', last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE, srs_id INTEGER, CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)); """
	srstable 			= """CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL, srs_id INTEGER PRIMARY KEY NOT NULL , organization TEXT NOT NULL, organization_coordsys_id INTEGER NOT NULL, definition  TEXT NOT NULL, description TEXT ); """
	geometrytable 		= """CREATE TABLE gpkg_geometry_columns ( table_name TEXT NOT NULL, column_name TEXT NOT NULL, geometry_type_name TEXT NOT NULL, srs_id INTEGER NOT NULL, z TINYINT NOT NULL, m TINYINT NOT NULL, CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name), CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name), CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id) ); """
	extensiontable 		= """CREATE TABLE gpkg_extensions ( table_name TEXT, column_name TEXT, extension_name TEXT NOT NULL, definition TEXT NOT NULL, scope TEXT NOT NULL, CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name) );"""
	tilematrixtable 	= """CREATE TABLE gpkg_tile_matrix ( table_name TEXT NOT NULL, zoom_level INTEGER NOT NULL, matrix_width INTEGER NOT NULL, matrix_height INTEGER NOT NULL, tile_width INTEGER NOT NULL, tile_height INTEGER NOT NULL, pixel_x_size DOUBLE NOT NULL, pixel_y_size DOUBLE NOT NULL, CONSTRAINT pk_ttm PRIMARY KEY (table_name, zoom_level), CONSTRAINT fk_tmm_table_name FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name) );"""
	tilematrixsettable 	= """CREATE TABLE gpkg_tile_matrix_set ( table_name TEXT PRIMARY KEY NOT NULL, srs_id INTEGER NOT NULL, min_x DOUBLE NOT NULL, min_y DOUBLE NOT NULL, max_x DOUBLE NOT NULL, max_y DOUBLE NOT NULL, CONSTRAINT fk_gtms_table_name FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name), CONSTRAINT fk_gtms_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id) );"""

	# always ensure we make a new file...
	# if os.path.isfile(filename):
	# 	filename = fileutils.createOutputFileName(filename)

	print ("Creating GeoPackage: %s" % (filename))
	conn = create_connection(filename)
	createtable(conn, contentstable)
	createtable(conn, srstable)
	createtable(conn, geometrytable)
	createtable(conn, extensiontable)
	createtable(conn, tilematrixtable)
	createtable(conn, tilematrixsettable)

	adddefaultsrsrecords(conn)
	return conn

###############################################################################
def create_connection(db_file):
	""" create a database connection to a SQLite database """
	try:
		conn = sqlite3.connect(':memory:')
		conn = sqlite3.connect(db_file)
		print(sqlite3.version)
	except Error as e:
		print(e)
	finally:
		return conn
###############################################################################
def createtable(conn, create_table_sql):
	"""create a table from the create_table_sql statement
	:param conn: Connection object
	:param create_table_sql: a CREATE TABLE statement
	:return:
	"""
	try:
		c = conn.cursor()
		c.execute(create_table_sql)
	except Error as e:
		print(e)

###############################################################################
def adddefaultsrsrecords(conn):
	'''create default srs records as per ogc specification'''
	cur = conn.cursor()

	sql = """INSERT OR IGNORE INTO "main"."gpkg_spatial_ref_sys" (
		"srs_name",
		"srs_id",
		"organization",
		"organization_coordsys_id",
		"definition",
		"description")
	VALUES (
		'Undefined cartesian SRS',
		'-1',
		'NONE',
		'-1',
		'undefined',
		'undefined cartesian coordinate reference system')
		"""
	try:
		cur.execute(sql)
	except Error as e:
		print(e)

	sql = """INSERT OR IGNORE INTO "main"."gpkg_spatial_ref_sys" (
		"srs_name",
		"srs_id",
		"organization",
		"organization_coordsys_id",
		"definition",
		"description")
	VALUES (
		'Undefined geographic SRS',
		'0',
		'NONE',
		'0',
		'undefined',
		'undefined geographic coordinate reference system')
		"""
	try:
		cur.execute(sql)
	except Error as e:
		print(e)

	sql = """
	INSERT OR IGNORE INTO 'main'.'gpkg_spatial_ref_sys' (
		'srs_name',
		'srs_id',
		'organization',
		'organization_coordsys_id',
		'definition',
		'description')
	VALUES (
		"WGS 84 geodetic",
		"4326",
		"EPSG",
		"4326",
		"GEOGCS['WGS 84',DATUM['WGS_1984',SPHEROID['WGS 84',6378137,298.257223563,AUTHORITY['EPSG','7030']],AUTHORITY['EPSG','6326']],PRIMEM['Greenwich',0,AUTHORITY['EPSG','8901']],UNIT['degree',0.0174532925199433,AUTHORITY['EPSG','9122']],AUTHORITY['EPSG','4326']]",
		"longitude/latitude coordinates in decimal degrees on the WGS 84 spheroid")
		"""
	try:
		cur.execute(sql)
	except Error as e:
		print(e)

	try:
		conn.commit()
	except Error as e:
		print(e)

	return cur.lastrowid

###############################################################################
def addsrsrecord(conn, name="WGS84", epsg=4326):
	'''add a new srs record to the gpkg'''
	cur = conn.cursor()

	sql = """INSERT OR IGNORE INTO "main"."gpkg_spatial_ref_sys" (
		"srs_name",
		"srs_id",
		"organization",
		"organization_coordsys_id",
		"definition",
		"description")
	VALUES ("""
	sql +=	"'" + name + "'" + ","
	sql +=	"'" + str(epsg) + "'"+ ","
	sql +=  "NONE',"
	sql +=	"'" + str(epsg) + "'"+ ","
	sql +=	"'EPSG',"
	sql +=	"'user specified epsg code')"
	
	cur.execute(sql)
	conn.commit()

	return cur.lastrowid

###############################################################################
def addgeometryrecord(conn, tablename, vectortype, srsid):
	'''create the geopackage geometry table which contains a list of layers and the srs for each'''
	cur = conn.cursor()
	sql = """INSERT OR IGNORE INTO "main"."gpkg_geometry_columns" (
		"table_name",
		"column_name",
		"geometry_type_name",
		"srs_id",
		"z",
		"m")
	VALUES (?,?,?,?,?,?)
	"""
	v = (tablename,	'geom', vectortype, srsid, '0', '0')

	try:
		cur.execute(sql, v)
		conn.commit()
	except Error as e:
		print(e)

	return cur.lastrowid

###############################################################################
def createvectortable(connection, tablename, envelope, type, fields, srsid=4326):
	addgeometryrecord(connection, tablename, type, srsid)
	# add new table to contents package
	addtabletocontents(connection, tablename, envelope, srsid)
	cur = connection.cursor()

	fieldstr = "( "
	# fieldstr = "( 'fid' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"
	for f in fields:
		fieldstr += "'" + f[0] + "' " + f[1] + ", "
	fieldstr += "'geom'" + type
	fieldstr += ")"
	sql = "CREATE TABLE if not exists " + tablename + fieldstr
	# sql = "CREATE TABLE " + tablename + """( "fid" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, "geom" POINT)"""

	try:
		cur.execute(sql)
		connection.commit()
	except Error as e:
		print(e)
	print("Created vector data table: %s" % (tablename))
	return connection

######################################################################f#########
def	addtabletocontents(conn, tablename, envelope, srsid):
	cur = conn.cursor()
	filter = ""
	lastchange = ""
	sql = "INSERT OR IGNORE INTO gpkg_contents VALUES (?,?,?,?,?,?,?,?,?,?)"
	v = (tablename, "features", tablename, filter, lastchange, envelope[0], envelope[1], envelope[2], envelope[3], srsid)
	# v = (tablename, "features", tablename, filter, lastchange, min_x, min_y, max_x, max_y, srsid)
	try:
		cur.execute(sql, v)
		conn.commit()
	except Error as e:
		print(e)
	return cur.lastrowid

###############################################################################
def update_envelope(conn,tablename, envelope):
	cur = conn.cursor()
	sql = "UPDATE gpkg_contents SET min_x = " + str(envelope[0]) 
	sql += ", max_x = " + str(envelope[1])  
	sql += ", min_y = " + str(envelope[2]) 
	sql += ", max_y = " + str(envelope[3])
	sql += " WHERE table_name == '" + tablename + "';"
	cur.execute(sql)
	conn.commit()

###############################################################################
def	addpointrecord(cursor, tablename, envelope, vector, fielddata, epsg=4326):
	'''add a new POINT to the table'''
	envelope = calcenvelope(envelope, vector)
	wkb = createpoint(vector, epsg)
	fielddata.append(wkb)
	values = " VALUES ("
	for _ in range(len(fielddata)):
		values += "?,"
	values = values[:-1] + ")"
	sql = "INSERT INTO " + tablename + values
	v = tuple(fielddata)
	cursor.execute(sql, v)

###############################################################################
def	addlinestringrecord(cursor, tablename, envelope, vectors, fielddata):
	'''add a new LINESTRING to the table'''
	# update the envelope
	envelope = calcenvelope(envelope, vectors)
	wkb = createlinestring(vectors)
	fielddata.append(wkb)
	values = " VALUES ("
	for _ in range(len(fielddata)):
		values += "?,"
	values = values[:-1] + ")"
	sql = "INSERT INTO " + tablename + values
	v = tuple(fielddata)
	# v = (None,wkb) + tuple(fielddata)
	cursor.execute(sql, v)
	return cursor.lastrowid

###############################################################################
def	addpolygonrecord(cursor, tablename, envelope, vectors, fielddata=[]):
	'''add a new POLYGON to the table'''
	# update the envelope
	envelope = calcenvelope(envelope, vectors)
	wkb = createpolygon(vectors)
	fielddata.append(wkb)
	values = " VALUES ("
	for _ in range(len(fielddata)):
		values += "?,"
	values = values[:-1] + ")"
	sql = "INSERT INTO " + tablename + values
	v = tuple(fielddata)

	cursor.execute(sql, v)
	return cursor.lastrowid

###############################################################################
def createpoint(vector, epsg=4326):
	'''create a point in well known binary'''
	'''https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary'''
	
	# GeoPackageBinaryHeader {
	# byte[2] magic = 0x4750; ①
	# byte version; ②
	# byte flags; ③
	# int32 srs_id;
	# double[] envelope; ④ #optional
	# }
	fmt 			= "<2sBBI"
	hdr 			= b"GP"					# magic identifier, always GP
	version 		= 0 					# always 0 which means version 1 of geopackage
	flags 			= 0
	flags 			= set_bit(flags,0)		# little endian byte order
	epsg 			= epsg

	# WKBPoint {
	# byte byteOrder;
	# static uint32 wkbType = 1;
	# Point point}

	# WKBMultiPoint            {
	# 	byte      byteOrder;
	# 	uint32    wkbType;                                     // 4
	# 	uint32    num_wkbPoints;
	# 	WKBPoint  WKBPoints[num_wkbPoints];
	# 	}

	# fmt 			+= "BII%sddd" # for xyZ representation	
	fmt 			+= "BIdd"
	geometry_type 	= 1						# geom type, 1 for points
	byteorder		= 0
	byteorder 		= set_bit(byteorder,0)		# little endian byte order
	# count 			= 1
	wkb = struct.pack(fmt, hdr, version, flags, epsg, byteorder, geometry_type, *vector)
	return wkb

###############################################################################
def createlinestring(vectors, epsg=4326):
	'''create a LINESTRING in well known binary'''
	'''https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary'''
	
	# GeoPackageBinaryHeader {
	# byte[2] magic = 0x4750; ①
	# byte version; ②
	# byte flags; ③
	# int32 srs_id;
	# double[] envelope; ④ #optional
	# }
	fmt 			= "<2sBBI"
	hdr 			= b"GP"					# magic identifier, always GP
	version 		= 0 					# always 0 which means version 1 of geopackage
	flags 			= 0
	flags 			= set_bit(flags,0)		# little endian byte order
	epsg 			= epsg

	# WKBLineString {
	# byte byteOrder;
	# static uint32 wkbType = 2;
	# uint32 numPoints;
	# Point points[numPoints]}

	fmt 			+= "BII%sd" % int(len(vectors))
	byteorder		= 0
	byteorder 		= set_bit(byteorder,0)		# little endian byte order
	geometry_type 	= 2						# geom type, 1 for points
	count 			= int(len(vectors)/2)

	wkb = struct.pack(fmt, hdr, version, flags, epsg,     byteorder, geometry_type, count, *vectors)
	return wkb

###############################################################################
def createpolygon(vectors, epsg=4326):
	'''create a POLYGON in well known binary'''
	'''numrings is the number of polygons in the vector list'''
	'''epsg is the spatial reference'''
	'''https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry#Well-known_binary'''
	
	# GeoPackageBinaryHeader {
	# byte[2] magic = 0x4750; ①
	# byte version; ②
	# byte flags; ③
	# int32 srs_id;
	# double[] envelope; ④ #optional
	# }
	fmt 			= "<2sBBI"
	hdr 			= b"GP"					# magic identifier, always GP
	version 		= 0 					# always 0 which means version 1 of geopackage
	flags 			= 0
	flags 			= set_bit(flags,0)		# little endian byte order
	epsg 			= epsg

	# WKBLineString {
	# byte byteOrder;
	# static uint32 wkbType = 3;
	# uint32 numPoints;
	# Point points[numPoints]}

	fmt 			+= "BIII%sd" % int(len(vectors))
	byteorder		= 0
	byteorder 		= set_bit(byteorder,0)		# little endian byte order
	geometry_type 	= 3						# geom type, 3 for a polygon
	count 			= int(len(vectors)/2)
	numrings 		= 1
	wkb = struct.pack(fmt, hdr, version, flags, epsg, byteorder, geometry_type, numrings, count, *vectors)
	return wkb

################################################################################ 
def calcenvelope(envelope, vectors):
	'''compute the envelope around a vector'''
	envelope[0] = min(envelope[0], min(vectors[0::2]))
	envelope[1] = max(envelope[1], max(vectors[0::2]))
	envelope[2] = min(envelope[2], min(vectors[1::2]))
	envelope[3] = max(envelope[3], max(vectors[1::2]))
	return envelope

################################################################################ 
def getSSDMFieldValue(fieldname):
	'''read through the SSDM.csv file and try to find a value for the requested field name.  This helps populate the SSDM tables'''
	localpath = os.path.dirname(os.path.realpath(__file__))
	sys.path.append(localpath)
	filename = os.path.join(localpath, "ssdmfieldvalue.txt")
	if os.path.isfile(filename):
		datafile = open(filename)
		for line in datafile:
			if line.startswith(str(fieldname)):
				return line.split(",")[1]
	return ""

################################################################################ 
def openSSDMFieldValues():
	'''open the SSDMfieldvalue.txt file so the user can make edits. This helps populate the SSDM tables with static values'''
	localpath = os.path.dirname(os.path.realpath(__file__))
	sys.path.append(localpath)
	filename = os.path.join(localpath, "ssdmfieldvalue.txt")
	if os.path.exists(filename):
		os.startfile(filename)
		# subprocess.call(('cmd', '/C', 'start', '', filename))		
		# subprocess.run(['open', filename], check=True)
###############################################################################
# bitwise helper functions
###############################################################################
def isBitSet(int_type, offset):
	'''testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.'''
	# mask = 1 << offset
	return (int_type & (1 << offset)) != 0

###############################################################################
def set_bit(value, bit):
 return value | (1<<bit)

###############################################################################
if __name__ == '__main__':
	main()
