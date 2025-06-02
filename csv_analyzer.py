# Author: JJ Kullberg
# Completed May 7, 2025
# Purpose: GEOG 498 term project, core classes

import pandas
from osgeo import ogr
from osgeo import osr
osr.UseExceptions()

class GeometryProcessor:
    """Abstract class that point, polyline, and polygon processors will be derived from"""
    def __init__(self, csv_file):
        self.csv_file = csv_file
        self.df = self.getDF()
        self.fields = self.df.columns
        self.fieldObjects = self.getFieldObjects()

    def getDF(self):
        """Create pandas dataframe from csv"""
        df = pandas.read_csv(self.csv_file)
        return df

    def getFieldObjects(self):
        """Pass list of column names to static function of class FieldObject"""
        objectList = FieldItem.fromColumnNames(self.fields)
        return objectList

    def createShapefile(self, wkid, output, fields):
        """Abstract method for creating shapefile, to be overridden"""
        pass

class FieldItem:
    """Object that represents a particular column of a dataframe, to be added as a shapefile field"""
    def __init__(self, name, formattedName):
        self.name = name
        self.formattedName = formattedName

    def fromColumnNames(names):
        """Static method that takes a list of field names and returns a list of FieldItem objects with unique
        formatted names"""
        nameCheck = set() # Empty set to check if a given field name has been looked at
        fieldItemList = [] # Empty list to store objects of class FieldObject

        # Get base name and add to nameCheck set. Check if basename already exists in set, and modify if so
        for name in names:
            shortName = name[:9].strip()
            formattedName = shortName

            counter = 1
            while formattedName in nameCheck:
                addition = str(counter)
                formattedName = shortName + addition
                counter += 1

            nameCheck.add(formattedName)
            # Create new FieldObject instance and add to list
            fieldItem = FieldItem(name, formattedName)
            fieldItemList.append(fieldItem)

        return fieldItemList

    def getOGRDataType(self, df):
        """Return data type for a field object that will be used in the creation of shapefile field"""
        # Check data type of column in the dataframe that the field name was obtained from
        df_data_type = df[self.name].dtype
        if df_data_type == 'object':
            return ogr.OFTString

        elif df_data_type == 'int64':
            return ogr.OFTInteger

        elif df_data_type == 'float64':
            return ogr.OFTReal

    def __eq__(self, other):
        """Objects are the same if they have the same name. This is to allow a list to check if a FieldObject is added
        twice"""
        return self.name == other.name

    def __str__(self):
        return self.name


class PointProcessor(GeometryProcessor):
    """Process a csv file containing point geometry and create a shapefile"""
    def __init__(self, csv_file):
        super(PointProcessor, self).__init__(csv_file)

    def addGeometry(self, latField, lonField):
        """Create point wkt point geometry for each set of lat/long coordinates in the rows"""
        try:
            wkt_list = []
            latIndex = self.fields.get_loc(latField)
            lonIndex = self.fields.get_loc(lonField)
            for row in self.df.itertuples(name=None, index=False):
                geom = f"POINT({row[lonIndex]} {row[latIndex]})"

                wkt_list.append(geom)

            self.df['geometry'] = wkt_list # Add the wkt geometries as a new df column
        except:
            pass

    # Override createShapefile method
    def createShapefile(self, wkid, output, fields):
        try:
            # Create empty shapefile
            drv = ogr.GetDriverByName('ESRI Shapefile')  # OGR shapefile driver
            sr = osr.SpatialReference()  # Create spatial reference object
            sr.ImportFromEPSG(int(wkid))  # Set spatial reference to input WKID
            outfile = drv.CreateDataSource(output)  # Create shapefile
            outlayer = outfile.CreateLayer('outlayer', geom_type=ogr.wkbPoint, srs=sr)  # Create layer, set geometry type
            # and spatial reference

            # Create field from each object found in input list of FieldObjects
            for fieldObject in fields:
                field = ogr.FieldDefn(fieldObject.formattedName, fieldObject.getOGRDataType(self.df))
                outlayer.CreateField(field)  # Add field to layer

            featureDefn = outlayer.GetLayerDefn()  # Get field definitions

            # Get index values for feature geometry
            geomIndex = self.df.columns.get_loc('geometry')

            # Loop through dataframe rows and add features
            for row in self.df.itertuples(name=None, index=False):
                geom = row[geomIndex]  # Get wkt point geometry
                outgeom = ogr.CreateGeometryFromWkt(geom)  # Create geometry object from wkt string
                outFeature = ogr.Feature(featureDefn)  # Create new feature
                outFeature.SetGeometry(outgeom)  # Add geometry to feature
                # Add values from dataframe for each field object
                for fieldObject in fields:
                    itemIndex = self.fields.get_loc(fieldObject.name)
                    outFeature.SetField(fieldObject.formattedName, row[itemIndex])

                outlayer.CreateFeature(outFeature)  # Create feature
                outFeature = None  # Close feature for next iteration

            outfile = None  # Close outfile
        except:
            pass

class PolylineProcessor(GeometryProcessor):
    """Process geometry and field attributes from a dataframe"""
    def __init__(self, csv_file):
        super(PolylineProcessor, self).__init__(csv_file)
        self.df = self.createNewDataframe()
        self.fields = self.df.columns
        self.fieldObjects = self.getFieldObjects()

    def createNewDataframe(self):
        """Reformat information in dataframe"""
        latIndex = self.df.columns.get_loc('latitude')
        lonIndex = self.df.columns.get_loc('longitude')
        elevationIndex = self.df.columns.get_loc('elevation')
        nameIndex = self.df.columns.get_loc('name')
        XYList = [] # Empty list to store nodes
        elevSum = 0 # Variable to sum elevations
        # New column names
        data = {'name': [], 'elevation': [], 'nodes': []}
        # Create a new df row with a list of nodes for all columns that contain the same name
        for row in self.df.itertuples(name=None, index=False):
            if row[nameIndex] not in data['name']:
                if data['name'] != []: # Check that we are not processing the first name
                    avgElev = elevSum / len(XYList) # Calculate average election
                    data['nodes'].append(','.join(XYList)) # Add nodes in the form of a string
                    data['elevation'].append(avgElev) # Add average elevation
                    XYList = [] # Reset XY list for next name
                    elevSum = 0 # Reset elevation variable for next name
                data['name'].append(row[nameIndex]) # Add new polyline name
                XYList.append(f"{row[latIndex]} {row[lonIndex]}") # Add first node to XY list
                elevSum += float(row[elevationIndex]) # Add first elevation value to elevation sum
            else:
                XYList.append(f"{row[latIndex]} {row[lonIndex]}") # Continue appending nodes to XY list
                elevSum += float(row[elevationIndex]) # Continue summing elevation

        # Add values for last data set
        avgElev = elevSum / len(XYList)
        data['nodes'].append(','.join(XYList))
        data['elevation'].append(avgElev)

        df = pandas.DataFrame(data)
        return df

    def addGeometry(self, nodeField):
        """Get wkt linestrings from node list"""
        try:
            wkt_list = []
            nodeIndex = self.fields.get_loc(nodeField)
            for row in self.df.itertuples(name=None, index=False):
                XYList = []
                # Get individual lat/long values from each node
                for node in row[nodeIndex].split(','):
                    lat = node.split(' ')[0]
                    lon = node.split(' ')[1]
                    XYList.append(f"{lon} {lat}")
                geom = f"LINESTRING ({','.join(XYList)})"  # Create WKT polyline string

                wkt_list.append(geom)

            self.df['geometry'] = wkt_list # Add geometry column with wkt linestrings to the dataframe

        except:
            pass
    def createShapefile(self, wkid, output, fields):
        """Process reformatted dataframe to add geometry and fields to a new shapefile"""
        # Create empty shapefile
        try:
            drv = ogr.GetDriverByName('ESRI Shapefile')  # OGR shapefile driver
            sr = osr.SpatialReference()  # Create spatial reference object
            sr.ImportFromEPSG(int(wkid))  # Set spatial reference to input WKID
            outfile = drv.CreateDataSource(output)  # Create shapefile
            outlayer = outfile.CreateLayer('outlayer', geom_type=ogr.wkbLineString, srs=sr)  # Create layer, set geometry
            # type and spatial reference

            # Create field from each object found in input list of FieldObjects
            for fieldObject in fields:
                field = ogr.FieldDefn(fieldObject.formattedName, fieldObject.getOGRDataType(self.df))
                outlayer.CreateField(field)  # Add field to layer

            featureDefn = outlayer.GetLayerDefn()  # Get field definitions

            # Get index values for feature geometry
            geomIndex = self.df.columns.get_loc('geometry')

            # Loop through dataframe rows and add features
            for row in self.df.itertuples(name=None, index=False):
                geom = row[geomIndex]  # Access wkt linestring for the given row
                outgeom = ogr.CreateGeometryFromWkt(geom)  # Create geometry object from linestring
                outFeature = ogr.Feature(featureDefn)  # Create new feature
                outFeature.SetGeometry(outgeom)  # Add geometry to feature
                # Add values from dataframe for each field object
                for fieldObject in fields:
                    itemIndex = self.df.columns.get_loc(fieldObject.name)
                    outFeature.SetField(fieldObject.formattedName, row[itemIndex])

                outlayer.CreateFeature(outFeature)  # Create feature
                outFeature = None  # Close feature for next iteration

            outfile = None  # Close outfile
        except:
            pass


class PolygonProcessor(GeometryProcessor):
    """Process geometry and field attributes from a dataframe"""
    def __init__(self, csv_file):
        super(PolygonProcessor, self).__init__(csv_file)
        self.df = self.createNewDataframe()
        self.fields = self.df.columns
        self.fieldObjects = self.getFieldObjects()

    def createNewDataframe(self):
        """Reformat information in dataframe"""
        latIndex = self.df.columns.get_loc('latitude')
        lonIndex = self.df.columns.get_loc('longitude')
        elevationIndex = self.df.columns.get_loc('elevation')
        nameIndex = self.df.columns.get_loc('name')
        XYList = [] # Empty list to store nodes
        elevSum = 0 # Variable to sum elevations
        data = {'name': [], 'elevation': [], 'nodes': []}
        # Create a new df row with a list of nodes for all columns that contain the same name
        for row in self.df.itertuples(name=None, index=False):
            if row[nameIndex] not in data['name']:
                if data['name'] != []: # Check that we are not processing the first name
                    avgElev = elevSum / len(XYList) # Calculate average election
                    XYList.append(XYList[0]) # Append first node to node list, to close polygon
                    data['nodes'].append(','.join(XYList))  # Add nodes to data in the form of a string
                    data['elevation'].append(avgElev) # Add average elevation to data
                    XYList = [] # Reset XY list for next name
                    elevSum = 0 # Reset elevation variable for next name
                data['name'].append(row[nameIndex]) # Add new polyline name
                XYList.append(f"{row[latIndex]} {row[lonIndex]}")  # Add first node to XY list
                elevSum += float(row[elevationIndex]) # Add first elevation value to elevation sum
            else:
                XYList.append(f"{row[latIndex]} {row[lonIndex]}") # Continue appending nodes to XY list
                elevSum += float(row[elevationIndex]) # Continue summing elevation

        # Add values for last data set
        avgElev = elevSum / len(XYList)
        XYList.append(XYList[0])
        data['nodes'].append(','.join(XYList))
        data['elevation'].append(avgElev)

        # Get first lat/long and append to end of list to ensure polygon is closed

        df = pandas.DataFrame(data)
        return df

    def addGeometry(self, nodeField):
         try:
            """Get wkt polygon strings from node list"""
            wkt_list = []
            nodeIndex = self.fields.get_loc(nodeField)
            for row in self.df.itertuples(name=None, index=False):
                XYList = []
                # Get individual lat/long values from each node
                for node in row[nodeIndex].split(','):
                    lat = node.split(' ')[0]
                    lon = node.split(' ')[1]
                    XYList.append(f"{lon} {lat}")
                geom = f"POLYGON (({','.join(XYList)}))" # Create WKT polygon string

                wkt_list.append(geom)

            self.df['geometry'] = wkt_list # Add geometry column with wkt strings to the dataframe
         except:
             pass

    def createShapefile(self, wkid, output, fields):
        try:
            """Process reformatted dataframe to add geometry and fields to a new shapefile"""
            # Create empty shapefile
            drv = ogr.GetDriverByName('ESRI Shapefile') # OGR shapefile driver
            sr = osr.SpatialReference() # Create spatial reference object
            sr.ImportFromEPSG(int(wkid)) # Set spatial reference to input WKID
            outfile = drv.CreateDataSource(output) # Create shapefile
            outlayer = outfile.CreateLayer('outlayer', geom_type=ogr.wkbPolygon, srs=sr) # Create layer, set geometry
            # type and spatial reference

            # Create field from each object found in input list of FieldObjects
            for fieldObject in fields:
                field = ogr.FieldDefn(fieldObject.formattedName, fieldObject.getOGRDataType(self.df))
                outlayer.CreateField(field) # Add field to layer

            featureDefn = outlayer.GetLayerDefn() # Get field definitions

            # Get index values for feature geometry
            geomIndex = self.df.columns.get_loc('geometry')

            # Loop through dataframe rows and add features
            for row in self.df.itertuples(name=None, index=False):
                geom = row[geomIndex] # Get LineString containing trip coordinates
                outgeom = ogr.CreateGeometryFromWkt(geom) # Create wkt geometry object from LineString
                outFeature = ogr.Feature(featureDefn) # Create new feature
                outFeature.SetGeometry(outgeom) # Add geometry to feature
                # Add values from dataframe for each field object
                for fieldObject in fields:
                    itemIndex = self.df.columns.get_loc(fieldObject.name)
                    outFeature.SetField(fieldObject.formattedName, row[itemIndex])

                outlayer.CreateFeature(outFeature) # Create feature
                outFeature = None # Close feature for next iteration

            outfile = None # Close outfile
        except:
            pass
