'''
functions underlying 3D reconstruction
Created on Dec 7, 2010

@lastchange: Nov 2015, FF
@author: hrabe, ff
'''

def adjustPickPositionInParticleList(particleList,offsetZ,binning,centerX,centerY,centerZ):
    """
    adjustPickPositionInParticleList:
    @param offsetZ: Z direction distance where the tomogram used for template matching was cut out
    @param binning: Binning factor of tomogram and thus of determined pick positions. Was the tomo 1x binned -> binning = 2^1 = 2 and so forth
    @param centerX: The center coordinate in the original sized tomogram
    @param centerY: The center coordinate in the original sized tomogram
    @param centerZ: The center coordinate in the original sized tomogram
    @return: Particle list with adjusted coordinates, ready for reconstruction   
    """
    
    for particle in particleList:
        
        pickPosition = particle.getPickPosition()
        x = pickPosition.getX()
        y = pickPosition.getY()
        z = pickPosition.getZ()
        
        z = z + offsetZ
        
        x = x * binning - centerX
        y = y * binning - centerY
        z = z * binning - centerZ
        
        pickPosition.setX(x)
        pickPosition.setY(y)
        pickPosition.setZ(z)
        
        particle.setPickPosition(pickPosition)
    
    return particleList
    
        
def positionInProjection(location3D, tiltAngle, tiltAxis='Y'):
    """
    positionInProjection:
    @param location3D: [x,y,z] vector of particle positions in tomogram
    @param tiltAngle: tilt angle
    @type tiltAngle: float
    @param tiltAxis: Set tilt axis of projections. 'Y' is default.
    @type tiltAxis: str
    @return: 2D Position vector [x,y]
    @author: Thomas Hrabe  
    """
    if tiltAxis == 'X':
        from pytom.tools.maths import XRotationMatrix
        rotationMatrix = XRotationMatrix(tiltAngle) 
    elif tiltAxis == 'Y':
        from pytom.tools.maths import YRotationMatrix
        rotationMatrix = YRotationMatrix(tiltAngle)
    elif tiltAxis == 'Z':
        from pytom.tools.maths import ZRotationMatrix
        rotationMatrix = ZRotationMatrix(tiltAngle)

    position2D = rotationMatrix * location3D

    return [position2D[0],position2D[1]]


def positionsInProjections(location3D,tiltStart,tiltIncrement,tiltEnd,tiltAxis='Y'):
    """
    positionsInProjections: Returns 2D positions in projections of a particle according to its 3D location in tomogram  
    @param location3D: 
    @param tiltStart:
    @param tiltIncrement:
    @param tiltEnd:
    @param tiltAxis: Set tilt axis of projections. Y is default.
    @return: List of positions starting with position for projection at tiltStart
    @author: Thomas Hrabe
    """
    positionList = []
    
    for angle in xrange(tiltStart,tiltEnd + tiltIncrement,tiltIncrement): 
        positionList.append(positionInProjection(location3D,angle,tiltAxis))
        
    return positionList


def alignWeightReconstructOld(tiltSeriesName, markerFileName, lastProj, tltfile=None, prexgfile=None, preBin=None,
                           volumeName=None, volumeFileType='em', alignResultFile='',
                           voldims=None, recCent=[0,0,0], tiltSeriesFormat='st', firstProj=1, irefmark=1, ireftilt=1,
                           handflip=False, alignedTiltSeriesName='align/myTilt', weightingType=-1,
                           lowpassFilter=1., projBinning=1, outMarkerFileName=None, verbose=False, outfile='',
                           write_images=True):
    """
    @param tiltSeriesName: Name of tilt series (set of image files in .em or .mrc format) or stack file (ending '.st').\
    Note: the actual file ending should NOT be provided.
    @type tiltSeriesName: str
    @param markerFileName: name of EM markerfile or IMOD wimp File containing marker coordinates
    @type markerFileName: str
    @param lastProj: index of last projection
    @param tltfile: ascii file containing the tilt angles
    @type tltfile: str
    @type lastProj: int
    @param prexgfile: file containing pre-shifts (IMOD way of doing things)
    @type prexgfile: str
    @param preBin: pre-binning in IMOD used for marker determination
    @type preBin: int
    @param volumeName: Filename of volume
    @type volumeName: str
    @param volumeFileType: type of output volume - em or mrc
    @type volumeFileType: str
    @param voldims: dimensions of reconstruction volume, e.g. [512,512,128] - if None chosen only aligned projs are \
    written
    @type voldims: list
    @param recCent: offset from center of volume - for example choose z!=0 to shift in z (post-binning coordinates) - \
    default (0,0,0)
    @type recCent: list
    @param tiltSeriesFormat: file format of tilt series: 'em', 'mrc' or 'st'
    @type tiltSeriesFormat: str
    @param firstProj: index of first projection - default 1
    @type firstProj: int
    @param irefmark: index of reference marker for alignment
    @type irefmark: int
    @param ireftilt: index of reference tilt
    @type ireftilt: int
    @param handflip: add 180 deg to default tilt axis resulting in change of handedness?
    @type handflip: bool
    @param alignedTiltSeriesName: name of ailgned tilt series
    @type alignedTiltSeriesName: str
    @param weightingType: type of weighting - -1 is analytical 'ramp' weighting and 0 is no weighting
    @type weightingType: int
    @param lowpassFilter: lowpass filter in Nyquist
    @type lowpassFilter: float
    @param projBinning: binning of projection (factor rather than power of two!)
    @type projBinning: int or float
    @param outMarkerFileName: filename of output marker file
    @type outMarkerFileName: str
    @param verbose: verbose?
    @type verbose: bool

    @author: FF
    """
    from pytom.reconstruction.TiltAlignmentStructures import TiltSeries, TiltAlignment, TiltAlignmentParameters

    if not alignResultFile:
        if verbose:
            print("Function alignWeightReconstruct started")
            mute = False
        else:
            mute = True
        from pytom.reconstruction.TiltAlignmentStructures import TiltSeries, TiltAlignment, TiltAlignmentParameters
        tiltParas = TiltAlignmentParameters(dmag=True, drot=True, dbeam=False, finealig=True,
                                            finealigfile='xxx.txt', grad=False,
                                            irefmark=irefmark, ireftilt=ireftilt, r=None, cent=[2049, 2049],
                                            handflip=handflip, optimizer='leastsq', maxIter=1000)
        markerFileType = markerFileName.split('.')[-1]
        # align with wimpfile
        if not preBin:
            preBin=1
        if markerFileType == 'wimp':
            if verbose:
                print(" WIMP file used for alignment")
            tiltSeries = TiltSeries(tiltSeriesName=tiltSeriesName, TiltAlignmentParas=tiltParas,
                                    alignedTiltSeriesName=alignedTiltSeriesName,
                                    markerFileName=None, firstProj=firstProj, lastProj=lastProj,
                                    tiltSeriesFormat=tiltSeriesFormat)
            tiltSeries.readIMODwimp(markerFileName=markerFileName, prexgfile=prexgfile, tltfile=tltfile, preBin=preBin,
                                    verbose=False)
        else:
            if verbose:
                print(" EM markerfile file used for alignment")
            tiltSeries = TiltSeries(tiltSeriesName=tiltSeriesName, TiltAlignmentParas=tiltParas,
                                    alignedTiltSeriesName=alignedTiltSeriesName,
                                    markerFileName=markerFileName, firstProj=firstProj, lastProj=lastProj,
                                    tiltSeriesFormat=tiltSeriesFormat)
            if tltfile:
                tiltSeries.getTiltAnglesFromIMODfile(tltfile=tltfile)
        tiltAlignment = TiltAlignment(TiltSeries_=tiltSeries)
        if outMarkerFileName:
            tiltSeries.writeMarkerFile(markerFileName=outMarkerFileName)
            tiltSeries._markerFileName = outMarkerFileName
        tiltAlignment.resetAlignmentCenter()  # overrule cent in Paras
        print(outfile)
        tiltAlignment.computeCoarseAlignment(tiltSeries, mute=mute, outfile=outfile)
        tiltAlignment.alignFromFiducials(mute=mute)
        # creating dir for aligned tilt series if default filename
        if alignedTiltSeriesName == 'align/myTilt':
            from os import mkdir
            try:
                mkdir('align')
            except OSError:
                print(" dir 'align' already exists - writing aligned files into existing dir")

        tiltSeries.write_aligned_projs(weighting=weightingType, lowpassFilter=lowpassFilter, binning=projBinning,
                                       verbose=verbose, write_images=write_images)
        if voldims:
            # overrule tiltSeriesFormat - aligned tiltseries is always a series of em files
            #tiltSeries._tiltSeriesFormat = 'em'
            vol_bp = tiltSeries.reconstructVolume(dims=voldims, reconstructionPosition=recCent, binning=1)

            vol_bp.write(volumeName, volumeFileType)

    else:
        print('new code')
        tiltSeries = TiltSeries(tiltSeriesName=tiltSeriesName)
        vol_bp = tiltSeries.reconstructVolume(dims=voldims, reconstructionPosition=recCent, binning=projBinning,
                                              alignResultFile=alignResultFile)

        vol_bp.write(volumeName, volumeFileType)


def alignWeightReconstruct(tiltSeriesName, markerFileName, lastProj, tltfile=None, prexgfile=None, preBin=None,
                           volumeName=None, volumeFileType='em', alignResultFile='',
                           voldims=None, recCent=[0,0,0], tiltSeriesFormat='st', firstProj=0, irefmark=1, ireftilt=1,
                           handflip=False, alignedTiltSeriesName='align/myTilt', weightingType=-1,
                           lowpassFilter=1., projBinning=1, outMarkerFileName=None, verbose=False, outfile='',
                           write_images=True, shift_markers=True, logfile_residual=''):
    """
    @param tiltSeriesName: Name of tilt series (set of image files in .em or .mrc format) or stack file (ending '.st').\
    Note: the actual file ending should NOT be provided.
    @type tiltSeriesName: str
    @param markerFileName: name of EM markerfile or IMOD wimp File containing marker coordinates
    @type markerFileName: str
    @param lastProj: index of last projection
    @param tltfile: ascii file containing the tilt angles
    @type tltfile: str
    @type lastProj: int
    @param prexgfile: file containing pre-shifts (IMOD way of doing things)
    @type prexgfile: str
    @param preBin: pre-binning in IMOD used for marker determination
    @type preBin: int
    @param volumeName: Filename of volume
    @type volumeName: str
    @param volumeFileType: type of output volume - em or mrc
    @type volumeFileType: str
    @param voldims: dimensions of reconstruction volume, e.g. [512,512,128] - if None chosen only aligned projs are \
    written
    @type voldims: list
    @param recCent: offset from center of volume - for example choose z!=0 to shift in z (post-binning coordinates) - \
    default (0,0,0)
    @type recCent: list
    @param tiltSeriesFormat: file format of tilt series: 'em', 'mrc' or 'st'
    @type tiltSeriesFormat: str
    @param firstProj: index of first projection - default 1
    @type firstProj: int
    @param irefmark: index of reference marker for alignment
    @type irefmark: int
    @param ireftilt: index of reference tilt
    @type ireftilt: int
    @param handflip: add 180 deg to default tilt axis resulting in change of handedness?
    @type handflip: bool
    @param alignedTiltSeriesName: name of ailgned tilt series
    @type alignedTiltSeriesName: str
    @param weightingType: type of weighting - -1 is analytical 'ramp' weighting and 0 is no weighting
    @type weightingType: int
    @param lowpassFilter: lowpass filter in Nyquist
    @type lowpassFilter: float
    @param projBinning: binning of projection (factor rather than power of two!)
    @type projBinning: int or float
    @param outMarkerFileName: filename of output marker file
    @type outMarkerFileName: str
    @param verbose: verbose?
    @type verbose: bool

    @author: FF
    """
    from pytom.reconstruction.TiltAlignmentStructures import TiltSeries, TiltAlignment, TiltAlignmentParameters
    from pytom.gui.guiFunctions import savestar, headerMarkerResults, fmtMR
    import numpy
    if not alignResultFile:
        if verbose:
            print("Function alignWeightReconstruct started")
            mute = False
        else:
            mute = True
        from pytom.reconstruction.TiltAlignmentStructures import TiltSeries, TiltAlignment, TiltAlignmentParameters
        tiltParas = TiltAlignmentParameters(dmag=True, drot=True, dbeam=False, finealig=True,
                                            finealigfile='xxx.txt', grad=False,
                                            irefmark=irefmark, ireftilt=ireftilt, r=None, cent=[2049, 2049],
                                            handflip=handflip, optimizer='leastsq', maxIter=1000)
        markerFileType = markerFileName.split('.')[-1]
        # align with wimpfile
        if not preBin:
            preBin=1
        if markerFileType == 'wimp':
            if verbose:
                print(" WIMP file used for alignment")
            tiltSeries = TiltSeries(tiltSeriesName=tiltSeriesName, TiltAlignmentParas=tiltParas,
                                    alignedTiltSeriesName=alignedTiltSeriesName,
                                    markerFileName=None, firstProj=firstProj, lastProj=lastProj,
                                    tiltSeriesFormat=tiltSeriesFormat)
            tiltSeries.readIMODwimp(markerFileName=markerFileName, prexgfile=prexgfile, tltfile=tltfile, preBin=preBin,
                                    verbose=False)
        else:
            if verbose:
                format = markerFileName.split('.')[-1].upper()
                print(f"{format} markerfile file used for alignment")
            tiltSeries = TiltSeries(tiltSeriesName=tiltSeriesName, TiltAlignmentParas=tiltParas,
                                    alignedTiltSeriesName=alignedTiltSeriesName,
                                    markerFileName=markerFileName, firstProj=firstProj, lastProj=lastProj,
                                    tiltSeriesFormat=tiltSeriesFormat)
            if tltfile:
                tiltSeries.getTiltAnglesFromIMODfile(tltfile=tltfile)
        tiltAlignment = TiltAlignment(TiltSeries_=tiltSeries)
        if outMarkerFileName:
            tiltSeries.writeMarkerFile(markerFileName=outMarkerFileName)
            tiltSeries._markerFileName = outMarkerFileName
        tiltAlignment.resetAlignmentCenter()  # overrule cent in Paras

        tiltAlignment.computeCoarseAlignment(tiltSeries, mute=mute, optimizeShift=shift_markers)
        tiltAlignment.alignFromFiducials(mute=mute, shift_markers=shift_markers,logfile_residual=logfile_residual)

        values = []




        if outfile:
            # Retrieve the index of reference image
            ireftilt = int(numpy.argwhere( tiltAlignment._projIndices.astype(int) == tiltSeries._TiltAlignmentParas.ireftilt)[0][0])

            # for n, i in enumerate(tiltAlignment._projIndices.astype(int)):
            #
            #
            #     print("{:3.0f} {:6.0f} {:6.0f} {:6.0f} {:6.0f}".format(tiltAlignment._tiltAngles[n],
            #           tiltAlignment._Markers[tiltSeries._TiltAlignmentParas.irefmark].xProj[n],
            #           tiltAlignment._Markers[tiltSeries._TiltAlignmentParas.irefmark].yProj[n],
            #           tiltSeries._ProjectionList[int(n)]._alignmentTransX,
            #           tiltSeries._ProjectionList[int(n)]._alignmentTransY))

            # Create center point (3D)
            cent = tiltAlignment.TiltSeries_._TiltAlignmentParas.cent
            cent.append(float(tiltSeries._imdim // 2 + 1))
            print(cent)

            # Create shift
            shift = [tiltSeries._ProjectionList[ireftilt]._alignmentTransX,
                     tiltSeries._ProjectionList[ireftilt]._alignmentTransY, 0]
            print(shift)

            # Retrieve the two relevant angles
            inPlaneAng = tiltAlignment._alignmentRotations[ireftilt]
            tiltAng = tiltAlignment._tiltAngles[ireftilt]

            # Retrieve the original pick position
            xx = tiltAlignment._Markers[tiltSeries._TiltAlignmentParas.irefmark].xProj[ireftilt]
            yy = tiltAlignment._Markers[tiltSeries._TiltAlignmentParas.irefmark].yProj[ireftilt]
            zz = float(tiltSeries._imdim // 2 + 1)

            pickpos = rotate_vector3D([xx,yy,zz], cent, shift, inPlaneAng, tiltAng)

            # Create ref marker point
            ref = tiltAlignment._Markers[tiltSeries._TiltAlignmentParas.irefmark].get_r()
            print(ref)
            ref = rotate_vector3D(ref, [0,0,0], shift, inPlaneAng, tiltAng)
            print(ref)

            for (imark, Marker) in enumerate(tiltAlignment._Markers):
                # reference marker irefmark is fixed to standard value
                r = rotate_vector3D(Marker.get_r(), [0,0,0], shift, inPlaneAng, tiltAng)
                print('in: ', r)
                values.append([imark, r[0]-ref[0], r[1]-ref[1], r[2]-ref[2],
                               pickpos[0]+r[0]-ref[0], pickpos[1]+r[1]-ref[1], pickpos[2]+r[2]-ref[2]])

            savestar(outfile, numpy.array(values), header=headerMarkerResults, fmt=fmtMR)


        # creating dir for aligned tilt series if default filename
        if alignedTiltSeriesName == 'align/myTilt':
            from os import mkdir
            try:
                mkdir('align')
            except OSError:
                print(" dir 'align' already exists - writing aligned files into existing dir")

        tiltSeries.write_aligned_projs(weighting=weightingType, lowpassFilter=lowpassFilter, binning=projBinning,
                                       verbose=verbose, write_images=write_images)
        if voldims:
            # overrule tiltSeriesFormat - aligned tiltseries is always a series of em files
            #tiltSeries._tiltSeriesFormat = 'em'
            vol_bp = tiltSeries.reconstructVolume(dims=voldims, reconstructionPosition=recCent, binning=1)

            vol_bp.write(volumeName, volumeFileType)

    else:
        print('new code')
        tiltSeries = TiltSeries(tiltSeriesName=tiltSeriesName)
        vol_bp = tiltSeries.reconstructVolume(dims=voldims, reconstructionPosition=recCent, binning=projBinning,
                                              alignResultFile=alignResultFile)

        vol_bp.write(volumeName, volumeFileType)


def rotate_vector3D(point3D, centerPoint3D, shift3D, inPlaneRotAngle, tiltAngle):
    from pytom.tools.maths import rotate_vector2d
    from numpy import sin, cos, pi

    newPoint = []

    # Recenter and shift
    for p,c,s in zip(point3D, centerPoint3D, shift3D):
        newPoint.append(p-c-s)

    # In-plane rotation of x and y coordinate
    inPlaneRotAngle = -inPlaneRotAngle-90
    cpsi = cos((inPlaneRotAngle%360) / 180. * pi)
    spsi = sin((inPlaneRotAngle%360) / 180. * pi)
    xmod, ymod = rotate_vector2d(newPoint[:2], cpsi, spsi)
    zmod = newPoint[2]

    print(newPoint, xmod,ymod, inPlaneRotAngle, tiltAngle)

    # In-plane rotation of x and z coordinate over tiltAngle
    sTilt = sin(tiltAngle / 180. * pi)
    cTilt = cos(tiltAngle / 180. * pi)
    xmod,zmod = rotate_vector2d([xmod,zmod], cTilt, sTilt)

    rotatedNewPoint = [xmod, ymod, zmod]

    # Add center
    transformedPoint = []
    for p,c in zip(rotatedNewPoint, centerPoint3D):
        transformedPoint.append(p+c)

    return transformedPoint
