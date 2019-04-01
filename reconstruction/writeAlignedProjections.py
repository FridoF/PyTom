import mrcfile
import copy
from pylab import imshow, show
from numpy import abs, float32

def writeAlignedProjections(TiltSeries_, weighting=None,
                            lowpassFilter=None, binning=None,verbose=False):
    """write weighted and aligned projections to disk

       @param TiltSeries_: Tilt Series
       @type TiltSeries_: reconstruction.TiltSeries
       @param weighting: weighting (<0: analytical weighting, >1 exact weighting (value corresponds to object diameter in pixel AFTER binning)
       @type weighting: float
       @param lowpassFilter: lowpass filter (in Nyquist)
       @type lowpassFilter: float
       @param binning: binning (default: 1 = no binning). binning=2: 2x2 pixels -> 1 pixel, binning=3: 3x3 pixels -> 1 pixel, etc.

       @author: FF
    """
    import numpy
    from pytom_numpy import vol2npy
    from pytom.basic.files import read_em, write_em
    from pytom.basic.functions import taper_edges
    from pytom.basic.transformations import general_transform2d
    from pytom.basic.fourier import ifft, fft
    from pytom.basic.filter import filter as filterFunction, bandpassFilter
    from pytom.basic.filter import circleFilter, rampFilter, exactFilter, fourierFilterShift
    from pytom_volume import complexRealMult, vol
    import pytom_freqweight
    from pytom.basic.transformations import resize

    if binning:
        imdim = int(float(TiltSeries_._imdim)/float(binning)+.5)
    else:
        imdim = TiltSeries_._imdim

    sliceWidth = imdim

    # pre-determine analytical weighting function and lowpass for speedup
    if (weighting != None) and (weighting < 0):
        w_func = fourierFilterShift(rampFilter( imdim, imdim))

    # design lowpass filter
    if lowpassFilter:
        if lowpassFilter > 1.:
            lowpassFilter = 1.
            print("Warning: lowpassFilter > 1 - set to 1 (=Nyquist)")
        # weighting filter: arguments: (angle, cutoff radius, dimx, dimy,
        lpf = pytom_freqweight.weight(0.0,lowpassFilter*imdim//2, imdim, imdim//2+1,1, lowpassFilter/5.*imdim)
        #lpf = bandpassFilter(volume=vol(imdim, imdim,1),lowestFrequency=0,highestFrequency=int(lowpassFilter*imdim/2),
        #                     bpf=None,smooth=lowpassFilter/5.*imdim,fourierOnly=False)[1]


    tilt_angles = []

    for projection in TiltSeries_._ProjectionList:
        tilt_angles.append( projection._tiltAngle )
    tilt_angles = sorted(tilt_angles)

    q = numpy.matrix(abs(numpy.arange(-imdim//2, imdim//2)))

    for (ii,projection) in enumerate(TiltSeries_._ProjectionList):
        if projection._filename.split('.')[-1] == 'st':
            from pytom.basic.files import EMHeader, read
            header = EMHeader()
            header.set_dim(x=imdim, y=imdim, z=1)
            idx = projection._index
            if verbose:
                print("reading in projection %d" % idx)
            image = read(file=projection._filename, subregion=[0,0,idx-1,TiltSeries_._imdim,TiltSeries_._imdim,1],
                         sampling=[0,0,0], binning=[0,0,0])
            if not (binning == 1) or (binning == None):
                image = resize(volume=image, factor=1/float(binning))[0]
        else:
            # read projection files
            from pytom.basic.files import EMHeader, read, read_em_header

            image = read(projection._filename)
            image = resize(volume=image, factor=1 / float(binning))[0]

            if projection._filename[-3:] == '.em':
                header = read_em_header(projection._filename)
            else:
                header = EMHeader()
                header.set_dim(x=imdim, y=imdim, z=1)
            '''                
            if ( binning==None or binning==1):
                if projection._filename[-3:] == '.em':
                    (image, header) = read_em(projection._filename)
                else:
                    from pytom.basic.files import read
                    image = read(projection._filename,binning=[binning,binning,1])
            else:
                (image, header) = read_em(projection._filename)
                image = resize(volume=image, factor=1/float(binning))[0]
            '''

        if lowpassFilter:
            filtered = filterFunction( volume=image, filterObject=lpf, fourierOnly=False)
            image = filtered[0]
        
        tiltAngle = projection._tiltAngle
        header.set_tiltangle(tiltAngle)
        # normalize to contrast - subtract mean and norm to mean
        immean = vol2npy(image).mean()
        image = (image - immean)/immean
        print('stats: ', immean, type(immean))
        # smoothen borders to prevent high contrast oscillations
        image = taper_edges(image, imdim//30)[0]
        
        # transform projection according to tilt alignment
        transX = -projection._alignmentTransX / binning
        transY = -projection._alignmentTransY / binning
        rot    = -(projection._alignmentRotation+90.)
        mag    = projection._alignmentMagnification

        if projection._filename.split('.')[-1] == 'st':
            newFilename = (TiltSeries_._alignedTiltSeriesName+"_"+str(projection.getIndex())+'.em')
        else:
            newFilename = (TiltSeries_._alignedTiltSeriesName+"_"+str(projection.getIndex())
                           +'.'+TiltSeries_._tiltSeriesFormat)
        if verbose:
            tline = ("%30s" %newFilename)
            tline = tline + (" (tiltAngle=%6.2f)" % tiltAngle)
            tline = tline + (": transX=%6.1f" %transX)
            tline = tline + (", transY=%6.1f" %transY)
            tline = tline + (", rot=%6.2f" %rot)
            tline = tline + (", mag=%5.4f" %mag)
            print(tline)
            
        image = general_transform2d(v=image, rot=rot, shift=[transX,transY], scale=mag, order=[2, 1, 0], crop=True)
        
        # smoothen once more to avoid edges 
        image = taper_edges(image, imdim//30)[0]
        
        # 'exact weighting, i.e., compute overlap of frequencies in Fourier space
        #if weighting >0:
        #   print("Exact weighting still needs to be ported ... - doing analytical weighting instead")
                #fimage = fftshift(tom_fourier(image));
                ## perform weighting
                #w_func = tom_calc_weight_function([size(image,1), size(image,2)], ...
                #        double([ProjDirResult; Tiltangles]'), weighting, ...
                #    double([ProjDirResult(ii) Tiltangles(ii)]));
        # analytical weighting
        if (weighting != None) and (weighting < 0):
            image = (ifft( complexRealMult( fft( image), w_func) )/
                  (image.sizeX()*image.sizeY()*image.sizeZ()) )
    
        elif (weighting != None) and (weighting > 0):
            #print "Exact weighting for tilt angle =", tiltAngle                                                                     
            w_func = fourierFilterShift(exactFilter(tilt_angles, tiltAngle, imdim, imdim, sliceWidth))
            image = (ifft( complexRealMult( fft( image), w_func) )/
                  (image.sizeX()*image.sizeY()*image.sizeZ()) )

        # write out projs
        #  imt.Header.Tiltaxis=0;
        #imt.Header.Tiltangle = Tiltangle;
        header.set_tiltangle(tilt_angles[ii])

        if newFilename.endswith ('.mrc'):
            data = copy.deepcopy(vol2npy(image))
            mrcfile.new(newFilename,data.T.astype(float32),overwrite=True)
        else:
            write_em(filename=newFilename, data=image, header=header)

        if verbose:
            tline = ("%30s written ..." %newFilename)
        #write_em(filename=fname, data=image)
        #image.write(fname)

