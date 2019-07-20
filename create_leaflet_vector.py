from __future__ import print_function
import os, sys
import json

from osgeo import ogr, osr
import shapefile
import folium

grid_sentinel = r"B:\PROJETO_IMG_DOWNLOAD\folium\sig\grid_pa_sentinel.shp"

def msg(s): print (s)
def dashes(): msg(40*'-')
def msgt(s): dashes(); msg(s); dashes()
def msgx(s): dashes(); msg('ERROR'); msg(s); dashes(); sys.exit(0)


def get_output_fname(fname, new_suffix):
    fparts = fname.split('.')
    if len(fparts[-1]) == 3:
        return '.'.join(fparts[:-1]) + new_suffix + '.' + fparts[-1]

    return fname + new_suffix

def reproject_to_4326(shape_fname):
    """Re-project the shapefile to a 4326. From the Python GDAL/OGR Cookbook

    Source: http://pcjericks.github.io/py-gdalogr-co...

    :param shape_fname: full file path to a shapefile (.shp)
    :returns: full file path to a shapefile reprojected as 4326
    """
    if not os.path.isfile(shape_fname):
        msgx('File not found: %s' % shape_fname)

    driver = ogr.GetDriverByName('ESRI Shapefile')
    inDataSet = driver.Open(shape_fname)

    # input SpatialReference
    inLayer = inDataSet.GetLayer()
    inSpatialRef = inLayer.GetSpatialRef()

    # output SpatialReference
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326)

    # create the CoordinateTransformation
    coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

    # create the output layer
    outputShapefile = get_output_fname(shape_fname, '_4326')
    #msg('output file: %s' % outputShapefile)

    if os.path.exists(outputShapefile):
        driver.DeleteDataSource(outputShapefile)
    outDataSet = driver.CreateDataSource(outputShapefile)
    outLayer = outDataSet.CreateLayer("basemap_4326", geom_type=ogr.wkbMultiPolygon)

    # add fields
    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        outLayer.CreateField(fieldDefn)

    # get the output layer's feature definition
    outLayerDefn = outLayer.GetLayerDefn()

    # loop through the input features
    inFeature = inLayer.GetNextFeature()
    while inFeature:
        # get the input geometry
        geom = inFeature.GetGeometryRef()
        # reproject the geometry
        geom.Transform(coordTrans)
        # create a new feature
        outFeature = ogr.Feature(outLayerDefn)
        # set the geometry and attribute
        outFeature.SetGeometry(geom)
        for i in range(0, outLayerDefn.GetFieldCount()):
            outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
        # add the feature to the shapefile
        outLayer.CreateFeature(outFeature)
        # destroy the features and get the next input feature
        outFeature.Destroy()
        inFeature.Destroy()
        inFeature = inLayer.GetNextFeature()

    # close the shapefiles
    inDataSet.Destroy()
    outDataSet.Destroy()


    msg('output file: %s' % outputShapefile)
    return outputShapefile

def convert_shp_to_geojson(shape_fname):
    """Using the pyshp library, https://github.com/GeospatialPython/pysh..., convert the shapefile to JSON

    Code is from this example:  http://geospatialpython.com/2013/07/shap...

    :param shape_fname: full file path to a shapefile (.shp)
    :returns: full file path to a GEOJSON representation of the shapefile

    (recheck/redo using gdal)
    """
    if not os.path.isfile(shape_fname):
        msgx('File not found: %s' % shape_fname)

    # Read the shapefile
    try: 
        reader = shapefile.Reader(shape_fname)
    except:
        msgx('Failed to read shapefile: %s' % shape_fname)

    fields = reader.fields[1:]
    field_names = [field[0] for field in fields]
    output_buffer = []
    for sr in reader.shapeRecords():
          atr = dict(zip(field_names, sr.record))
          geom = sr.shape.__geo_interface__
          output_buffer.append(dict(type="Feature", geometry=geom, properties=atr))

    # write the GeoJSON file
    out_fname = os.path.join(shape_fname.replace('.shp', '.json'))

    geojson = open(out_fname, "w")
    geojson.write(json.dumps({"type": "FeatureCollection","features": output_buffer}, indent=2))
    geojson.close()    
    msg('file written: %s' % out_fname)

    return out_fname

def style_function(feature):
    return {
        'fillColor': '#008000',
        'color': 'blue',
        'weight': 1.5,
        'dashArray': '0, 0'
    }

def highlight_function(feature):
    return {
        'fillColor': '#ffaf00',
        'color': 'green',
        'weight': 3,
        'dashArray': '5, 5'
    }

def make_leaflet_page(geojson_file, ouput_html_fname):
    """Using folium, make an HTML page using GEOJSON input 
        examples: https://github.com/wrobstory/folium

    :param geojson_file: full file path to a GEO JSON file
    :param ouput_html_fname: name of HTML file to create (will only use the basename)
    """
    if not os.path.isfile(geojson_file):
        msgx('File not found: %s' % geojson_file)

    # Boston 
    '''
    fg = folium.FeatureGroup(name="tiles")
    with open(geojson_file) as geojson:
        tileDic = json.load(geojson)

    for feature in tileDic['features']:
        coords = [[y,x] for i in feature['geometry']['coordinates'] for x,y in i ]
        tileId = feature['properties']['tile_id']
        print(coords)
        print(tileId)
        fg.add_child(folium.Polygon(locations=coords,fill=True,popup=(folium.Popup(tileId))))
    '''
    m = folium.Map(location=[ -4.861101, -52.591553],tiles='Stamen Toner',)
    geojson = folium.GeoJson(geojson_file,style_function=style_function,highlight_function=highlight_function)
    #m.add_child(fg)
    #
    folium.GeoJsonTooltip(fields=['tile_id']).add_to(geojson)

    geojson.add_to(m)
    m.add_child(folium.LayerControl())
    ouput_html_fname = os.path.basename(ouput_html_fname)
    m.save(ouput_html_fname)
    print ('file written', ouput_html_fname)


if __name__=='__main__':
    #reprojected_fname = reproject_to_4326('data/social_disorder_in_boston/social_disorder_in_boston_yqh.shp')
    geojson_fname = convert_shp_to_geojson(grid_sentinel)
    make_leaflet_page(geojson_fname, 'grid_pa_sentinel.html')


'''
    function onMapClick(e) {
    alert("You clicked the map at " + e.latlng);
}
map_81cdf183ae614f0c836f9422924987e9.on('click', onMapClick);
'''