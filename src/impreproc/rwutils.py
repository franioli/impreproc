#-------------------------------------------------------------------------------
#                           GeoNetpy v0.0.1 alpha
#
# Copyright (C) 2018 Lorenzo Rossi, Daniele Sampietro
#-------------------------------------------------------------------------------
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import time
import numpy as np
import os.path
import geoutils as gu
import re
import xlrd

# generic functions -----------------------------------------------------------
def fileextchecker(fname, ext):
    ''' check if the file fname exist, otherwise add the ext extension and check
    again if the file exist.
    If the file does not exist the function return -1.
    The function accept as ext input a list of extension. In case the file is 
    without extension the added extension is the one of the existing file 
    (if any)'''
    
    if type(ext)==str: # check if ext is a string
        ext = [ext]    # in case introduce it into a list to correctly indexing it
    elif type(ext)!=list: # if ext is not a string and not a list convert it to a list
        ext = list(ext)
    test = True # check if at least one of the extensions is present at the end of the filename (extension is present if test become false) 
    for i in range(0, len(ext)):
        test = test and fname[-(len(ext[i])+1):].lower() != ('.' + ext[i])
        
    if not(os.path.isfile(fname)) and test: 
    # if the file does not have the extension and does not exist the various extensions
    # are tested in order to check if a file with one of the extensions exists
    # and fname consequently modified
        for i in range(0, len(ext)):
            if os.path.isfile(fname + '.' + ext[i]):
                fname = fname + '.' + ext[i]
    # finally after all the modification the existence of fname is checked again
    # If it exists it is returned, else -1 is returned
    if os.path.isfile(fname):
        return fname
    else:
        return -1

# read functions --------------------------------------------------------------
def ptsread(fname, verbose=1, concatenate=1):   
    '''Read the pts point cloud ASCII format.
    SYNTAX:
          xyz, rgb, ins = ptsread(fname, verbose = 1, concatenate = 1)
    
     INPUT:
     - fname       --> name of the pts file
     - verbose     --> opt, bool, true = verbose output. If no specified it is
                       assumed true
     - concatenate --> opt, bool, true = concatenate all the point clouds. If
                       not specified is assumed true
     
     OUTPUT:
     - xyz --> coordinates of the point cloud (nparray if concatenate is true,
               list of nparray if concatenate is false)
     - rgb --> RGB of the point cloud (nparray if concatenate is true,
               list of nparray if concatenate is false)
     - ins --> intensity of the point cloud (nparray if concatenate is true,
               list of nparray if concatenate is false)
    
       v1.0
       Lorenzo Rossi
       2018-08-18
    '''
    
    # check if the file exist, otherwise add the pts extension
    if not(os.path.isfile(fname)) and fname[-4:].lower() != '.pts':
        fname = fname + '.pts'        
        
    tin = time.time()  # starting time
    
    # read the file -----------------------------------------------------------
    fid = open(fname, 'r')
    
    if verbose == 1:
        print('Reading ' +  fname + ':')
        nLines = len(fid.readlines())
    
    # initialize variables
    data  = [] # store the data (separated as in the file)
    nData = [] # store the number of data per each part
    nPart = 0  # counter of the numper of parts
    
    fid.seek(0, 0)         # go to the beginning of the file
    line = fid.readline()  # read the first line
    while line != '':      # loop to read all the part of the file
        nData.append(int(line.replace('\n', ''))) # store the number of data of the current part
        if verbose == 1:
            print('\tReading part %d (%d points)...%.1f%%' % (nPart+1, nData[nPart], sum(nData) / nLines * 100))
        # data.append([np.genfromtxt(fid, delimiter=' ', max_rows = nData[nPart-1])])
        data.append(np.fromfile(fid, count=7*nData[nPart], sep=' '))  # faster
        data[nPart] = np.reshape(data[nPart], [nData[nPart], 7])               # the shape of the data is nData[nPart-1]
        nPart = nPart + 1     # increase the nPart counter
        line = fid.readline() # read a new line (contains the number of the points of next PC or the end of the file)
    fid.close()
    
    if verbose == 1:
        print('File read in %.1f sec' % (time.time() - tin))    
    
    # store the file in variables ---------------------------------------------
    if concatenate == 1:
        data = np.concatenate(data)
        xyz = data[:,0:3]
        ins = data[:,3]
        rgb = data[:,4:7]
    else:
        xyz = []
        ins = []
        rgb = []
        for i in range(len(data)):
            xyz.append(data[i][:,0:3])
            ins.append(data[i][:,3])
            rgb.append(data[i][:,4:7])

    return xyz, rgb, ins

def ptsreadb(fname, verbose = 1, concatenate = 1):
   '''Read the pts point cloud ASCII format.
   SYNTAX:
         xyz, rgb, ins = ptsread2(fname, verbose = 1, concatenate = 1)
   
    INPUT:
    - fname       --> name of the pts file
    - verbose     --> opt, bool, true = verbose output. If no specified it is
                      assumed true
    - concatenate --> opt, bool, true = concatenate all the point clouds. If
                      not specified is assumed true
    
    OUTPUT:
    - xyz --> coordinates of the point cloud (nparray if concatenate is true,
              list of nparray if concatenate is false)
    - rgb --> RGB of the point cloud (nparray if concatenate is true,
              list of nparray if concatenate is false)
    - ins --> intensity of the point cloud (nparray if concatenate is true,
              list of nparray if concatenate is false)
    
    NB: the b version is too much slower for huge points clouds
 
    v1.1
    Lorenzo Rossi
    2018-08-18
   '''
   
   tin = time.time()  # starting time
   if verbose == 1:
           print('Reading ' +  fname + ':')
   # read the file and load data in a list with all the elements already spitted
   fid = open(fname, 'r')
   indata = [i.split(sep=' ') for i in fid.readlines()]
   fid.close()
   # initialize empty lists to store the data (coordinates, intensitiy and color)
   xyz = []
   ins = []
   rgb = []
   # initialize counters
   nl = 0      # number of line to be read
   nPart = 0   # number of read parts
   nLines = len(indata) # total number of lines
   
   while nl < nLines: # loop until lines are finished
       if len(indata[nl]) == 1: # if the number of data is 1 it means that is the line 
                                # indicating the number of elements of the current part
           nData = int(indata[nl][0])
           nPart = nPart + 1
           if verbose == 1:
               print('\tReading part %d (%d points)...%.1f%%' % (nPart, nData, (nData + nl - nPart -1) / nLines * 100))
           # store the data by appending matrices in a new element of the corresponding list
           xyz.append(np.column_stack((np.array([float(k[0]) for k in indata[nl+1:nl+1+nData]]), \
                                       np.array([float(k[1]) for k in indata[nl+1:nl+1+nData]]), \
                                       np.array([float(k[2]) for k in indata[nl+1:nl+1+nData]]))))
           ins.append(np.array([float(k[3]) for k in indata[nl+1:nl+1+nData]]))
           rgb.append(np.column_stack((np.array([float(k[4]) for k in indata[nl+1:nl+1+nData]]), \
                                       np.array([float(k[5]) for k in indata[nl+1:nl+1+nData]]), \
                                       np.array([float(k[6]) for k in indata[nl+1:nl+1+nData]]))))
           nl = nl + nData + 1 # increase the number of the line to be read
   # concatenate the data in necessary
   if concatenate == 1:
       xyz = np.concatenate(xyz)
       ins = np.concatenate(ins)
       rgb = np.concatenate(rgb)
   if verbose == 1:
       print('File read in %.1f sec' % (time.time() - tin))

def mm2read(fname):
    '''Read the mm2 Topcon format.
    SYNTAX:
        tsobs, tsstn = mm2read(fname)
        
    INPUT:
        fname --> string containing the name of the mm2 file (extension is
                  optional)
    OUTPUT:
        tsobs --> list containing an observation per row. The field order in
                  each row is: Station, Point, hs, Azimut, Zenit, Slope Distance,
                  hp, code, Station number
        tsstn --> list containing the name of the stations. The field order in 
                  each row is: Station number, Station name, hs
    
    v1.0
    Lorenzo Rossi
    2018-08-18
    '''
    # check if the file exist, otherwise add the mm2 extension
    if not(os.path.isfile(fname)) and fname[-4:].lower() != '.mm2':
        fname = fname + '.mm2' 
        
    # read all the lines of the file
    fid = open(fname, 'r')
    indata = [i.split(sep='\x1d') for i in fid.readlines()]
    fid.close()
    
    # count number of stations and observations
    ltype = [i[0] for i in indata]
    ntotstn = ltype.count('S|')
    ntotobs = ltype.count('P|')
    
    # initialize output variables
    tsstn = [None] * ntotstn
    tsobs = [None] * ntotobs
    
    # initialize useful variable for the loop
    stni = None
    hsi  = None
    nstn = 0
    nobs = 0
    
    # loop to decode all the lines of the file
    for i in range(len(indata)):
        if ltype[i] == 'S|': # station definitions
            stni = indata[i][1]
            hsi  = float(indata[i][3])
            tsstn[nstn] = [nstn, stni, hsi]
            nstn = nstn + 1
        elif ltype[i] == 'P|': # observations to points
            pti = indata[i][1]
            cdi = indata[i][2]
            hpi = float(indata[i][3])
            try:
                azi = float(indata[i][4])
            except:
                azi = np.nan    
            try:
                zni = float(indata[i][5])
            except:
                zni = np.nan    
            try:
                dsi = float(indata[i][6])
            except:
                dsi = np.nan 
            tsobs[nobs] = [stni, pti, hsi, azi, zni, dsi, hpi, cdi, nstn-1]
            nobs = nobs+1
    return tsobs, tsstn

def rw5readline(indata, strlist, fieldtype):
    ''' Read a line of an rw5 file.
    SYNTAX:
        outdata = rw5readline(indata, strlist, fieldtype)
        
    INPUT:
    - indata    --> input list of string to be parsed (already divided at ,)
    - strlist   --> list of string identifing the fields
    - filedtype --> list of string identifing the type of the field for the casting
    
    OUTPUT:
    - outdata   --> list containing the value of the filed according to field order
    
    v1.0
    Lorenzo Rossi
    2018-08-19
    '''
    outdata = dict((el, None) for el in strlist)
    for i in range(len(indata)):
        for j in range(len(strlist)):
            if indata[i][0:len(strlist[j])] == strlist[j]:
                if fieldtype[j] == 'str':
                    outdata[strlist[j]] = indata[i][len(strlist[j]):].replace('\n', '')
                else:
                    exec('outdata[strlist[j]]=' + fieldtype[j] + '(indata[i][len(strlist[j]):])')
    return outdata

def addgpsline(gps):
    '''Add a new gps empty line to the hps list'''
	# Field list:
    # [0.Point, 1.Phi [deg], 2.Lam [deg], 3.h [m], 4.Code, 5.hr [m], 6.X [m], 7.Y [m], 8.Z [m], 
    #         9.Easting [m], 10.Northing [m], 11.H [m], 12.Date, 13.Time, 14.Base Point, 15.DX [m], 
    #         16.DY [m], 17.DZ [m], 18.Cxx, 19.Cyy, 20.Czz, 21.Cxy, 22.Cxz, 23.Cyz, 24.ESDV [m], 
    #         25.NSDV [m], 26.VSDV [m], 27.STATUS, 28.SATS, 29.PDOP, 30.HDOP, 31.VDOP, 32.GDOP, 
    #         33.TDOP, 34.Depth quality, 35.RTK device, 36.Cee, 37.Cnn, 38.Chh, 39.Cen, 40.Ceh, 41.Cnh]
    gps.append({'Name': '', 'Phi': np.nan, 'Lam': np.nan, 'h': np.nan, 'Code': '', 'hr': np.nan, 'X': np.nan, 'Y': np.nan, 'Z': np.nan,
           'EastL': np.nan, 'NorthL': np.nan, 'HL': np.nan, 'Time':  np.nan * np.zeros((6)), 'BPnameraw': '', 'BPname': '', 'BPid': np.nan, 'BProw': np.nan,
           'DXraw': np.nan, 'DYraw': np.nan, 'DZraw': np.nan, 'DX': np.nan, 'DY': np.nan, 'DZ': np.nan, 'Cxxraw': np.nan * np.zeros((6)), 'Cxx': np.nan * np.zeros((6)), 
           'ESDV': np.nan, 'NSDV': np.nan, 'VSDV': np.nan, 'STATUSfull': '', 'STATUS': '', 'SATS': np.nan, 'PDOP': np.nan, 'HDOP': np.nan, 'VDOP': np.nan,
           'GDOP': np.nan, 'TDOP': np.nan, 'Depth quality': np.nan, 'Cee': np.nan * np.zeros((6)), 'GPSTime': np.nan * np.zeros(6), 'GPSTimeraw': np.nan * np.zeros((4)), 
           'Xraw': np.nan, 'Yraw': np.nan, 'Zraw': np.nan, 'Ceeraw': np.nan * np.zeros((6)), 'FixedEpochs': [np.nan, np.nan]})

def addbpline(bp):
    '''Add a new basepoint empty line to the bp list'''
    # basepoints [0.Point, 1.Phi [deg], 2.Lam [deg], 3.h [m], 4.Antenna height [m],
    #             5.Antenna phase centre vertical offset [m], 6.X [m], 7.Y[m], 8.Z[m],
    #             9. RTK Protocol, 10. RTK device, 11. RTK Network, 
    #             12.X PC [m], 13.Y PC [m], 14.Z PC[m]]
    bp.append({'Name': '', 'ID': np.nan, 'Phi': np.nan, 'Lam': np.nan, 'h': np.nan, 'AG': np.nan,
          'PA': np.nan, 'X': np.nan, 'Y': np.nan, 'Z': np.nan, 'RTKprot': '', 'RTKdev': '', 'RTKnet': '',
          'Xraw': np.nan, 'Yraw': np.nan, 'Zraw': np.nan,})

def rw5read(fname, ellname = 'WGS84', corrX = 0, corrY = 0, corrZ = 0, isDXraw=0):
    '''Read the rw5 Stonex format, extracting gps information.
    SYNTAX:
        gps, bp = rw5read(fname, ellname)
        
    INPUT:
        fname   --> string containing the name of the rw5 file (extension is
                    optional)
        ellname --> optional, ellipsoid name (for phi, lam, h --> X, Y, Z). If 
                    not given is assumed as 'GRS80'
    OUTPUT:
        gps  --> list containing a gps observation per row. The field order in
                 each row is:
                 0.Point, 1.Phi [deg], 2.Lam [deg], 3.h [m], 4.Code, 5.hr [m], 6.X [m], 7.Y [m], 8.Z [m], 
                 9.Easting [m], 10.Northing [m], 11.H [m], 12.Date, 13.Time, 14.Base Point, 15.DX [m], 
                 16.DY [m], 17.DZ [m], 18.Cxx, 19.Cyy, 20.Czz, 21.Cxy, 22.Cxz, 23.Cyz, 24.ESDV [m], 
                 25.NSDV [m], 26.VSDV [m], 27.STATUS, 28.SATS, 29.PDOP, 30.HDOP, 31.VDOP, 32.GDOP, 
                 33.TDOP, 34.Depth quality, 35.RTK device, 36.Cee, 37.Cnn, 38.Chh, 39.Cen, 40.Ceh, 41.Cnh
        bp   --> list containing the name of the stations. The field order in 
                 each row is: 0.Point, 1.Phi [deg], 2.Lam [deg], 3.h [m], 4.Antenna height [m],
                 5. Antenna phase centre vertical offset [m], 6.X [m], 7.Y[m], 8.Z[m], 
                 9. RTK Protocol, 10. RTK device, 11. RTK Network
    
    v1.0
    Lorenzo Rossi
    2018-08-20
    '''
    # check if the file exist, otherwise add the rw5 extension
    fname = fileextchecker(fname, 'rw5')
    
    # open the file and parse each row using , as separator
    fid = open(fname, 'r')
    indata = [i.split(sep=',') for i in fid.readlines()]
    fid.close()
    
    # ellipsoid parameters
    a, f = gu.fellipsoid(ellname)

    gps = []
    bp  = []
    
    hr = 0   # set the rover height to 0
    last = ''
    RTKdev = '' # rtk devide to be assigned to the last observation
    for i in range(len(indata)): # loop on all the rows, each if condition filter a kind of row
        if indata[i][0] == 'GPS':
            addgpsline(gps) # each new row is initialized as nan (thus avoiding problem during computation!)
            ri = rw5readline(indata[i], ['PN', 'LA', 'LN', 'EL', '--'], ['str', 'float', 'float', 'float', 'str'])
            # phi and lam are stored as dd.ppss.ssss
            gps[-1]['Name'] = ri['PN']
            gps[-1]['Phi']  = gu.sex2dec(ri['LA']) # deg
            gps[-1]['Lam']  = gu.sex2dec(ri['LN']) # deg
            gps[-1]['h']    = ri['EL'] - hr # correct for antenna height
            gps[-1]['hr']   = hr # [m]
            gps[-1]['Code'] = ri['--']
            # convert phi, lam, h --> X, Y, Z
            gps[-1]['X'], gps[-1]['Y'], gps[-1]['Z'] = gu.geo2cart(gps[-1]['Phi']*np.pi/180, gps[-1]['Lam']*np.pi/180, gps[-1]['h'], a, f)
            gps[-1]['Xraw'], gps[-1]['Yraw'], gps[-1]['Zraw'] = gu.geo2cart(gps[-1]['Phi']*np.pi/180, gps[-1]['Lam']*np.pi/180, gps[-1]['h'] + gps[-1]['hr'], a, f)
            # if len(bp) > 0: # set the base point at the last base point read (if any)
            #    gps[-1][14] = bp[-1][0] 
            # phase centre heigt
            # appy the coodinates correction corrX, corrY, corrZ (for UHF points only or if RTdev is empty (for the new palm PC)
            if 'UHF' in RTKdev or RTKdev == '':
                gps[-1]['X'] = gps[-1]['X'] - corrX
                gps[-1]['Y'] = gps[-1]['Y'] - corrY
                gps[-1]['Z'] = gps[-1]['Z'] - corrZ
                gps[-1]['Phi'], gps[-1]['Lam'], gps[-1]['h'] = gu.cart2geo(gps[-1]['X'], gps[-1]['Y'], gps[-1]['Z'], a, f)
                gps[-1]['Phi'] = gps[-1]['Phi'] * 180 / np.pi
                gps[-1]['Lam'] = gps[-1]['Lam'] * 180 / np.pi
            gps[-1]['RTKdev'] = RTKdev
            last = 'GPS'
            
        elif indata[i][0] == 'MO':
            last = 'MO'
            
        elif '--RTK Method:' in indata[i][0]: # discover if it is UHF or GPRS
            if last!='BP' and indata[i+1][0] == 'BP':
                addbpline(bp)  # each new row is initialized as nan (thus avoiding problem during computation!)
                ri = rw5readline(indata[i], ['--RTK Method: ', ' Device: ', ' Network: '], \
                                      ['str', 'str', 'str'])
                bp[-1]['RTKdev']  = ri[' Device: '] 
                bp[-1]['RTKnet']  = ri[' Network: '] 
                bp[-1]['RTKprot'] = ri['--RTK Method: '] 
            elif last=='BP':
                ri = rw5readline(indata[i], ['--RTK Method: ', ' Device: ', ' Network: '], \
                                      ['str', 'str', 'str'])
                bp[-1]['RTKdev']  = ri[' Device: '] 
                bp[-1]['RTKnet']  = ri[' Network: '] 
                bp[-1]['RTKprot'] = ri['--RTK Method: ']
            last = 'Method'
            RTKdev = rw5readline(indata[i], [' Device: '], ['str'])[' Device: ']
            
        elif indata[i][0] == 'BP':
            if last!='Method': # verify if the station is already initialized by RTK method
                addbpline(bp)  # each new row is initialized as nan (thus avoiding problem during computation!)
            ri = rw5readline(indata[i], ['PN', 'LA', 'LN', 'EL', 'AG', 'PA'], \
                                  ['str', 'float', 'float', 'float', 'float', 'float'])
            bp[-1]['Name'] = ri['PN']
            bp[-1]['ID'] = int(re.findall('\d+', ri['PN'])[-1])
            bp[-1]['Phi'] = gu.sex2dec(ri['LA']) # phi and lam are stored as dd.ppss.ssss
            bp[-1]['Lam'] = gu.sex2dec(ri['LN']) # phi and lam are stored as dd.ppss.ssss
            bp[-1]['h'] = ri['EL'] - ri['AG'] - ri['PA'] # correct for antenna height and phase centre
            bp[-1]['AG'] = ri['AG'] # antenna height
            bp[-1]['PA'] = ri['PA'] # antenna phase centre vertical offset
            # conversion phi, lam, h --> X, Y, Z
            bp[-1]['X'], bp[-1]['Y'], bp[-1]['Z'] = gu.geo2cart(bp[-1]['Phi']*np.pi/180, bp[-1]['Lam']*np.pi/180, bp[-1]['h'], a, f)
            bp[-1]['Xraw'], bp[-1]['Yraw'], bp[-1]['Zraw'] = gu.geo2cart(bp[-1]['Phi']*np.pi/180, bp[-1]['Lam']*np.pi/180, bp[-1]['h'] + bp[-1]['AG'] + bp[-1]['PA'], a, f)
            # apply the shift (for UHF surveys)
            if 'UHF' in RTKdev:
                bp[-1]['X'] = bp[-1]['X'] - corrX
                bp[-1]['Y'] = bp[-1]['Y'] - corrY
                bp[-1]['Z'] = bp[-1]['Z'] - corrZ
                bp[-1]['Xraw'] = bp[-1]['Xraw'] - corrX
                bp[-1]['Yraw'] = bp[-1]['Yraw'] - corrY
                bp[-1]['Zraw'] = bp[-1]['Zraw'] - corrZ
                bp[-1]['Phi'], bp[-1]['Lam'], bp[-1]['h'] = gu.cart2geo(bp[-1]['X'], bp[-1]['Y'], bp[-1]['Z'], a, f)
                bp[-1]['Phi'] = bp[-1]['Phi'] * 180 / np.pi
                bp[-1]['Lam'] = bp[-1]['Lam'] * 180 / np.pi
            last = 'BP'
            
        elif indata[i][0] == 'LS':
            hr = rw5readline(indata[i], ['HR'], ['float'])['HR']
            last = 'LS'
            
        elif last == 'GPS':
            if indata[i][0] == '--GS' and len(gps)>0:
                ri = rw5readline(indata[i], ['E ', 'N ', 'EL'], ['float', 'float', 'float'])
                gps[-1]['EastL'] = ri['E ']
                gps[-1]['NorthL'] = ri['N ']
                gps[-1]['HL'] = ri['EL']
                
            elif '--DT' in indata[i][0] and len(gps)>0:
                date = indata[i][0][4:].replace('\n', '').split(sep = '-')
                if gps[-1]['Time'][0] != 0:
                    gps[-1]['Time'] = np.zeros((6))
                gps[-1]['Time'][0] = float(date[2])
                gps[-1]['Time'][1] = float(date[1])
                gps[-1]['Time'][2] = float(date[0])
                
            elif '--TM' in indata[i][0] and len(gps)>0:
                tm = indata[i][0][4:].replace('\n', '').split(sep = ':')
#                if gps[-1]['Time'][3] != 0:
#                    gps[-1]['Time'] = np.zeros((6))
                gps[-1]['Time'][3] = float(tm[0])
                gps[-1]['Time'][4] = float(tm[1])
                gps[-1]['Time'][5] = float(tm[2])
                
            elif indata[i][0] == 'G0' and len(gps)>0:
                ri = rw5readline(indata[i], ['Base ID read at rover: ', '(Average) - Base ID read at rover: ',], ['str', 'str'])
                bpid = [ri['Base ID read at rover: '], ri['(Average) - Base ID read at rover: ']]
                if bpid[0] == None and bpid[1] != None:
                    try:
                        gps[-1]['BPid'] = int(bpid[1])
                    except ValueError:
                        print('Error converting BP id at point %s' %(gps[-1]['Name']))
                elif bpid[1] == None and bpid[0] != None:
                    try:
                        gps[-1]['BPid'] = int(bpid[0])
                    except ValueError:
                        print('Error converting BP id at point %s' %(gps[-1]['Name']))
                else:
                    gps[-1]['BPid'] = ''
                gps[-1]['BProw'] = len(bp) - 1
#                try:
#                    idx = [r['ID'] for r in bp].index(bpid[1])
#                    gps[-1]['BPname'] = bp[idx]['Name']
#                except ValueError:
#                    pass         
                gps[-1]['GPSTime'] = np.float_(re.split('/|:| ', indata[i][1]))
                
            elif indata[i][0] == 'G1' and len(gps)>0:
                # bpi =  gps[-1]['BPname']
                ri = rw5readline(indata[i], ['BP', 'DX', 'DY', 'DZ'], ['str', 'float', 'float', 'float'])
                gps[-1]['BPnameraw'] = ri['BP']
                gps[-1]['DXraw'] = ri['DX']
                gps[-1]['DYraw'] = ri['DY']
                gps[-1]['DZraw'] = ri['DZ']
#                if type(gps[-1]['BPname'])==float:
#                    if np.isnan(gps[-1]['BPname']):
#                        gps[-1]['BPname'] = bpi
#                if gps[-1]['BPname']=='':
#                    gps[-1]['BPname'] = bpi
                
            elif indata[i][0] == 'G2' and len(gps)>0:
                ri = rw5readline(indata[i], ['VX', 'VY', 'VZ'], ['float', 'float', 'float'])
                gps[-1]['Cxxraw'][0] = ri['VX']
                gps[-1]['Cxxraw'][3] = ri['VY']
                gps[-1]['Cxxraw'][5] = ri['VZ']
                
            elif indata[i][0] == 'G3' and len(gps)>0:
                ri = rw5readline(indata[i], ['XY', 'XZ', 'YZ'], ['float', 'float', 'float'])
                gps[-1]['Cxxraw'][1] = ri['XY']
                gps[-1]['Cxxraw'][2] = ri['XZ']
                gps[-1]['Cxxraw'][4] = ri['YZ']
            
            elif '--GT' in indata[i][0] and len(gps)>0:
                ri = rw5readline(indata[i], ['SW', 'ST', 'EW', 'ET'], ['float', 'float', 'float', 'float'])
                gps[-1]['GPSTimeraw'] = [ri['SW'], ri['ST'], ri['EW'], ri['ET']]
                
            elif '--HSDV:' in indata[i][0]:
                # gps[-1][24:34] = 
                ri = rw5readline(indata[i],\
                   [' ESDV:', ' NSDV:', ' VSDV:', ' STATUS:', ' SATS:', ' HDOP:', ' VDOP:', ' PDOP:', ' TDOP:', ' GDOP:'], \
                   ['float', 'float', 'float', 'str', 'int', 'float', 'float', 'float', 'float', 'float'])
                if ri[' ESDV:'] != None:
                    gps[-1]['ESDV'] = ri[' ESDV:']
                if ri[' NSDV:'] != None:
                    gps[-1]['NSDV'] = ri[' NSDV:']
                if ri[' VSDV:'] != None:
                    gps[-1]['VSDV'] = ri[' VSDV:']
                if ri[' STATUS:'] != None:
                    gps[-1]['STATUSfull'] = ri[' STATUS:'] 
                    if 'fixed' in  gps[-1]['STATUSfull'].lower():
                        gps[-1]['STATUS'] = 'FIXED'
                    else:
                        gps[-1]['STATUS'] = gps[-1]['STATUSfull'] 
                if ri[' SATS:'] != None:
                    gps[-1]['SATS'] = ri[' SATS:']
                if ri[' HDOP:'] != None:
                    gps[-1]['HDOP'] = ri[' HDOP:']
                if ri[' VDOP:'] != None:
                    gps[-1]['VDOP'] = ri[' VDOP:'] 
                if ri[' PDOP:'] != None:
                    gps[-1]['PDOP'] = ri[' PDOP:']  
                if ri[' TDOP:'] != None:
                    gps[-1]['TDOP'] = ri[' TDOP:'] 
                if ri[' GDOP:'] != None:
                    gps[-1]['GDOP'] = ri[' GDOP:']
                    
            elif '--ERMS' in indata[i][0] and len(gps)>0:
                gps[-1]['ESDV'] = float(indata[i][0].split()[2])
                
            elif '--NRMS' in indata[i][0] and len(gps)>0:
                gps[-1]['NSDV'] = float(indata[i][0].split()[2])
                
            elif '--VSDV' in indata[i][0] and len(gps)>0:
                gps[-1]['VSDV'] = float(indata[i][0].split()[2])
                
            elif '--Fixed Readings' in indata[i][0] and len(gps)>0:
                gps[-1]['STATUSfull'] = indata[i][0][2:].replace('\n', '')
                if 'fixed' in  gps[-1]['STATUSfull'].lower():
                    gps[-1]['STATUS'] = 'FIXED'
                else:
                    gps[-1]['STATUS'] = gps[-1]['STATUSfull']
                fixedEpochs = re.findall('\d+', indata[i][0])
                if len(fixedEpochs) == 2:               
                    gps[-1]['FixedEpochs'] = [int(el) for el in fixedEpochs]
                
            elif '--Number of Satellites' in indata[i][0] and len(gps)>0:
                gps[-1]['SATS'] = int(indata[i][0].split()[4])
                
            elif '--HDOP' in indata[i][0] and len(gps)>0:
                gps[-1]['HDOP'] = float(indata[i][0].split()[2])
                
            elif '--VDOP' in indata[i][0] and len(gps)>0:
                gps[-1]['VDOP'] = float(indata[i][0].split()[2])
                
            elif '--PDOP' in indata[i][0] and len(gps)>0:
                gps[-1]['PDOP'] = float(indata[i][0].split()[2])
                
            elif '--Depth Measurement Quality:' in indata[i][0] and len(gps)>0: # in case of depth measurement replace the description!!
                gps[-1]['Depth quality'] = float(indata[i][0].split()[3]) 
    # store the covariance matrices in terms of E, N, h coordinates and correctly
    # scale the Cxx matrix. The rescaling operation is performed according to
    # ESDV, NSDV and HSDV, since it is possible that the SD stored directly by 
    # the receiver and variances in Cxx could be not coherent.
    #
    # Assuming:
    # - Cxx, the covariance matrix in terms of X, Y, Z or np.nan f it is not stored
    # - ESDV, NSDV, HSDV the standard deviation given by the instruments;
    #
    # a. When the Cxx matrix has been stored, the rescaling algorithm is
    #    1.  compute Cee (applying Cxx2Cee), obtaining a matrix with shape
    #        Cee = | sig_e^2 sig_en  sig_eh  |
    #              | sig_en  sig_n^2 sig_nh  | 
    #              | sig_eh  sig_nh  sig_h^2 |
    #
    #    2.  rho_en = sig_en / (sig_e * sig_n)
    #        rho_eh = sig_eh / (sig_e * sig_h)
    #        rho_nh = sig_nh / (sig_n * sig_h)
    #
    #    3.   Cee = | ESDV^2              rho_en*(ESDV*NSDV)  rho_eh*(ESDV*HSDV)  |
    #               | rho_en*(ESDV*NSDV)  NSDV^2              rho_nh*(NSDV*HSDV)  | 
    #               | rho_eh*(ESDV*HSDV)  rho_nh*(NSDV*HSDV)  HSDV^2              |
    #
    # b. When the Cxx is not present (has been identified as nan), the covariance
    #    matrix is assumed to be diagonal:
    #     1.    Cee = | ESDV^2  0      0     |
    #                 | 0       NSDV^2 0     | 
    #                 | 0       0      HSDV^2|
    #
    # Finally:
    # c.    Cxx is computed by means of covariance propagation law (using Cee2Cxx)
    
    # extract the Cxx covariance matrices
    Cxx = [np.array([[gps[i]['Cxxraw'][0], gps[i]['Cxxraw'][1], gps[i]['Cxxraw'][2]], \
                     [gps[i]['Cxxraw'][1], gps[i]['Cxxraw'][3], gps[i]['Cxxraw'][4]], \
                     [gps[i]['Cxxraw'][2], gps[i]['Cxxraw'][4], gps[i]['Cxxraw'][5]]]) \
                for i in range(len(gps))]
    # initilize list of Cee covariance matrices
    Cee  = [np.nan] * len(gps) # original matrix
    Cee2 = [np.nan] * len(gps) # corrected matrix
    Cxx2 = [np.nan] * len(gps) # corrected matrix (geocentric coordinates)
    print(range(len(gps)))
    for i in range(len(gps)):
        if np.sum(np.isnan(Cxx[i])) <= 0: # verify if Cxx is present
            # compute Cee covariance matrix
            Cee[i] = gu.Cxx2Cee(Cxx[i], gps[i]['X'], gps[i]['Y'], gps[i]['Z'], a, f)
            if np.isnan(gps[i]['ESDV']) or np.isnan(gps[i]['NSDV']) or np.isnan(gps[i]['VSDV']):
                gps[i]['ESDV'] = np.sqrt(Cee[i][0,0])
                gps[i]['NSDV'] = np.sqrt(Cee[i][1,1])
                gps[i]['VSDV'] = np.sqrt(Cee[i][2,2])
                Cee2[i] = np.copy(Cee[i])
            else:
                # compute correlation coefficient
                rho = [Cee[i][0,1] / np.sqrt(Cee[i][0,0] * Cee[i][1,1]), \
                       Cee[i][0,2] / np.sqrt(Cee[i][0,0] * Cee[i][2,2]), \
                       Cee[i][1,2] / np.sqrt(Cee[i][1,1] * Cee[i][2,2])]
                # rebuilt the covariance matrix based on std and rho
                Cee2[i] = np.array([[gps[i]['ESDV']**2,                   rho[0]*gps[i]['ESDV']*gps[i]['NSDV'], rho[1]*gps[i]['ESDV']*gps[i]['VSDV']],  \
                                   [rho[0]*gps[i]['ESDV']*gps[i]['NSDV'], gps[i]['NSDV']**2,                    rho[2]*gps[i]['NSDV']*gps[i]['VSDV']],  \
                                   [rho[1]*gps[i]['ESDV']*gps[i]['VSDV'], rho[2]*gps[i]['NSDV']*gps[i]['VSDV'], gps[i]['VSDV']**2]])
        else: # otherwise use the standard deviations to build uncorrelated covariance matrix
            Cee[i]  = np.array([[gps[i]['ESDV']**2, 0, 0], [0, gps[i]['NSDV']**2, 0], [0, 0, gps[i]['VSDV']**2]])
            Cee2[i] = np.array([[gps[i]['ESDV']**2, 0, 0], [0, gps[i]['NSDV']**2, 0], [0, 0, gps[i]['VSDV']**2]])
        Cxx2[i] = gu.Cee2Cxx(Cee2[i], gps[i]['X'], gps[i]['Y'], gps[i]['Z'], a, f)
        gps[i]['Cxx'] = np.array([Cxx2[i][0,0], Cxx2[i][0,1], Cxx2[i][0,2], Cxx2[i][1,1], Cxx2[i][1,2], Cxx2[i][2,2]])
        gps[i]['Cee'] = np.array([Cee2[i][0,0], Cee2[i][0,1], Cee2[i][0,2], Cee2[i][1,1], Cee2[i][1,2], Cee2[i][2,2]])
        gps[i]['Ceeraw'] = np.array([Cee[i][0,0], Cee[i][0,1], Cee[i][0,2], Cee[i][1,1], Cee[i][1,2], Cee[i][2,2]])
            
    # recompute DX, DY, DZ to get vectors at ground point
    for i in range(len(gps)):
        try:
            # idx_gps_bp = [bpi['ID'] for bpi in bp].index(gps[i]['BPid'])
            if gps[i]['BProw'] != -1:
                gps[i]['DX'] = gps[i]['X'] - bp[gps[i]['BProw']]['X']
                gps[i]['DY'] = gps[i]['Y'] - bp[gps[i]['BProw']]['Y']
                gps[i]['DZ'] = gps[i]['Z'] - bp[gps[i]['BProw']]['Z']
                gps[i]['BPname'] = bp[gps[i]['BProw']]['Name']
            elif len(bp) > 0:
                gps[i]['DX'] = gps[i]['X'] - bp[0]['X']
                gps[i]['DY'] = gps[i]['Y'] - bp[0]['Y']
                gps[i]['DZ'] = gps[i]['Z'] - bp[0]['Z']
                gps[i]['BPname'] = bp[0]['Name']
        except:
            pass
    
    return gps, bp

def tabulaxlsread(fname):
    '''Read the excel file from Tabula export.
    SYNTAX:
        tsobs, tsstn = tabulaxlsread(fname)
        
    INPUT:
        fname --> string containing the name of the xls file (extension is
                  optional)
    OUTPUT:
        tsobs --> list containing an observation per row. The field order in
                  each row is: Station, Point, hs, Azimut, Zenit, Slope Distance,
                  hp, code, Station number
        tsstn --> list containing the name of the stations. The field order in 
                  each row is: Station number, Station name, hs
    
    v1.0
    Lorenzo Rossi
    2019-01-04
    '''
    # check if the file exist, otherwise add the xls extension
    fname = fileextchecker(fname, ['xls', 'xlsx'])
    # read all the data form the sheet --------------------------------------------
    indata = [[]]
    excel = xlrd.open_workbook(fname)
    sheet_0 = excel.sheet_by_index(0) # Open the first tab

    # scan all rows and columns and load data in all data
    for row_index in range(sheet_0.nrows):
        row= ""
        for col_index in range(sheet_0.ncols):
            value = sheet_0.cell(rowx=row_index,colx=col_index).value             
            row += "{0} ".format(value)
            split_row = row.split()   
        indata.append(split_row)
        
    # reorder the data ------------------------------------------------------------
    # remove useless rows
    for i in range(len(indata)-1, -1, -1):
        if len(indata[i])==0:
            indata.pop(i)
        elif indata[i][0].lower()=='stampe' or indata[i][0].lower()=='libretto' \
        or indata[i][0].lower()=='gruppi' or indata[i][0].lower()=='tabula' \
        or indata[i][0].lower()=='nome' or (indata[i][0].lower()=='punto' and indata[i][1].lower()=='h.p.'):
            indata.pop(i)
    # parsing data
    tsstn = []
    tsobs = []
    nstn = 0
    for i in range(len(indata)):
        if indata[i][0].lower()=='stazione':
            stni = indata[i][1]
            try:
                hsi = float(indata[i][4])
            except:
                hsi = np.nan
            tsstn.append([nstn, stni, hsi])
            nstn  = nstn + 1
        elif nstn > 0:
            pti = indata[i][0]
            try:
                hpi = float(indata[i][1])
            except:
                hpi = np.nan
            try:
                azi = float(indata[i][2].replace(',', '.'))
            except:
                azi = np.nan
            try:
                zni = float(indata[i][3].replace(',', '.'))
            except:
                zni = np.nan
            try:
                dsi = float(indata[i][4].replace(',', '.'))
            except:
                dsi = np.nan
            if len(indata[i]) == 6:
                cdi = indata[i][5]
            else:
                cdi = ''
            tsobs.append([stni, pti, hsi, azi, zni, dsi, hpi, cdi, nstn-1])
    return tsobs, tsstn

def tabulacoordxlsread(fname):
    '''Read the excel file from Tabula export.
    SYNTAX:
        name, x, y, z, code = tabulacoordxlsread(fname)
        
    INPUT:
        fname --> string containing the name of the xls file (extension is
                  optional)
    OUTPUT:
        name --> list of point name
        x    --> list of x coordinates
        y    --> list of x coordinates
        z    --> list of x coordinates
        code --> point code / description
                 
    
    v1.0
    Lorenzo Rossi
    2019-05-08
    '''
    # check if the file exist, otherwise add the xls extension
    fname = fileextchecker(fname, ['xls', 'xlsx'])
    # read all the data form the sheet --------------------------------------------
    indata = []
    coldata = []
    excel = xlrd.open_workbook(fname, formatting_info=True)
    sheet_0 = excel.sheet_by_index(0) # Open the first tab
    
    # scan all rows and columns and load data in all data
    for row_index in range(sheet_0.nrows):
        row= []
        for col_index in range(sheet_0.ncols):
            value = sheet_0.cell(rowx=row_index,colx=col_index).value             
            row.append(value)
            # split_row = row.split()   
        indata.append(row)
        try:
            xf_index = sheet_0.cell_xf_index(row_index, 0)
            xf = excel.xf_list[xf_index]
            font = excel.font_list[xf.font_index]
            if font:
                coldata.append(excel.colour_map.get(font.colour_index))
        except:
            coldata.append((1000,1000,1000))
        
    # reorder the data ------------------------------------------------------------
    # remove useless rows
    for i in range(len(indata)-1, -1, -1):
        if len(indata[i][0])==0:
            indata.pop(i)
            coldata.pop(i)
        elif 'Tabula t pm by TOPOPROGRAM & Service. Tutti i diritti riservati.' in indata[i][0] or \
        (indata[i][0].lower()=='nome' and indata[i][3].lower()=='materializzazione') or \
       'Nome lavoro' in indata[i][0]:
            indata.pop(i)
            coldata.pop(i)
    
    isStation = [np.sum(np.array(ci))>0 for ci in coldata]
    name = [ri[0] for ri in indata]
    code = [ri[3] for ri in indata]
    x = [float(ri[4]) for ri in indata]
    y = [float(ri[5]) for ri in indata]
    z = [float(ri[6]) for ri in indata]
    return name, x, y, z, code, isStation

def mrkread(fname):
    '''Function to read DJI MRK files
    '''
    # check if the file exist, otherwise add the rw5 extension
    fname = fileextchecker(fname, 'mrk')
    
    # open the file and parse each row using , as separator
    fid = open(fname, 'r')
    indata = [re.split(',|\t|[|]|\n', i) for i in fid.readlines()]
    fid.close()
    
    n = len(indata)
    outdata = {'Time': [None] * n, 
               'Name': [None] * n,
               'Lat':  [None] * n,
               'Lon':  [None] * n,
               'Ellh': [None] * n,
               'stdE': [None] * n,
               'stdN': [None] * n,
               'stdV': [None] * n,
               'dE':   [None] * n,
               'dN':   [None] * n,
               'dV':   [None] * n,
               'Qual': [None] * n,
               'Flag': [None] * n}
    
    for i in range(n):
        outdata['Name'][i] = '%03d' % np.float_(indata[i][0])
        outdata['Time'][i] = np.float_(indata[i][1])
        outdata['Lat'][i]  = np.float_(indata[i][9])
        outdata['Lon'][i]  = np.float_(indata[i][11])
        outdata['Ellh'][i] = np.float_(indata[i][13])
        outdata['stdN'][i] = np.float_(indata[i][15])
        outdata['stdE'][i] = np.float_(indata[i][16])
        outdata['stdV'][i] = np.float_(indata[i][17])
        outdata['dN'][i]   = np.float_(indata[i][3])
        outdata['dE'][i]   = np.float_(indata[i][5])
        outdata['dV'][i]   = np.float_(indata[i][7])
        outdata['Qual'][i] = np.float_(indata[i][18])
        outdata['Flag'][i] = indata[i][19]

    return outdata    

# writing functions -----------------------------------------------------------
def ptswrite(fname, xyz, rgb, ins, verbose = 1):
    ''' Function to wirte a PTS point cloud format for Leica Infinity.
     SYNTAX:
               ptswrite(fname, xyz, rgb, ins, verbose)
    
     INPUT:
     - fname   --> name of the pts file
     - xyz     --> coordinates of the point cloud (nparray if concatenate is true,
                   list of nparray if concatenate is false)
     - rgb     --> RGB of the point cloud (nparray if concatenate is true,
                   list of nparray if concatenate is false)
     - ins     --> intensity of the point cloud (nparray if concatenate is true,
                   list of nparray if concatenate is false)
     - verbose --> opt, bool, true = verbose output. If no specified it is
                   assumed true
    
       v1.0
       Lorenzo Rossi
       2018-08-18
   '''
    # check if the file has the pts extension, otherwise add it
    if fname[-4:].lower() != '.pts':
        fname = fname + '.pts'
    
    tin = time.time()  # starting time
    
    fid = open(fname, 'w')
    
    # check on the type of data. List --> multiple PC file, Nparray --> single PC file
    if type(xyz) == list and type(rgb) == list and type(ins) == list: # case list
        if len(xyz) == len(rgb) and len(xyz) == len(ins):    
            if verbose == 1:
                print('Writing %s:' %(fname))
            for i in range(len(xyz)): # loop on all the point clouds
                if xyz[i].shape[0] == rgb[i].shape[0] and xyz[i].shape[0] == ins[i].shape[0]:
                    nData = xyz[i].shape[0]
                    if verbose == 1:
                         print('\tWriting part %d (%d points)...' %(i+1, nData))
                    np.savetxt(fid, np.array([nData]), fmt='%d')
                    np.savetxt(fid, np.column_stack((xyz[i], ins[i], rgb[i])), fmt= '%.4f %.4f %.4f %.0f %.0f %.0f %.0f')
                else:
                    print('\nData dimensions of part %d not coherent!' %(i+1))
            print('File written in %.1f sec' %(time.time() - tin))
        else:
            print('\nData dimensions not coherent!')
    elif type(xyz) == np.ndarray and type(rgb) == np.ndarray and type(ins) == np.ndarray: # case nparray
        if xyz.shape[0] == rgb.shape[0] and xyz.shape[0] == ins.shape[0]:
            if verbose == 1:
                print('Writing %s:' %(fname))
            nData = xyz.shape[0]
            np.savetxt(fid, np.array([nData]), fmt='%d')
            np.savetxt(fid, np.column_stack((xyz, ins, rgb)), fmt= '%.4f %.4f %.4f %.0f %.0f %.0f %.0f')
            print('File written in %.1f sec' %(time.time() - tin))
        else:
            print('\nData dimensions of PC not coherent!')
    else:
        print('\nData type not coherent!')
        
    fid.close()