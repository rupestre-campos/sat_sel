import os
from osgeo import osr, gdal, ogr
from subprocess import call
import folium
from folium import plugins
from bs4 import BeautifulSoup as Soup
from bs4 import Tag


def style_function_arcad(feature):
    return {
            'fillColor': '#000000',
            'color': '#000000',
            'weight': 0.05,
            'dashArray': '0, 0'
        }


def GetExtent(gt,cols,rows):
    ''' Return list of corner coordinates from a geotransform

        @type gt:   C{tuple/list}
        @param gt: geotransform
        @type cols:   C{int}
        @param cols: number of columns in the dataset
        @type rows:   C{int}
        @param rows: number of rows in the dataset
        @rtype:    C{[float,...,float]}
        @return:   coordinates of each corner
    '''
    ext=[]
    xarr=[0,cols]
    yarr=[0,rows]
    for px in xarr:
        for py in yarr:
            x=gt[0]+(px*gt[1])+(py*gt[2])
            y=gt[3]+(px*gt[4])+(py*gt[5])
            ext.append([x,y])
            #print x,y
        yarr.reverse()
    return ext

def getCenter(ext):
    x = []
    y = []
    for point in ext:
        x.append(point[0])
        y.append(point[1])
    xc = float(sum(x))/len(x)
    yc = float(sum(y))/len(y)
    return (xc,yc)

def preview_to_new_map(img_list,data_folder,tile_id,uf,db_col):
    ds = gdal.Open(img_list[0])
    gt = ds.GetGeoTransform()
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    ext = GetExtent(gt,cols,rows)
    center = getCenter(ext)
    ds = None


    tiles = 'Stamen Toner'
    m = folium.Map(location=[center[1],center[0]], height='90%', zoom_start = 10,tiles=tiles)
    #tiles='Stamen Toner'
    #if len(img_list) >1:
    n=0
    show = False

    for imgn in img_list:
        print imgn
        imgn_name = os.path.basename(imgn)
        ds = gdal.Open(imgn)
        gt = ds.GetGeoTransform()
        cols = ds.RasterXSize
        rows = ds.RasterYSize
        ext = GetExtent(gt,cols,rows)
        ds = None
        #with rio.open(imgn) as src:
        #    img_rio = src.read()
        coords = [[i[1],i[0]] for i in ext]
        print coords
        n+=1
        if n == len(img_list):
            show = True
        folium.raster_layers.ImageOverlay(name=imgn_name,image=imgn,interactive=True,bounds=coords,show=show).add_to(m)


    m.add_child(folium.LayerControl())
    outHtml = 'tiles_preview.html'
    call('rm {}'.format(outHtml),shell=True)
    m.save(outHtml)


    with open(outHtml) as html:
        soup = Soup(html, 'html.parser')

    map_number = soup.find_all("div", {"class": "folium-map"})
    map_number = map_number[0].get('id')

    tag = soup.body

    new_tag = soup.new_tag('h1')
    new_tag.string = "Sattelite preview selection Tool"
    tag.insert(1,new_tag)

    new_tag = soup.new_tag('form',action="/fulldownload", method="get")
    tag.insert(2,new_tag)
    tag_form = soup.form
    new_tag = soup.new_tag('div', **{'class':'field'})
    new_tag.string = "SELECTED Images :"
    tag_form.insert(1,new_tag)
    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'images','id':'images','size':'250','type':'text'})
    #new_tag = soup.new_tag('input', name="tileId",  size="250", **{'type':'text'})
    tag_form.insert(2,new_tag)
    new_tag = soup.new_tag('div', **{'class':'field'})
    new_tag.string = "Parameters :"
    tag_form.insert(3,new_tag)
    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'uf','id':'uf','type':'text','value':uf[0],'readonly':'readonly'})
    tag_form.insert(4,new_tag)
    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'tile_id','id':'tile_id','type':'text','value':tile_id[0],'readonly':'readonly'})
    tag_form.insert(5,new_tag)
    new_tag = Tag(builder=soup.builder,
               name='input',
               attrs={'name':'db_col','id':'db_col','type':'text','value':db_col,'readonly':'readonly'})
    tag_form.insert(6,new_tag)

    new_tag = soup.new_tag('input', value="Save", **{'type':'submit'})
    tag_form.insert(7,new_tag)

    click_function = '''
    function clickHandler(e) {
        var lay = [];

        var n=0;
        for (var l in %s._layers) {
            if (n==0) {

                for (var t in %s._layers[l]._events.add[0].ctx._layers) {
                    var overlay = %s._layers[l]._events.add[0].ctx._layers[t];

                    if (overlay.layer._map != null && overlay.name != 'stamentoner' && overlay.name != 'area cadastravel') {
                        console.log(overlay.name);
                        console.log('Active');
                        lay.push(overlay.name)
                    }

            }};
            n+=1
        }
        //console.log(lay)
        var tile_input = document.getElementById('tile_id');
        tile_input.value = lay;
    };
    %s.on("dblclick", clickHandler);
    ''' % (map_number,map_number,map_number,map_number)

    tag_script = soup.find_all('script')[-1]
    tag_script.append(click_function)
    with open(outHtml, "wb") as f_output:
        f_output.write(soup.prettify("utf-8"))

def main():
    pass

if __name__=='__main__':
    main()
