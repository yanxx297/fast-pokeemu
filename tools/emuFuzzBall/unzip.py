import gzip

file = "program"
outfilename = "unzip"
inF = gzip.open(file, 'rb')
outF = open(outfilename, 'wb')
outF.write( inF.read() )
inF.close()
outF.close()