#name:			SSDM_Geopackage.py
#created:		Jan 2019
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module defining an SSDM V2.0 schema using native python.  this module works hand in hand with the geopackage.py module to enable the creation of a geopackage containing an implementaiton of SSDM
#description:	An open source implementation the SSDM schema using the OGC geopackage file format unlocks SSDM from the existing restraints that SSDM ONLY works inside ESRI ArcGIS which has license restrictions.

import sys
import geopackage
import geodetic


###############################################################################
def main():
	'''test the creation of a geopackage using basic python without complex module installs '''

	filename = "C:/temp/geopackage.gpkg"
	con = geopackage.creategeopackage(filename)

	geopackage.addsrsrecord(con, "pkpk", 32650)

	geopackage.createpoints(con)
	geopackage.createlinestrings(con)
	geopackage.createpolygons(con)


###############################################################################
def	ssdmarchive():
	'''helper function to create SSDMArchive fields'''
	fields 		= []
	#checked - ok 12/4/2021
	fields.append(["LAST_UPDATE", 		"DATETIME"]) #Date the dataset was last edited
	fields.append(["LAST_UPDATE_BY", 	"TEXT(150)"]) #Editor's name
	return fields

###############################################################################
def	ssdmobject():
	'''helper function to create SSDMObject fields'''
	fields 		= []
	#checked - ok 12/4/2021
	fields.append(["OBJECTID", 		"INTEGER PRIMARY KEY AUTOINCREMENT"]) #OBJECTID needed for ESRI and for QGIS editing  #THISIS NOT PART OF STANDARD SSDM.  Maybe needs a diferent implementation?
	# fields.append(["FEATURE_ID", 		"INTEGER PRIMARY KEY AUTOINCREMENT"]) #GUID Data Type #16 byte see: desktop.arcgis.com/en/arcmap/10.3/manage-data/geodatabases/arcgis-field-data-types.htm#GUID-97064FAE-B42E-4DC3-A5C9-9A6F12D053A8 
	fields.append(["FEATURE_ID", 		"TEXT(38) NOT NULL"]) ##GUID## Data Type #16 byte see: desktop.arcgis.com/en/arcmap/10.3/manage-data/geodatabases/arcgis-field-data-types.htm#GUID-97064FAE-B42E-4DC3-A5C9-9A6F12D053A8 
	fields.append(["SURVEY_ID", 		"SMALLINT"]) #Numeric Survey Job Reference Number #4 byte integer
	fields.append(["SURVEY_ID_REF", 	"TEXT(255)"]) #AlphaNumeric Survey Job Reference Number
	fields.append(["REMARKS", 			"TEXT(255)"]) #Feature Comments
	return fields

###############################################################################
def	ssdmfeature():
	'''helper function to create SSDMfeature fields'''
	fields 		= []
	#checked - ok 14/8/2019
	fields.append(["LAYER", 					"TEXT(255)"]) #CAD Layer
	fields.append(["FEATURE_NAME", 				"TEXT(100)"]) #Seabed Feature name
	fields.append(["FEATURE_DESC", 				"TEXT(255)"]) #Seabed Feature Description
	fields.append(["DATA_SOURCE", 				"TEXT(255)"]) #Feature Data Source - refer to domain list for code
	fields.append(["INTERPRETATION_SOURCE", 	"TEXT(255)"]) #Feature Interpretation Source – refer to domain list for code
	return fields

###############################################################################
def	ssdmsurveyobject():
	'''helper function to create SSDMSurveyObject fields'''
	fields 		= []
	#checked - ok 14/8/2019
	fields.append(["SURVEY_NAME", 				"TEXT(255)"]) #Survey Project / Campaign Name
	return fields

###############################################################################
def	ssdmenvobject():
	'''helper function to create SSDMEnvObject fields'''
	fields 		= []
	#checked - ok 12/4/2021
	fields.append(["SAMPLE_NAME", 		"TEXT(50)"]) #Sample Name
	fields.append(["SAMPLE_DESC", 		"TEXT(100)"]) #Sample Description
	fields.append(["SAMPLING_METHOD", 	"TEXT(50)"]) #Sampling Method Classification -refer to domain list for code GEO_SAMPLE_METHOD
	fields.append(["SAMPLING_DATE", 	"DATETIME"]) #Sample Acquisition Date
	fields.append(["DATA_URL", 			"TEXT(255)"]) #Data Hyperlink URL
	fields.append(["REPORT_URL", 		"TEXT(255)"]) #Report Hyperlink URL
	return fields

###############################################################################
def	ssdmgeohazardobject():
	'''helper function to create SSDMGeohazardObject fields'''
	#checked - ok 12/4/2021
	fields 		= []
	fields.append(["REFLECTOR_NUMBER", 		"TEXT(20)"]) #Shallow Geologic Zone Reflector Number – refer to domain list for code REFLECTOR_NUMBER
	fields.append(["GEOLOGIC_UNIT", 		"TEXT(20)"]) #Shallow Geologic Zone Unit – refer to domain list for code
	fields.append(["HORIZON", 				"TEXT(30)"]) #Shallow Geologic Zone Horizon Number – refer to domain list for code GEOLOGIC_HORIZON
	return fields

###############################################################################
def	ssdmgeoseabedobject():
	'''helper function to create SSDMSeabedObject fields'''
	#checked - ok 12/4/2021
	fields 		= []
	fields.append(["SURVEY_DATE", 			"DATETIME"]) 	#Survey End Date
	fields.append(["HEIGHT", 				"DOUBLE"]) 		#Feature Height off Seabed – store UoM in UnitOfMeasure table
	fields.append(["HEIGHT_DESCRIPTION", 	"TEXT(50)"]) 	#Feature Height Label (i.e. “2.7m”)
	fields.append(["DEPTH", 				"DOUBLE"]) 		#Feature Water Depth – store UoM in UnitOfMeasure table
	fields.append(["DIMENSION_DESCRIPTION", "TEXT(20)"]) 	#Feature Dimension Label (i.e. “4.4m x 1.85m”)
	return fields

###############################################################################
def	ssdmsurveydetails():
	'''helper function to create SSDMSurveyDetails fields'''
	#checked - ok 12/4/2021
	fields 		= []
	fields.append(["SURVEY_AREA_NAME", 	"TEXT(50)"]) 	#Survey Area Name (i.e. Field Name or Survey Area Designated by Project Scope)
	fields.append(["SURVEY_TYPE", 				"TEXT(250"]) 		#Survey Purpose / Type (i.e. Seabed Reconnaissance Survey) – refer to domain list for code SYMBOL_POLYGON_SURVEY_TYPE
	fields.append(["WORK_CATEGORY", "TEXT(5)"]) 	#Survey Work Category (i.e. Geophysical Survey) – refer to domain list for code WORK_CATEGORY
	fields.append(["SURVEY_START_DATE", 			"DATETIME"]) 	#Survey Start Date
	fields.append(["SURVEY_END_DATE", 			"DATETIME"]) 	#Survey End Date
	fields.append(["REPORT_REF_NO", 				"TEXT(50"]) 		#Survey Report Document Number
	fields.append(["REPORT_URL", 				"TEXT(255"]) 		#Survey Report Document Hyperlink URL
	fields.append(["CLIENT_NAME", 				"TEXT(50"]) 		#Client for whom Survey was Executed – refer to domain list for code
	fields.append(["COUNTRY_NAME", 				"TEXT(50"]) 		#Country in which Survey was Executed – refer to domain list for code
	fields.append(["SYMBOLOGY_CODE", 				"TEXT(20"]) 		#Survey Purpose / Type (i.e. Seabed Reconnaissance Survey) – refer to domain list for code

	return fields

###############################################################################
##############################################################################
# def	createTSdip_Sample_Pnt():
# # def	createTSdip_Sample_Pnt(connection, tablename="TSdip_Sample_Pnt", epsg=4326):
# 	'''helper function to create SSDM table for mission plan'''
# 	type 		= "POINT"		# the point type.  POINT, LINESTRING, POLYGON etc as per OGC types

# 	# the SSDM fields for FC: "TSdip_Sample_Pnt
# 	fields 		= []
# 	fields += ssdmarchive()
# 	fields += ssdmobject()
# 	fields += ssdmenvobject()

# 	#checked - ok 14/8/2019
# 	fields.append(["SURVEY_DATE", 		"DATETIME"])
# 	fields.append(["PROJECT_NAME", 		"TEXT(250)"])
# 	fields.append(["FROM_TIME", 		"TEXT(10)"])
# 	fields.append(["TO_TIME", 			"TEXT(10)"])
# 	fields.append(["INSTRUMENT_USED", 	"TEXT(50)"])
# 	fields.append(["TEMPERATURE",		"DOUBLE"])
# 	fields.append(["SALINITY", 			"DOUBLE"])
# 	fields.append(["PRESSURE", 			"DOUBLE"])
# 	fields.append(["VELOCITY", 			"DOUBLE"])
# 	fields.append(["CONDUCTIVITY", 		"DOUBLE"])
# 	fields.append(["DENSITY", 			"DOUBLE"])
# 	fields.append(["DEPTH", 			"DOUBLE"])
# 	fields.append(["LOCALITY", 			"TEXT(100)"])
# 	fields.append(["SYMBOLOGY_CODE", 	"TEXT(20)"])
# 	# fields.append(["X", 			"DOUBLE"])
# 	# fields.append(["Y", 			"DOUBLE"])

# 	return type, fields

	##############################################################################
def	createProposed_Survey_Run_Lines():
# def	createProposed_Survey_Run_Lines(connection, tablename="LINESTRING", epsg=4326):
	'''helper function to create SSDM table for mission plan'''
	type 		= "LINESTRING"		# the point type.  POINT, LINESTRING, POLYGON etc as per OGC types

	# the SSDM fields for FC: "Proposed_Survey_Run_Lines"
	fields 		= []
	fields += ssdmarchive()
	fields += ssdmobject()

	#checked - ok 14/8/2019
	fields.append(["SURVEY_NAME", 		"TEXT(255)"])
	fields.append(["LINE_PREFIX", 		"TEXT(20)"])
	fields.append(["LINE_NAME", 		"TEXT(20)"])
	fields.append(["LINE_DIRECTION", 	"DOUBLE"])
	fields.append(["SYMBOLOGY_CODE", 	"TEXT(20)"])

	fields.append(["PROJECT_NAME", 		"TEXT(250)"])
	fields.append(["SURVEY_BLOCK_NAME", "TEXT(50)"])
	fields.append(["PREPARED_BY", 		"TEXT(50)"])
	fields.append(["PREPARED_DATE", 	"DATETIME"])
	fields.append(["APPROVED_BY", 		"TEXT(50)"])

	fields.append(["APPROVED_DATE", 	"DATETIME"])
	fields.append(["LAYER", 			"TEXT(255)"])
	fields.append(["SHAPE_Length", 		"DOUBLE"])

	return type, fields
	# table = vectortable (connection, tablename, epsg, type, fields)
	# return table

# ##############################################################################
# def createUTPtable():
# # def createUTPtable(connection, tablename="UTP", type="POINT", epsg=4326):
# 	'''helper function to create table for UTP QC'''
# 	# type 		= "POINT"		# the point type.  POINT, LINESTRING, POLYGON etc as per OGC types
	
# 	fields 		= []
# 	fields.append(["tpID", 					"DOUBLE"])
# 	fields.append(["SurveyDate",			"DOUBLE"])
# 	fields.append(["SurveyTime", 			"TEXT"])
# 	fields.append(["UNIXTime", 				"DOUBLE"])
# 	fields.append(["Latitude", 				"DOUBLE"])
# 	fields.append(["Longitude", 			"DOUBLE"])
# 	fields.append(["tpLatitude", 			"DOUBLE"])
# 	fields.append(["tpLongitude", 			"DOUBLE"])
# 	fields.append(["tpDepth", 				"DOUBLE"])
# 	fields.append(["range_m", 				"DOUBLE"])
# 	fields.append(["rangeStd", 				"DOUBLE"])
# 	fields.append(["soundSpeed", 			"DOUBLE"])
# 	fields.append(["cminuso", 				"DOUBLE"])
# 	fields.append(["acceptancethreshold", 	"DOUBLE"])

# 	return type, fields
# 	# table = vectortable (connection, tablename, epsg, type, fields)
# 	# return table

# ###############################################################################
# def createPointSSDMGv2():
# # def createPointSSDMGv2(connection, tablename="pointSSDMGv2", epsg=4326):
# 	'''helper function to create table for navlab, strapdown and Hipap processing which use point v2 format'''
# 	type 		= "POINT"		# the point type.  POINT, LINESTRING, POLYGON etc as per OGC types
	
# 	fields 		= []
# 	fields += ssdmarchive()
# 	fields += ssdmobject()

# 	fields.append(["LINE_ID", 				"SMALLINT"])
# 	fields.append(["LINE_NAME", 			"TEXT(40)"])
# 	fields.append(["LAST_SEIS_PT_ID", 		"SMALLINT"])
# 	fields.append(["SYMBOLOGY_CODE", 		"TEXT(10)"])
# 	fields.append(["DATA_SOURCE", 			"TEXT(150)"])		#, size=150) 	#SSDMSurvey_TrackLines class
	
# 	fields.append(["CONTRACTOR_NAME", 		"TEXT"])			#, size=20)	#SSDMSurvey_TrackLines class
# 	fields.append(["LINE_LENGTH", 			"DOUBLE"]) 			#SSDMSurvey_TrackLines class
# 	fields.append(["FIRST_SEIS_PT_ID", 		"DOUBLE"])			#SSDMSurvey_TrackLines class
# 	fields.append(["HIRES_SEISMIC_EQL_URL",	"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
# 	fields.append(["OTHER_DATA_URL", 		"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
	
# 	fields.append(["LAYER", 				"TEXT(255)"])		#, size=255)	#SSDMSurvey_TrackLines class
# 	fields.append(["SHAPE_Length", 			"DOUBLE"])			#SSDMSurvey_TrackLines class
# 	fields.append(["SurveyTime", 			"TEXT"])
# 	fields.append(["UNIXTime", 				"DOUBLE"])
# 	fields.append(["Longitude", 			"DOUBLE"])
	
# 	fields.append(["Latitude", 				"DOUBLE"])
# 	fields.append(["Depth", 				"DOUBLE"])
# 	fields.append(["Roll", 					"DOUBLE"])
# 	fields.append(["Pitch", 				"DOUBLE"])
# 	fields.append(["Heading", 				"DOUBLE"])
	
# 	fields.append(["stdDevPos", 			"DOUBLE"])
# 	fields.append(["stdDevDep", 			"DOUBLE"])
# 	fields.append(["usblage", 				"DOUBLE"])
# 	fields.append(["utpage", 				"DOUBLE"])
# 	fields.append(["thuthreshold", 			"DOUBLE"])
	
# 	fields.append(["tvuthreshold", 			"DOUBLE"])
# 	fields.append(["thuaccepted", 			"DOUBLE",]) 		#boolean to represnet if horizontal position accuracy exceeds cleint requirement
# 	fields.append(["tvuaccepted", 			"DOUBLE"]) 			#boolean to represnet if horizontal position accuracy exceeds cleint requirement

# 	return type, fields

# 	# table = vectortable (connection, tablename, epsg, type, fields)
# 	# return table

###############################################################################
def createSurveyTracklineSSDM():
# def createSurveyTracklineSSDMG(connection, tablename="SurveyTrackLine", epsg=4326):

	'''helper function to create table compliant with the SSDM schema typically called SurveyTrackLine'''
	type 		= 'LINESTRING'
	fields 		= []
	fields += ssdmarchive()
	fields += ssdmobject()

	fields.append(["LINE_ID", 				"SMALLINT"])
	fields.append(["LINE_NAME", 			"TEXT(40)"])
	fields.append(["LAST_SEIS_PT_ID", 		"SMALLINT"])
	fields.append(["SYMBOLOGY_CODE", 		"TEXT(10)"])
	fields.append(["DATA_SOURCE", 			"TEXT(150)"])		#, size=150) 	#SSDMSurvey_TrackLines class
	
	fields.append(["CONTRACTOR_NAME", 		"TEXT"])			#, size=20)	#SSDMSurvey_TrackLines class
	fields.append(["LINE_LENGTH", 			"DOUBLE"]) 			#SSDMSurvey_TrackLines class
	fields.append(["FIRST_SEIS_PT_ID", 		"DOUBLE"])			#SSDMSurvey_TrackLines class
	fields.append(["HIRES_SEISMIC_EQL_URL",	"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
	fields.append(["OTHER_DATA_URL", 		"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
	fields.append(["HIRES_SEISMIC_RAP_URL", "TEXT(255)"])		#, size=255)	#SSDMSurvey_TrackLines class
	
	fields.append(["LAYER", 				"TEXT(255)"])		#, size=255)	#SSDMSurvey_TrackLines class
	fields.append(["SHAPE_Length", 			"DOUBLE"])			#SSDMSurvey_TrackLines class

#extra
	# fields.append(["SurveyTime", 			"TEXT"])
	# fields.append(["UNIXTime", 				"DOUBLE"])
	# fields.append(["Longitude", 			"DOUBLE"])
	
	# fields.append(["Latitude", 				"DOUBLE"])

	# fields.append(["LINE_ID", 					"DOUBLE"])			#SSDMSurvey_TrackLinesclass
	# fields.append(["LINE_NAME", 				"TEXT(40)"])		#, size=40)	#SSDMSurvey_TrackLines class
	# fields.append(["LAST_SEIS_PT_ID", 			"DOUBLE"]) 			#SSDMSurvey_TrackLines class
	# fields.append(["DATA_SOURCE", 				"TEXT(150)"])		#, size=150) 	#SSDMSurvey_TrackLines class
	# fields.append(["CONTRACTOR_NAME", 			"TEXT(20)"])		#, size=20)	#SSDMSurvey_TrackLines class
	# fields.append(["LINE_LENGTH", 				"DOUBLE"])			#, decimal=8) #SSDMSurvey_TrackLines class
	# fields.append(["FIRST_SEIS_PT_ID", 			"DOUBLE"])			#SSDMSurvey_TrackLines class
	# fields.append(["HIRES_SEISMIC_EQL_URL", 	"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
	# fields.append(["OTHER_DATA_URL", 			"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
	# fields.append(["LAYER", 					"TEXT(255)"])		#, size=255)	#SSDMSurvey_TrackLines class
	# fields.append(["SHAPE_Length", 				"DOUBLE"])			#, decimal=8)	#SSDMSurvey_TrackLines class

	return type, fields

	# table = vectortable (connection, tablename, epsg, type, fields)
	# return table

# ###############################################################################
# def createTrackPoint():
# # def createPointSSDMGv2(connection, tablename="pointSSDMGv2", epsg=4326):
# 	'''helper function to create table for navlab, strapdown and Hipap processing which use point v2 format'''
# 	type 		= "POINT"		# the point type.  POINT, LINESTRING, POLYGON etc as per OGC types
	
# 	fields 		= []
# 	fields += ssdmarchive()
# 	fields += ssdmobject()

# 	fields.append(["LINE_ID", 				"SMALLINT"])
# 	fields.append(["LINE_NAME", 			"TEXT(40)"])
# 	fields.append(["LAST_SEIS_PT_ID", 		"SMALLINT"])
# 	fields.append(["SYMBOLOGY_CODE", 		"TEXT(10)"])
# 	fields.append(["DATA_SOURCE", 			"TEXT(150)"])		#, size=150) 	#SSDMSurvey_TrackLines class
	
# 	fields.append(["CONTRACTOR_NAME", 		"TEXT"])			#, size=20)	#SSDMSurvey_TrackLines class
# 	fields.append(["LINE_LENGTH", 			"DOUBLE"]) 			#SSDMSurvey_TrackLines class
# 	fields.append(["FIRST_SEIS_PT_ID", 		"DOUBLE"])			#SSDMSurvey_TrackLines class
# 	fields.append(["HIRES_SEISMIC_EQL_URL",	"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
# 	fields.append(["OTHER_DATA_URL", 		"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
	
# 	fields.append(["LAYER", 				"TEXT(255)"])		#, size=255)	#SSDMSurvey_TrackLines class
# 	fields.append(["SHAPE_Length", 			"DOUBLE"])			#SSDMSurvey_TrackLines class
# 	fields.append(["SurveyTime", 			"TEXT"])
# 	fields.append(["UNIXTime", 				"DOUBLE"])
# 	fields.append(["Longitude", 			"DOUBLE"])
	
# 	fields.append(["Latitude", 				"DOUBLE"])
# 	fields.append(["Depth", 				"DOUBLE"])
# 	fields.append(["Roll", 					"DOUBLE"])
# 	fields.append(["Pitch", 				"DOUBLE"])
# 	fields.append(["Heading", 				"DOUBLE"])
	
# 	return type, fields

# 	# table = vectortable (connection, tablename, epsg, type, fields)
# 	# return table

# ###############################################################################
# def createCoverageSSDMG():
# # def createCoverageSSDMG(connection, tablename="SurveyCoverage", epsg=4326):

# 	'''helper function to create table compliant with the SSDM schema typically called SurveyTrackLine'''
# 	'''helper function to create table for navlab, strapdown and Hipap processing which use point v2 format'''
# 	type 		= 'POLYGON'
# 	fields 		= []
# 	fields += ssdmarchive()
# 	fields += ssdmobject()

# 	fields.append(["LINE_ID", 					"DOUBLE"])			#SSDMSurveyObject class
# 	fields.append(["LINE_NAME", 				"TEXT(40)"])		#, size=40)	#SSDMSurvey_TrackLines class
# 	fields.append(["LAST_SEIS_PT_ID", 			"DOUBLE"]) 			#SSDMSurvey_TrackLines class
# 	fields.append(["DATA_SOURCE", 				"TEXT(150)"])		#, size=150) 	#SSDMSurvey_TrackLines class
# 	fields.append(["CONTRACTOR_NAME", 			"TEXT(20)"])		#, size=20)	#SSDMSurvey_TrackLines class
# 	fields.append(["LINE_LENGTH", 				"DOUBLE"])			#, decimal=8) #SSDMSurvey_TrackLines class
# 	fields.append(["FIRST_SEIS_PT_ID", 			"DOUBLE"])			#SSDMSurvey_TrackLines class
# 	fields.append(["HIRES_SEISMIC_EQL_URL", 	"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
# 	fields.append(["OTHER_DATA_URL", 			"TEXT(254)"])		#, size=254)	#SSDMSurvey_TrackLines class
# 	fields.append(["LAYER", 					"TEXT(255)"])		#, size=255)	#SSDMSurvey_TrackLines class
# 	fields.append(["SHAPE_Length", 				"DOUBLE"])			#, decimal=8)	#SSDMSurvey_TrackLines class

# 	return type, fields

# 	# table = vectortable (connection, tablename, epsg, type, fields)
# 	# return table

###############################################################################
if __name__ == '__main__':
	main()
