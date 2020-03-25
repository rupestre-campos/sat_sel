from multiprocessing import Pool,Manager,cpu_count
from subprocess import call
import os

def paralel_img_processing(img_path,pr):
    if len(img_path)>0:
        proc = len(img_path)
        if proc > pr:
            proc = pr
        out_imgs = [(x,'{}.tif'.format(x[:-4])) for x in img_path]
        pool = Pool(processes=proc, maxtasksperchild=10)
        jobs= {}
        for item in out_imgs:
            jobs[item[0]] = pool.apply_async(reproject_to_4326, [item])
        for item,result in jobs.items():
            try:
                result = result.get()
            except Exception as e:
                print(e)
        pool.close()
        pool.join()
    return [('{}.png'.format(x[:-4])) for x in img_path]

def reproject_to_4326(imgs):
    img_p = imgs[0]
    out_img = '{}.vrt'.format(imgs[1][:-4])
    png = '{}.png'.format(imgs[1][:-4])
    try:
        if not os.path.isfile('{}.png'.format(out_img[:-4])):
            call('gdalwarp -q -t_srs epsg:4326 -of VRT {} {}'.format(img_p,out_img),shell=True)
            call('gdal_translate -q -of PNG -a_nodata 0 {} {}'.format(out_img,png),shell=True)
            call('gdaladdo -r cubic --config COMPRESS_OVERVIEW JPEG --config PHOTOMETRIC_OVERVIEW YCBCR \
                  --config PHOTOMETRIC_OVERVIEW YCBCR {} 2 4 8 16 32 64 128 256'.format(png),shell=True)
            call('rm {}'.format(img_p),shell=True)
            call('rm {}'.format(out_img),shell=True)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    pass
