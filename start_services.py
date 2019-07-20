from subprocess import call
import webbrowser
import time

python_path = r"C:\Program Files\QGIS 3.4\bin\python.exe"
server_path = r'C:\IMG_DOWNLOAD\small_server.py'

call('start /MIN /SEPARATE {} {}'.format('python',server_path),shell=True)
#time.sleep(2)
#webbrowser.open('http://localhost:8080', new=2)