from __future__ import print_function
import os, sys
import json
from subprocess import call
from osgeo import ogr, osr
import shapefile
import folium
from bs4 import BeautifulSoup as Soup
from bs4 import Tag
import re


def msg(s): print (s)
def dashes(): msg(40*'-')
def msgt(s): dashes(); msg(s); dashes()
def msgx(s): dashes(); msg('ERROR'); msg(s); dashes(); sys.exit(0)

def get_layers_from_search(conn,ar_cad,uf,sat):
    uf[0] = uf[0].upper()
    satLay = conn.GetLayer('monitoramento_kfw.grid_sat')
    brLay = conn.GetLayer('monitoramento_kfw.br_estados_ibge_2015')
    if ar_cad[0] == '1':
        get_arcad(uf[0])
    brLay.SetAttributeFilter("uf = '{}'".format(uf[0].upper()))
    n=0
    multi = ogr.Geometry(ogr.wkbMultiPolygon)
    for feat in brLay:
        multi = multi.Union(feat.geometry())
        n+=1
    long = multi.Centroid().GetX()
    lat = multi.Centroid().GetY()
    loc = [long,lat]
    satLay.SetAttributeFilter("sat = '{}'".format(sat[0].upper()))
    satLay.SetSpatialFilter(multi)
    return satLay,multi,loc

def create_grid_sat_shp(shp_folder,satLay,multi):
    output = os.path.join(shp_folder,'sat.shp')
    if os.path.isfile(output):
        call('rm {}'.format(output),shell=True)
    drv = ogr.GetDriverByName("ESRI Shapefile")
    out_ds = drv.CreateDataSource(output)
    out_lyr = out_ds.CreateLayer(output, satLay.GetSpatialRef(),satLay.GetGeomType())
    d_2017 = ogr.FieldDefn("d_2017", ogr.OFTString)
    d_2017.SetWidth(250)
    out_lyr.CreateField(d_2017)

    d_2018 = ogr.FieldDefn("d_2018", ogr.OFTString)
    d_2018.SetWidth(250)
    out_lyr.CreateField(d_2018)

    d_2019 = ogr.FieldDefn("d_2019", ogr.OFTString)
    d_2019.SetWidth(250)
    out_lyr.CreateField(d_2019)

    tId = ogr.FieldDefn("tile_id", ogr.OFTString)
    tId.SetWidth(50)
    out_lyr.CreateField(tId)
    defn = out_lyr.GetLayerDefn()

    n=0
    for feat in satLay:
        geom = feat.geometry()
        if geom.Intersects(multi):
            tileId = feat.GetField('tile_id')
            d17 = feat.GetField('d_2017')
            d18 = feat.GetField('d_2018')
            d19 = feat.GetField('d_2019')
            out_feat = ogr.Feature(defn)
            out_feat.SetGeometry(geom)
            out_feat.SetField('d_2017', d17)
            out_feat.SetField('d_2018', d18)
            out_feat.SetField('d_2019', d19)
            out_feat.SetField('tile_id', tileId)
            out_lyr.CreateFeature(out_feat)
            out_feat = None
            n+=1
    out_lyr = None
    out_ds = None

def get_arcad(uf,shp_folder):
    drv = ogr.GetDriverByName("ESRI Shapefile")
    uf = uf.upper()
    arcadLay = conn.GetLayer('monitoramento_kfw.area_cadastravel')
    arcadLay.SetAttributeFilter("cod_estado = '{}'".format(uf))
    #multi = ogr.Geometry(ogr.wkbMultiPolygon)
    #for feat in arcadLay:
    #	multi = multi.Union(feat.geometry())
    output = os.path.join(shp_folder,'arcad.shp')
    if os.path.isfile(output):
        call('rm {}'.format(output),shell=True)
    out_ds = drv.CreateDataSource(output)
    out_lyr = out_ds.CreateLayer(output, arcadLay.GetSpatialRef(),arcadLay.GetGeomType())
    defn = out_lyr.GetLayerDefn()
    for feat in arcadLay:
        geom = feat.geometry()
        out_feat = ogr.Feature(defn)
        out_feat.SetGeometry(geom)
        out_lyr.CreateFeature(out_feat)
        out_feat = None
    out_lyr = None
    out_ds = None


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
          #print(atr)

    # write the GeoJSON file
    out_fname = os.path.join(shape_fname.replace('.shp', '.json'))
    if os.path.isfile(out_fname):
        call('rm {}'.format(out_fname),shell=True)

    geojson = open(out_fname, "w")
    geojson.write(json.dumps({"type": "FeatureCollection","features": output_buffer}, indent=2))
    geojson.close()
    msg('file written: %s' % out_fname)

    return out_fname

def style_function(feature):
    if feature['properties']['d_2017'] == '' and feature['properties']['d_2018'] == '' and feature['properties']['d_2019'] == '':
        style = {
            'fillColor': '#ff0000',
            'color': 'blue',
            'weight': 1.5,
            'dashArray': '0, 0'
        }

    elif feature['properties']['d_2017'] != '' and feature['properties']['d_2018'] != '' and feature['properties']['d_2019'] != '':
        style = {
            'fillColor': '#008000',
            'color': 'blue',
            'weight': 1.5,
            'dashArray': '0, 0'
        }

    elif feature['properties']['d_2017'] != '' or feature['properties']['d_2018'] != '' or feature['properties']['d_2019'] != '':
        style = {
            'fillColor': '#ecff00',
            'color': 'blue',
            'weight': 1.5,
            'dashArray': '0, 0'
        }

    return style

def style_function_arcad(feature):
    return {
            'fillColor': '#000000',
            'color': '#000000',
            'weight': 0.05,
            'dashArray': '0, 0'
        }

def highlight_function(feature):

    high = {'fillColor': '#ffaf00',
        'color': 'green',
        'weight': 3,
        'dashArray': '5, 5'}
    return high

def make_leaflet_page(geojson_grid,geojson_arcad, output_html_path,loc):
    """Using folium, make an HTML page using GEOJSON input
        examples: https://github.com/wrobstory/folium

    :param geojson_grid: full file path to a GEO JSON file
    :param output_html_fname: name of HTML file to create (will only use the basename)
    """
    if not os.path.isfile(geojson_grid):
        msgx('File not found: %s' % geojson_grid)

    # Boston
    '''
    fg = folium.FeatureGroup(name="tiles")
    with open(geojson_grid) as geojson:
        tileDic = json.load(geojson)

    for feature in tileDic['features']:
        coords = [[y,x] for i in feature['geometry']['coordinates'] for x,y in i ]
        tileId = feature['properties']['tile_id']
        print(coords)
        print(tileId)
        fg.add_child(folium.Polygon(locations=coords,fill=True,popup=(folium.Popup(tileId))))
    '''

    m = folium.Map(location=[ loc[1], loc[0]],height='70%',tiles='Stamen Toner',zoom_start=6)
    if not geojson_arcad == None:
        geojson = folium.GeoJson(geojson_arcad,style_function=style_function_arcad,name='area cadastravel')
        geojson.add_to(m)
    geojson = folium.GeoJson(geojson_grid,style_function=style_function,highlight_function=highlight_function,name='grid sattelite')
    #m.add_child(fg)
    #
    folium.GeoJsonTooltip(fields=['tile_id','d_2017','d_2018','d_2019']).add_to(geojson)

    geojson.add_to(m)



    m.add_child(folium.LayerControl())

    output_html_fname = os.path.basename(output_html_path)
    if os.path.isfile(output_html_path):
        call('rm {}'.format(output_html_path),shell=True)
    m.save(output_html_path)
    print ('file written', output_html_fname)

    with open(output_html_path) as html:
        soup = Soup(html, 'html.parser')
    map_number = soup.find_all("div", {"class": "folium-map"})
    map_number = map_number[0].get('id')

    tag = soup.body

    new_tag = soup.new_tag('h1', **{'style':"font-weight: bold;font-size: 42px;"})
    new_tag.string = "Sattelite preview selection Tool"
    tag.insert(1,new_tag)

    new_tag = soup.new_tag('form',action="/download_tile", method="get")
    tag.insert(2,new_tag)
    tag_form = soup.form

    new_tag = soup.new_tag('div', **{'class':'field','style':'font-weight: bold;font-size: 13px;'})
    new_tag.string = "Tile ID:"
    tag_form.insert(1,new_tag)
    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'tile_id','id':'tile_id','size':'25','type':'text'})
    #new_tag = soup.new_tag('input', name="tileId",  size="250", **{'type':'text'})
    tag_form.insert(2,new_tag)



    new_tag = soup.new_tag('input', value="Search", **{'type':'submit','style':"float: right;height:185px;width:300px;font-size: 80px;font-weight: bold;"})
    tag_form.insert(3,new_tag)

    new_tag = soup.new_tag('div', **{'class':'field','style':'font-weight: bold;font-size: 13px;'})
    new_tag.string = "Fixed Date:"
    tag_form.insert(4,new_tag)

    new_tag = soup.new_tag('div1')

    tag_form.insert(5,new_tag)
    tag_div1 = soup.div1
    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'f_date','id':'2017','value':'2017','type':'radio'})
    #new_tag = soup.new_tag('input', name="tileId",  size="250", **{'type':'text'})
    tag_div1.insert(1,new_tag)
    new_tag = soup.new_tag('label', **{'for':'2017'})
    new_tag.string = '2016'
    tag_div1.insert(2,new_tag)

    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'f_date','id':'2018','value':'2018','type':'radio'})
    #new_tag = soup.new_tag('input', name="tileId",  size="250", **{'type':'text'})
    tag_div1.insert(3,new_tag)
    new_tag = soup.new_tag('label', **{'for':'2018'})
    new_tag.string = '2018'
    tag_div1.insert(4,new_tag)

    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'f_date','id':'2019','value':'2019','type':'radio'})
    #new_tag = soup.new_tag('input', name="tileId",  size="250", **{'type':'text'})
    tag_div1.insert(5,new_tag)
    new_tag = soup.new_tag('label', **{'for':'2019'})
    new_tag.string = '2019'
    tag_div1.insert(6,new_tag)

    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'f_date','id':'other','value':'other','type':'radio'})
    #new_tag = soup.new_tag('input', name="tileId",  size="250", **{'type':'text'})
    tag_div1.insert(7,new_tag)
    new_tag = soup.new_tag('label', **{'for':'other'})
    new_tag.string = 'Non prefixed date --> Set it here'
    tag_div1.insert(8,new_tag)

    new_tag = soup.new_tag('label', **{'class':'field','style':'font-weight: bold;font-size: 13px;'})
    new_tag.string = 'Initial Date:'
    tag_div1.insert(9,new_tag)


    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'initial_date','id':'initial_date','type':'date'})
    tag_div1.insert(10,new_tag)


    new_tag = soup.new_tag('label', **{'class':'field','style':'font-weight: bold;font-size: 13px;'})
    new_tag.string = 'Final Date:'
    tag_div1.insert(11,new_tag)


    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'final_date','id':'final_date','type':'date'})
    tag_div1.insert(12,new_tag)

    new_tag = soup.new_tag('div', **{'class':'field','style':'font-weight: bold;'})
    new_tag.string = 'Maximum cloud percent:'
    tag_form.insert(6,new_tag)

    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'max_cloud','id':'max_cloud','type':'text'})
    tag_form.insert(7,new_tag)

    new_tag = soup.new_tag('div', **{'class':'field','style':'font-weight: bold;'})
    new_tag.string = 'Maximum number of results:'
    tag_form.insert(8,new_tag)

    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'max_tile','id':'max_tile','type':'text'})
    tag_form.insert(9,new_tag)

    tag_script = soup.find_all('script')[-1]

    tag_list = tag_script.prettify().split('\n')

    new_var = "var selected_tile = '';"
    get_value_func = [ 'selected_tile = e.target.feature.properties.tile_id;',
                    'var tile_input = document.getElementById("tile_id");',
                    'tile_input.value = selected_tile;']
    n=0
    for line in tag_list:
        if 'script' in line and n <10:
            tag_list.insert(n+1,new_var)
        if 'click' in line:
            i = 0
            for statem in get_value_func:
                tag_list.insert(n+i+1,statem)
                i+=1
            break
            #print line
        n+= 1

    tag_script.string = '\n'.join(tag_list[1:-1])





    with open(output_html_path, "wb") as f_output:
        f_output.write(soup.prettify("utf-8"))

def create_leaf_page(shp_folder,arcad,loc):
    shp_grid = os.path.join(shp_folder,"sat.shp")
    shp_arcad = os.path.join(shp_folder,"arcad.shp")
    geojson_grid = convert_shp_to_geojson(shp_grid)
    if arcad == '1':
        geojson_arcad = convert_shp_to_geojson(shp_arcad)
    else:
        geojson_arcad = None
    make_leaflet_page(geojson_grid,geojson_arcad, "grid_sat.html",loc)


if __name__=='__main__':
    #reprojected_fname = reproject_to_4326('data/social_disorder_in_boston/social_disorder_in_boston_yqh.shp')
    create_leaf_page('1')


'''
    function onMapClick(e) {
    alert("You clicked the map at " + e.latlng);
}
map_81cdf183ae614f0c836f9422924987e9.on('click', onMapClick);
'''
