from subprocess import call
import os
from osgeo import ogr
from datetime import datetime
import pandas as pd
import re
from multiprocessing import Pool,Manager,cpu_count
#gsutil cp -r gs://gcp-public-data-sentinel-2/tiles/20/L/PQ/S2A_MSIL1C_20151230T142546_N0201_R010_T20LPQ_20151230T235521.SAFE ./
#https://krstn.eu/landsat-batch-download-from-google/
'''
grid_sentinel = r'B:\monitoramento_kfw\base_raster\download\PA\grid_pa_sentinel.shp'
outfolder = r".\preview"
startdate = '2018-08-01'
enddate = '2019-03-25'
tile_limit = 3
cloud_limit = 10
#sat = '8'
'''

stDate = re.compile(r'201[6-9][01]\d[0-3]\dT[01]\d\d\d\d\d')
stTile = re.compile(r'(?i)[12][0-589][H-N][B-HK-NP-RT-VW-Z][A-HJ-NP-V]')

#stDate = re.compile(r'201[6789][01]\d[0123]\d')

def downloadSentinel(data_folder,tileid,cloud_limit,tile_limit,startdate,enddate,outfolder,preview,pr):
    sortColumns = ['CLOUD_COVER']
    tilefuso = tileid[0:2]
    single_letter = tileid[2:3]
    double_letter = tileid[3:]
    file_name = os.path.join("index","sentinel_filtered_dataframev3.pickle")
    df = pd.read_pickle(file_name)
    tile_id = '{}_{}_{}'.format(tilefuso,single_letter,double_letter)
    start = datetime.strptime(startdate, '%Y-%m-%d')
    end = datetime.strptime(enddate, '%Y-%m-%d')
    select = df[(df['SENSING_TIME'] >= start) & (df['SENSING_TIME'] <= end)]
    select = select[(select['TILE_ID'] == tile_id)]
    select = select[select['CLOUD_COVER'] <= cloud_limit]
    select = select.sort_values(sortColumns)
    td_numb = 0
    out_tile_folder = os.path.join(outfolder,tile_id)
    call('mkdir {}'.format(out_tile_folder),shell=True)
    image_list = []
    download_scenes = []
    if len(select) != 0:
        #print select
        #print products Columns: [TILE_ID, PRODUCT_ID, GRANULE_ID, SENSING_TIME, CLOUD_COVER, GEOMETRIC_QUALITY, NORTH_LAT, SOUTH_LAT, WEST_LON, EAST_LON, TOTAL_SIZE, BASE_URL]
        for i in select.index.values:
            if td_numb >= tile_limit:
                break
            prodId = select.at[i,'PRODUCT_ID']
            print prodId
            granuleId = select.at[i,'GRANULE_ID']

            _st_date = stDate.findall(prodId)[0]
            _st_tile = stTile.findall(prodId)
            if not len(_st_tile) == 0:
                _st_tile = _st_tile[0]
                preview_file_name = 'T{}_{}_PVI.jp2'.format(_st_tile,_st_date)
            else:
                prname = granuleId.replace('MSI','PVI').split('.')[0][:-4]
                preview_file_name = '{}.jp2'.format(prname)
            td_numb +=1
            #print ('downloading scene number {} for this tile id'.format(td_numb))
            print prodId , _st_tile, _st_date
            url = select.at[i,'BASE_URL'].strip()
            preview_url = '/'.join([url,'GRANULE',granuleId,'QI_DATA',preview_file_name])
            #print preview_url
            if preview == True:
                preview_path = os.path.join(out_tile_folder,preview_file_name)
                image_list.append(preview_path)
                if os.path.isfile('{}.png'.format(preview_path[:-4])):
                    print('already downloaded')
                    continue
                url = preview_url

            download_scenes.append((url,out_tile_folder))
        if len(download_scenes)> 0:
            proc = len(download_scenes)
            if proc > pr:
                proc = pr
            parallelMother(download_scenes,proc)
            print('download complete')
        image_list.reverse()
        return [out_tile_folder,image_list]
    else:
        return [out_tile_folder,image_list]
        print('could not find any scene with that criteria')


    #scenes = stack_sentinel(tilefuso,bands,outfolder)
    #print '\n scenes dictionary'
    #print scenes
    #createFP(scenes,outfolder)
    #return scenes
def parallelMother(scenes,proc):
    pool = Pool(processes=proc, maxtasksperchild=10)
    jobs= {}
    for item in scenes:
        jobs[item[0]] = pool.apply_async(download_parallel, [item])
    for item,result in jobs.items():
        try:
            result = result.get()
        except Exception as e:
            print(e)
    pool.close()
    pool.join()

def download_parallel(data):
    url = data[0]
    out_tile_folder =data[1]
    call('python "./gsutil/gsutil.py" -q cp -r {} {}'.format(url,out_tile_folder),shell=True)

def main():
    driver = ogr.GetDriverByName('ESRI Shapefile')
    dataSource = driver.Open(grid_sentinel, 0) # 0 means read-only. 1 means writeable
    layer = dataSource.GetLayer()
    for feature in layer:
        tile = feature.GetField('tile_id')
        tile_fuso = tile[0:2]
        single_letter = tile[2:3]
        double_letter = tile[3:]
        print tile_fuso,single_letter,double_letter
        downloadSentinel(data_folder,tile_fuso,single_letter,double_letter,cloud_limit,tile_limit,startdate,enddate,sort_columns,outfolder,bands)

if __name__ == "__main__":
    main()
