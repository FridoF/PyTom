#!/usr/bin/env pytom

import numpy
import random
import os
import sys
import glob
from pytom.basic.structures import ParticleList, Rotation
from pytom.basic.files import read
from pytom_numpy import vol2npy
from pylab import *
from scipy.spatial.transform import Rotation as R

def get_size(particleList, directory):
    tempPL = ParticleList()
    tempPL.fromXMLFile(particleList)

    tomoName = tempPL[0].getPickPosition().getOriginFilename() if tempPL[0].getPickPosition().getOriginFilename() else tempPL[0].getSourceInfo().getTomoName()

    if not os.path.exists(tomoName):
        tomoName = os.path.join(directory, tomoName)
        if not os.path.exists(tomoName):
            return 'Failed'

    try: dimx,dimy,dimz = vol2npy( read(tomoName) ).copy().shape
    except: return 'Failed'

    return dimx,dimy,dimz

def mirrorParticleList(particleList, outname, directory='./'):
    sizes = get_size(particleList, directory)
    if sizes == 'Failed':
        print('Mirroring particle coordinates did not succeed. Please ensure the paths to the origin tomogram are correct')
        return
    dimx,dimy,dimz = sizes

    tempPL = ParticleList()
    tempPL.fromXMLFile(particleList)
    for particle in tempPL:
        pp = particle.getPickPosition()
        pp.setX(dimx - pp.getX())
        pp.setY(dimy - pp.getY())
        pp.setZ(dimz - pp.getZ())
        shift = particle.getShift()
        shift.invert()
    tempPL.toXMLFile(outname)

def parseChimeraOutputFile(chimeraOutputFile, ref_vector=[0, 0, 1], convention='zxz'):
    import os

    assert os.path.exists(chimeraOutputFile)



    try:
        vec = os.popen(
            "cat " + chimeraOutputFile + " | grep rotation_axis | head -1 | awk '{print $5, $4, $3}'").read()[:-1]
        rotation_vector = [float(line) for line in vec.split(',') if line]
        rotation_vector[0] *= -1
        rotation_vector[1] *= -1
        rotation_vector[2] *= -1

        rot = os.popen("cat " + chimeraOutputFile + " | grep rotation_angle | head -1 | awk '{print $2}'").read()[:-1]
        rotation_angle = float(rot.replace(',', ''))
        r = R.from_rotvec((numpy.array(rotation_vector)))  # -numpy.array(ref_vector)))
        z1, x, z2 = r.as_euler("zxz", degrees=True)
    except:
        raise Exception('Parsing chimera file failed.')

    print(z2, x, z1, rotation_angle)
    return z1 - rotation_angle, x, z2

def updatePL(fnames, outnames, directory='', suffix='', wedgeangles=[], multiplyshift=0,
             new_center=[], sizeSubtomo=64, move_shift=False, binSubtomo=1, binRecon=1, rotation=[],
             anglelist='', mirror=False,  tomogram_dir='./', convention='zxz'):
    if type(fnames) == str:
        fnames = [fnames]
    if type(outnames) == str:
        outnames = [outnames]

    try: wedgelen = len(wedgeangles)
    except: wedgelen = 0

    for n, xmlfile in enumerate(fnames):
        tempPL = ParticleList()
        tempPL.fromXMLFile(xmlfile)

        for particle in tempPL:

            # Update directory to particle
            if directory:
                filename = os.path.join(directory, os.path.basename(particle.getFilename()))
                particle.setFilename(filename)

            # Add suffix to directory name in which particle is stored
            # e.g. suffix = _bin3
            #  --> Subtomograms/tomogram_000/particle_1.em will become Subtomograms/tomogram_000_bin3/particle_1.em
            if suffix:
                filename = particle.getFilename()
                filename = os.path.join( os.path.dirname(filename) + suffix, os.path.basename(filename))
                particle.setFilename(filename)

            # Update wedge angles of angle1 and angle2
            if wedgelen >  n + 1:
                w = particle.getWedge()
                w.setWedgeAngles(wedgeangles[n*2:n*2+2])

            # Shift is multiply by the respective binning factor.
            if multiplyshift:
                shift = particle.getShift()
                shift.scale(multiplyshift)


            # Randomize the angles of all particles in particle list.
            if type(anglelist) == type(numpy.array([])):
                cc = 180. / numpy.pi
                import random
                z1, z2, x = random.choice(anglelist)
                particle.setRotation(rotation=Rotation(z1=z1 * cc, z2=z2 * cc, x=x * cc, paradigm='ZXZ'))

            shift = particle.getShift()
            angles = particle.getRotation().toVector(convention=convention)
            rot_particleList = R.from_euler(convention, angles, degrees=True)

            if new_center:
                new_center_vector = numpy.array(new_center) - sizeSubtomo//2
                print(new_center_vector)
                new_center_vector_rotated = rot_particleList.apply(new_center_vector)
                print(new_center_vector_rotated)
                shift.addVector( new_center_vector_rotated)
                print(shift)
            if move_shift == True:
                pp = particle.getPickPosition()
                shift.scale( binSubtomo / binRecon)
                pp + shift.toVector()
                shift.scale(0.)

            # Combine rotations from particleList and rotation
            if rotation:
                rot_rotation = R.from_euler(convention, rotation, degrees=True)
                combined_rotation = rot_particleList * rot_rotation
                z1, x, z2 = combined_rotation.as_euler(convention, degrees=True)
                particle.setRotation(rotation=Rotation(z1=z1, z2=z2, x=x, paradigm='ZXZ'))


        tempPL.toXMLFile(outnames[n])
        if mirror: mirrorParticleList(outnames[n], outnames[n], directory=tomogram_dir)

if __name__ == '__main__':
    import sys
    from pytom.tools.script_helper import ScriptHelper, ScriptOption
    from pytom.tools.parse_script_options import parse_script_options
    from pytom.basic.structures import ParticleList

    options = [ScriptOption(['-o', '--outputName'], 'Output name of xml', True, False),
               ScriptOption(['-f', '--fileName'], 'particleList filesname.', True, False),
               ScriptOption(['-s', '--suffix'], 'Suffix placed behind last dirname before particle_??.em.', True, False),
               ScriptOption(['-d', '--subtomoDirectory'], 'Update directory of subtomogram reconstructions. If "particle_" is included in name, only dirname before prefix is considered', True, True),
               ScriptOption(['-w', '--wedgeAngles'],'Wedge angles for all particles. if one angle is given, both angles are updated with this angle.', True, True),
               ScriptOption(['-a', '--rotatePL'], 'Rotate the particle list according to either chimera output file or three euler angles (separated by ,).', True,True),
               ScriptOption(['-i', '--shiftToPickPos'], 'move the shift to pick position. The parameter sypplied is the binning factor to go from shift to pick position.'),
               ScriptOption(['-h', '--help'], 'Help.', False, True)]

    helper = ScriptHelper(sys.argv[0].split('/')[-1], # script name
                          description='Update paramters in a particle list.',
                          authors='Gijs van der Schot',
                          options=options)

    if len(sys.argv) == 1:
        print(helper)
        sys.exit()

    try:
        outname, XMLfnames, suffix, prefix, wedgeangles, rotate, shiftBin, help = parse_script_options(sys.argv[1:], helper)
    except Exception as e:
        print(e)
        sys.exit()

    if help is True:
        print(helper)
        sys.exit()

    fnames = []

    if wedgeangles:
        wedgeangles = wedgeangles.split(',')
        if len(wedgeangles) %2:
            wedgeangles = wedgeangles+[wedgeangles[-1]]
    else:
        wedgeangles= []

    try:
        wedgeangles = list(map(float,wedgeangles))
    except Exception as e:
        print("Wedge Angle Error: ", e)
        sys.exit()

    if suffix:
        if not suffix.startswith('_'): suffix = '_'+suffix
    else:
        suffix=''

    if prefix: directory = prefix.split('/particle_')[0]
    else: directory=''
    if XMLfnames:
        print(XMLfnames)
        fnames = XMLfnames.split(',' )

    try:
        if rotate and os.path.exists(rotate):
            chimeraFName = rotate
        elif rotate != None:
            z1,x,z2 = list(map(float,rotate.split(',')))
        else:
            z1,x,z2 = 0,0,0
    except Exception as e:
        print('rotateError: ', e)
        #sys.exit()

    try:
        binningFactorRecon = float(shiftBin)
        binningFactorSubtomo = 1
    except Exception as e:
        print('binning factor error: ', e)



    updatePL(fnames, outname, directory=directory, wedgeangles=wedgeangles, suffix=suffix)

    print('Success: Particle List updated!')

