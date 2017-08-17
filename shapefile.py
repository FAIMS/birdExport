'''
Python:
    accept epsg as argument

    copy into new DB
    create structure for 3nf
    add geometry columns
    Call Ruby:
        Write responses into 3nf
    write geometries into 3nf tables

    call shapefile tool


    TODO:
        convert ruby calls into rbenv or system ruby calls
        figure out how shell script wrapper needs to work for exporter


'''

import unicodedata
import sqlite3
import csv, codecs, cStringIO
from xml.dom import minidom
import sys
import pprint
import glob
import json
import os
import shutil
import re
import zipfile
import subprocess
import glob
import tempfile
import errno
import imghdr
import bz2
import tarfile
import datetime

from collections import defaultdict
import zipfile
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

modes = { zipfile.ZIP_DEFLATED: 'deflated',
          zipfile.ZIP_STORED:   'stored',
          }

print sys.argv

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def convertBuffer(self, obj):

        #print type(obj)        
        
        if isinstance(obj, basestring):         
            #print obj.encode("utf-8", errors="replace")
            return obj.encode("utf-8", errors="replace").replace('"',"''")
        if isinstance(obj, buffer):         
            bufferCon = sqlite3.connect(':memory:')
            bufferCon.enable_load_extension(True)
            bufferCon.load_extension(LIBSPATIALITE)
            foo = bufferCon.execute("select astext(?);", ([obj])).fetchone()            
            return foo[0]
        if obj == None:
            return ""
        return obj



    def writerow(self, row):
        self.writer.writerow(['"%s"' % self.convertBuffer(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data.replace('"""','"').replace('"None"',''))
        # empty queue
        self.queue.truncate(0)
        self.stream.flush()

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
        


    



def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def upper_repl(match):
    if (match.group(1) == None):
        return ""
    return match.group(1).upper()

def clean(str):
     out = re.sub(" ([a-z])|[^A-Za-z0-9]+", upper_repl, str)     
     return out

def cleanWithUnder(str):
     out = re.sub("[^a-zA-Z0-9]+", "_", str)     
     return out  

def makeSurePathExists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


originalDir = sys.argv[1]
exportDir = tempfile.mkdtemp()+"/"
finalExportDir = sys.argv[2]+"/"
importDB = originalDir+"db.sqlite3"
exportDB = exportDir+"shape.sqlite3"
jsondata = json.load(open(originalDir+'module.settings'))
srid = jsondata['srid']
arch16nFiles=[]
for file in glob.glob(originalDir+"*.properties"):
    arch16nFiles.append(file)


if lsb_release.get_lsb_information()['RELEASE'] == '16.04':
    LIBSPATIALITE = 'mod_spatialite.so'
else:
    LIBSPATIALITE = 'libspatialite.so.5'    

arch16nFile = next((s for s in arch16nFiles if '.0.' in s), arch16nFiles[0])
# print jsondata
moduleName = clean(jsondata['name'])
fileNameType = "Identifier" #Original, Unchanged, Identifier

images = None
try:
    foo= json.load(open(sys.argv[3],"r"))
    # print foo["Export Images and Files?"]
    if (foo["Export Images and Files?"] != []):
        images = True
    else:
        images = False
except:
    sys.stderr.write("Json input failed")
    images = True

print "Exporting Images %s" % (images)

def zipdir(path, zip):
    for root, dirs, files in os.walk(path):
        for file in files:
            zip.write(os.path.join(root, file))


try:
    os.remove(exportDB)
except OSError:
    pass

importCon = sqlite3.connect(importDB)
importCon.enable_load_extension(True)
importCon.load_extension(LIBSPATIALITE)
exportCon = sqlite3.connect(exportDB)
exportCon.enable_load_extension(True)
exportCon.load_extension(LIBSPATIALITE)


exportCon.execute("select initSpatialMetaData(1)")
'''
for line in importCon.iterdump():
    try:
        exportCon.execute(line)
    except sqlite3.Error:       
        pass
'''     
            
exifCon = sqlite3.connect(exportDB)
exifCon.row_factory = dict_factory
exportCon.enable_load_extension(True)
exportCon.load_extension(LIBSPATIALITE)


  
exportCon.execute("create table keyval (key text, val text);")

f = open(arch16nFile, 'r')
for line in f:
    if "=" in line:
        keyval = line.replace("\n","").replace("\r","").decode("utf-8").split('=')
        keyval[0] = '{'+keyval[0]+'}'
        exportCon.execute("replace into keyval(key, val) VALUES(?, ?)", keyval)
f.close()







for aenttypeid, aenttypename in importCon.execute("select aenttypeid, aenttypename from aenttype"): 
    aenttypename = clean(aenttypename)
    attributes = ['identifier', 'createdBy', 'createdAtGMT', 'modifiedBy', 'modifiedAtGMT']
    for attr in importCon.execute("select distinct attributename from attributekey join idealaent using (attributeid) where aenttypeid = ? group by attributename order by aentcountorder", [aenttypeid]):
        attrToInsert = clean(attr[0])
        if attrToInsert not in attributes:
            attributes.append(attrToInsert)
    attribList = " TEXT, \n\t".join(attributes)
    createStmt = "Create table if not exists %s (\n\tuuid TEXT PRIMARY KEY,\n\t%s TEXT);" % (aenttypename, attribList)

    exportCon.execute(createStmt)

geometryColumns = []
for row in importCon.execute("select aenttypename, geometrytype(geometryn(geospatialcolumn,1)) as geomtype, count(distinct geometrytype(geometryn(geospatialcolumn,1))) from latestnondeletedarchent join aenttype using (aenttypeid) where geomtype is not null group by aenttypename having  count(distinct geometrytype(geometryn(geospatialcolumn,1))) = 1"):
    geometryColumns.append(row[0])
    geocolumn = "select addGeometryColumn('%s', 'geospatialcolumn', %s, '%s', 'XY');" %(clean(row[0]),srid,row[1]);
    
    exportCon.execute(geocolumn)





for aenttypename, uuid, createdAt, createdBy, modifiedAt, modifiedBy,geometry in importCon.execute("select aenttypename, uuid, createdAt || ' GMT', createdBy, datetime(modifiedAt) || ' GMT', modifiedBy, geometryn(transform(geospatialcolumn,casttointeger(%s)),1) from latestnondeletedarchent join aenttype using (aenttypeid) join createdModifiedAtBy using (uuid) order by createdAt" % (srid)):
    
    if (aenttypename in geometryColumns):       
        insert = "insert into %s (uuid, createdAtGMT, createdBy, modifiedAtGMT, modifiedBy, geospatialcolumn) VALUES(?, ?, ?, ?, ?, ?)" % (clean(aenttypename))
        exportCon.execute(insert, [str(uuid), createdAt, createdBy, modifiedAt, modifiedBy, geometry])
    else:
        insert = "insert into %s (uuid, createdAtGMT, createdBy, modifiedAtGMT, modifiedBy) VALUES(?, ?, ?, ?, ?)" % (clean(aenttypename))
        exportCon.execute(insert, [str(uuid), createdAt, createdBy, modifiedAt, modifiedBy])



try:
    os.remove(exportDir+'shape.out')
except OSError:
    pass


subprocess.call(["bash", "./format.sh", originalDir, exportDir, exportDir])



updateArray = []

for line in codecs.open(exportDir+'shape.out', 'r', encoding='utf-8').readlines():  
    out = line.replace("\n","").replace("\\r","").split("\t")
    #print "!!%s -- %s!!" %(line, out)
    if (len(out) ==4):      
        update = "update %s set %s = ? where uuid = %s;" % (clean(out[1]), clean(out[2]), out[0])
        data = (unicode(out[3].replace("\\n","\n").replace("'","''")),)
        # print update, data
        exportCon.execute(update, data)




exportCon.commit()

filename=datetime.date.today().strftime("BirdNesting-OutstandingTasks-%Y-%m-%d.csv")
shutil.copyfile(exportDir+filename, finalExportDir+filename)




'''
tarf = tarfile.open("%s/%s-export.tar.bz2" % (finalExportDir,moduleName), 'w:bz2')
try:
    for file in files:
        tarf.add(exportDir+file, arcname=moduleName+'/'+file)
finally:
    tarf.close()
'''



try:
    os.remove(exportDir)
except OSError:
    pass
