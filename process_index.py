import pickle
import os
from osgeo import ogr
from subprocess import call
import gzip
import shutil
import datetime



def extract_gz(out_index):
    index = os.path.join(out_index,'index.csv.gz')
    out_index = os.path.join(out_index,'index.csv')
    with gzip.open(index, 'rb') as f_in:
        with open(out_index, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    #call('del /q {}'.format(index),shell=True)
    return out_index

def download_index(url,out_index):
    call('python "./gsutil/gsutil.py" -q cp -r {} {}'.format(url,out_index),shell=True)


def process_indexBR():
    out_index = '/home/rupestre/IMG_DOWNLOAD/index'
    url = 'gs://gcp-public-data-sentinel-2/index.csv.gz'

    download_index(url,out_index)
    index_csv = extract_gz(out_index)
    f = open(index_csv)
    outfolder = '\\'.join(index_csv.split('\\')[:-1])
    databaseUser = "ckc"
    databasePW = "garrafadecafe"

    databaseServer = "177.105.35.20"
    databaseName = "equipe_geo"

    connString = "PG: host=%s dbname=%s user=%s password=%s" %(databaseServer,databaseName,databaseUser,databasePW)

    conn = ogr.Open(connString)

    satLay = conn.GetLayer('monitoramento_kfw.grid_sat')

    satLay.SetAttributeFilter("sat = 'SENTINEL'")
    sentinelBR = {}
    for feature in satLay:
        tileId = feature.GetField('tile_id')
        fuse = tileId[:2]
        single_letter = tileId[2:3]
        double_letter = tileId[3:]
        print(fuse,single_letter,double_letter)
        key = '{}_{}_{}'.format(fuse,single_letter,double_letter)
        sentinelBR[key] = {}

    n = 0
    for line in f:
        if n == 0:
            n+=1
            continue
        data = line.split(',')
        tileId = data[3]
        fuse = tileId[:2]
        single_letter = tileId[2:3]
        double_letter = tileId[3:]
        key = '{}_{}_{}'.format(fuse,single_letter,double_letter)
        if key in sentinelBR:
            if not data[1] in sentinelBR[key]:
                sentinelBR[key][data[1]] ={}
            sentinelBR[key][data[1]] = {'GRANULE_ID':data[0],'PRODUCT_ID':data[1],'SENSING_TIME':data[4],'TOTAL_SIZE':data[5],'CLOUD_COVER':data[6],'GEOMETRIC_QUALITY':data[7],'NORTH_LAT':data[9],'SOUTH_LAT':data[10],'WEST_LON':data[11],'EAST_LON':data[12],'BASE_URL':data[13]}
            n += 1
            if data[1] == '':
                print(line)
            print(n,'\t-\t',data[1])

    output_pickle_file = os.path.join(outfolder,'sentinel_index.pickle')
    p = open(output_pickle_file, 'wb')
    pickle.dump(sentinelBR, p, pickle.HIGHEST_PROTOCOL)
    p.close()

    import pandas as pd

    f = open(output_pickle_file, 'rb')
    save = pickle.load(f)
    #n = 0
    #for i in save:
    #    n += len(save[i])

    totalEntry = n
    columns = ['TILE_ID','PRODUCT_ID','GRANULE_ID','SENSING_TIME','CLOUD_COVER','GEOMETRIC_QUALITY','NORTH_LAT','SOUTH_LAT','WEST_LON','EAST_LON','TOTAL_SIZE','BASE_URL']
    df = pd.DataFrame(index=[i for i in xrange(totalEntry)],columns=columns)

    i = 0
    for tileId in save:
        print(tileId)
        for productId in save[tileId]:
            info = save[tileId][productId]
            rowList = [tileId,productId,info['GRANULE_ID'],info['SENSING_TIME'],info['CLOUD_COVER'],info['GEOMETRIC_QUALITY'],info['NORTH_LAT'],info['SOUTH_LAT'],info['WEST_LON'],info['EAST_LON'],info['TOTAL_SIZE'],info['BASE_URL']]
            for j in range(len(rowList)):
                df.at[i,columns[j]] = rowList[j]
            i += 1

    df = df.dropna(how='all')
    df['CLOUD_COVER'] = df.CLOUD_COVER.astype(float)
    df['SENSING_TIME'] = df.apply(lambda row: row['SENSING_TIME'][:-5], axis=1)
    df['SENSING_TIME'] =  pd.to_datetime(df['SENSING_TIME'])


    file_name = os.path.join(outfolder,'sentinel_filtered_dataframev3.pickle')
    df.to_pickle(file_name)

if __name__ == "__main__":
    main()
