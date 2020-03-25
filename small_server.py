from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import urlparse
from download_sentinel import downloadSentinel
from create_leaflet_raster import preview_to_new_map
from paralel_reproject import paralel_img_processing
from osgeo import ogr
import os
from subprocess import call
from create_leaflet_vector_bd_wSelect import create_leaf_page,get_arcad,create_grid_sat_shp,get_layers_from_search
from process_index import process_indexBR

pr = 4

databaseUser = "ckc"
databasePW = "garrafadecafe"

databaseServer = "177.105.35.20"
databaseName = "equipe_geo"

data_folder = '/home/rupestre/IMG_DOWNLOAD'

PORT_NUMBER = 8080

tile_id = ''
db_col = ''
sat = ''
uf = ''
ar_cad = ''
#This class will handles any incoming request from
#the browser
class myHandler(BaseHTTPRequestHandler):

	#Handler for the GET requests
	def do_GET(self):
		global tile_id,data_folder,db_col,pr,sat,uf,ar_cad

		if self.path=="/":
			self.path="/index.html"

		try:
			#Check the file extension required and
			#set the right mime type

			sendReply = False
			if self.path.endswith(".html"):
				mimetype='text/html'
				sendReply = True
			if self.path.startswith("/update_index"):
				process_indexBR()
				self.path="/index.html"
				self.wfile.write('Your sentinel index has just been updated! Return and select your images')

			if self.path.startswith("/gen_map"):
				if not self.path.endswith('update'):
					sat = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('sat', None)
					uf = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('uf', None)
					ar_cad = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('arcad', None)
				print sat,uf,ar_cad

				shp_folder = os.path.join(data_folder,'shp')
				connString = "PG: host=%s dbname=%s user=%s password=%s" %(databaseServer,databaseName,databaseUser,databasePW)
				conn = ogr.Open(connString)
				satLay,multi,loc = get_layers_from_search(conn,ar_cad,uf,sat)
				create_grid_sat_shp(shp_folder,satLay,multi)
				create_leaf_page(shp_folder,ar_cad[0],loc)
				conn = None
				self.send_response(200)
				self.end_headers()
				#self.path="/tiles_preview.html"
				self.path="/grid_sat.html"
				self.wfile.write('<html>')
				self.wfile.write('  <head>')
				self.wfile.write('		<meta http-equiv="refresh" content="0;url={}" />'.format(self.path))
				self.wfile.write('  </head>')
				self.wfile.write('</html>')

			if self.path.startswith("/download_tile"):

				tile_id = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('tile_id', None)
				pre_fix_date = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('f_date', None)
				initial_date = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('initial_date', None)
				final_date = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('final_date', None)
				max_cloud = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('max_cloud', None)
				max_tile = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('max_tile', None)
				outfolder= os.path.join(data_folder,'preview')
				print('got {} {} {} {} {} {}'.format(tile_id,pre_fix_date,initial_date,final_date,max_cloud,max_tile))
				if pre_fix_date[0] == "2017":
					initial_date = '2016-01-01'
					final_date = '2016-12-31'
					db_col = 'd_2017'
				elif pre_fix_date[0] == "2018":
					initial_date = '2018-01-01'
					final_date = '2018-12-31'
					db_col = 'd_2018'
				elif pre_fix_date[0] == "2019":
					initial_date = '2019-01-01'
					final_date = '2019-12-31'
					db_col = 'd_2019'
				else :
					initial_date = initial_date[0]
					final_date = final_date[0]
					db_col = 'img_down'

				out_tiles = downloadSentinel(tile_id[0],int(max_cloud[0]),int(max_tile[0]),initial_date,final_date,outfolder,True,pr)
				if not len(out_tiles[1]) == 0:
					print('search resulted in {}'.format(out_tiles))
					out_tiles = paralel_img_processing(out_tiles[1],pr)
					print('process resulted in {}'.format(out_tiles))
					preview_to_new_map(out_tiles,ar_cad[0])
					print('map preview generated')
					#self.path="/tiles_preview.html"
					self.send_response(200)
					self.end_headers()
					self.path="/tiles_preview.html"
					self.wfile.write('<html>')
					self.wfile.write('  <head>')
					self.wfile.write('		<meta http-equiv="refresh" content="0;url={}" />'.format(self.path))
					self.wfile.write('  </head>')
					self.wfile.write('</html>')
				else:
					self.send_error(404,'Not any image found, try again')

			if self.path.startswith("/fulldownload"):
				print self.path
				selected_imgs = urlparse.parse_qs(urlparse.urlparse(self.path).query).get('tile_id', None)
				selected_imgs = selected_imgs[0].split(',')
				print tile_id,selected_imgs
				connString = "PG: host=%s dbname=%s user=%s password=%s" %(databaseServer,databaseName,databaseUser,databasePW)
				conn = ogr.Open(connString,1)
				satLay = conn.GetLayer('monitoramento_kfw.grid_sat')
				satLay.SetAttributeFilter("sat = 'SENTINEL' AND tile_id = '{}'".format(tile_id[0]))
				for feature in satLay:
					feature.SetField(db_col, ','.join(selected_imgs))
					satLay.SetFeature(feature)
				conn = None
				self.send_response(200)
				self.end_headers()
				self.path="/gen_map_update"
				self.wfile.write('<html>')
				self.wfile.write('  <head>')
				self.wfile.write('		<meta http-equiv="refresh" content="0;url={}" />'.format(self.path))
				self.wfile.write('  </head>')
				self.wfile.write('</html>')


			if sendReply == True:
				#Open the static file requested and send it
				f = open(curdir + sep + self.path)
				self.send_response(200)
				self.send_header('Content-type',mimetype)
				self.end_headers()
				self.wfile.write(f.read())
				f.close()
			return


		except IOError:
			self.send_error(404,'File Not Found: %s' % self.path)
		except KeyboardInterrupt:
			self.send_error(404,'File Not Found: %s' % self.path)


def main():
	PORT_NUMBER = 8080
	try:
		#Create a web server and define the handler to manage the
		#incoming request
		server = HTTPServer(('', PORT_NUMBER), myHandler)
		print 'Started httpserver on port ' , PORT_NUMBER

		#Wait forever for incoming htto requests
		server.serve_forever()

	except KeyboardInterrupt:
		print '^C received, shutting down the web server'
		server.socket.close()

if __name__ == "__main__":
	main()
