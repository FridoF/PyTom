templateXML       = '''<JobDescription Destination="{d[6]}">
  <Volume Filename="{d[0]}"/>
  <Reference Weighting="" File="{d[1]}"/>
  <Mask Filename="{d[2]}" Binning="1" isSphere="True"/>
  <WedgeInfo Angle1="{d[3]}" Angle2="{d[4]}" CutoffRadius="0.0" TiltAxis="custom">
    <Rotation Z1="0.0" Z2="0.0" X="0.0"/>
  </WedgeInfo>
  <Angles Type="FromEMFile" File="{d[5]}"/>
  <Score Type="FLCFScore" Value="-100000000">
    <DistanceFunction Deviation="0.0" Mean="0.0" Filename=""/>
  </Score>
</JobDescription>'''

old = '''
<JobDescription>
  <Volume Filename="{d[0]}">
  </Volume>
  <Reference File="{d[1]}">
  </Reference>
  <Mask Filename="{d[2]}" Binning="1" isSphere="True">
  </Mask>
  <WedgeInfo Angle1="{d[3]}" Angle2="{d[4]}" CutoffRadius="0.0" TiltAxis="custom">
    <Rotation Z1="0.0" Z2="0.0" X="0.0">
    </Rotation>
  </WedgeInfo>
  </Angles>
  <Score Type="FLCFScore" Value="-100000000">
  </Score>
</JobDescription>
 
'''

templateAlignment = '''cd {d[0]}

{d[1]}/bin/pytom {d[1]}/gui/additional/reconstructTomogram.py \\
    --tiltSeriesName sorted/sorted  \\
    --firstIndex {d[2]} \\
    --lastIndex {d[3]} \\
    --referenceIndex {d[4]} \\
    --markerFile alignment/markerfile.em \\
    --referenceMarkerIndex {d[5]} \\
    --projectionTargets alignment/unweighted_unbinned/sorted_aligned \\
    --projectionBinning {d[6]} \\
    --lowpassFilter 0.9 \\
    --tiltSeriesFormat mrc \\
    --weightingType 0 '''

templateWBP       = '''cd {d[0]}

{d[1]}/bin/pytom {d[1]}/gui/additional/reconstructTomogram.py \\
    --tiltSeriesName sorted/sorted \\
    --firstIndex {d[2]} \\
    --lastIndex {d[3]} \\
    --referenceIndex {d[4]} \\
    --markerFile reconstruction/WBP/markerfile.em \\
    --referenceMarkerIndex {d[5]} \\
    --projectionTargets reconstruction/WBP/temp_files_unweighted/sorted_aligned \\
    --projectionBinning {d[6]} \\
    --lowpassFilter 0.9  \\
    --weightingType {d[10]}  \\
    --tomogramFile reconstruction/WBP/{d[7]}_WBP.mrc \\
    --tiltSeriesFormat {d[8]} \\
    --fileType {d[8]}  \\
    --tomogramSizeX {d[9]}  \\
    --tomogramSizeY {d[9]} \\
    --tomogramSizeZ {d[9]} \\
    --reconstructionCenterX 0 \\
    --reconstructionCenterY 0 \\
    --reconstructionCenterZ 0


unlink ../../04_Particle_Picking/Tomograms/{d[7]}_WBP.{d[8]}
ln -s {d[0]}/reconstruction/WBP/{d[7]}_WBP.{d[8]} ../../04_Particle_Picking/Tomograms/{d[7]}_WBP.{d[8]}'''



templateINFR      = '''cd {d[0]}

{d[1]}/bin/pytom {d[1]}/gui/additional/reconstructTomogram.py \\
    --tiltSeriesName reconstruction/INFR/sorted  \\
    --firstIndex {d[2]} \\
    --lastIndex {d[3]} \\
    --referenceIndex {d[4]} \\
    --markerFile reconstruction/INFR/markerfile.em \\
    --referenceMarkerIndex {d[5]} \\
    --projectionTargets reconstruction/INFR/temp_files_unweighted/sorted_aligned \\
    --projectionBinning {d[6]} \\
    --lowpassFilter 0.9 \\
    --weightingType 0 \\
    --tiltSeriesFormat em \\
    --fileType em

unlink ../../04_Particle_Picking/Tomograms/{d[8]}_INFR.em
{d[1]}/bin/pytom {d[7]}/reconstruction/reconstruct_INFR.py -d reconstruction/INFR/temp_files_unweighted/ -o reconstruction/INFR/{d[8]}_INFR.em 
ln -s {d[0]}/reconstruction/INFR/{d[8]}_INFR.em ../../04_Particle_Picking/Tomograms/{d[8]}_INFR.em'''




templateFRMJob    = '''<FRMJob Destination='{d[15]}' BandwidthRange='[{d[0]},{d[1]}]' Frequency='{d[2]}' MaxIterations='{d[3]}' PeakOffset='{d[4]}' RScore='{d[5]}' WeightedAverage='{d[6]}'>
    <Reference PreWedge="" File="{d[7]}" Weighting="{d[8]}"/>
    <Mask Filename="{d[9]}" Binning="{d[10]}" isSphere="{d[11]}"/>
    <SampleInformation PixelSize="{d[12]}" ParticleDiameter="{d[13]}"/>
    <ParticleListLocation Path="{d[14]}"/>
</FRMJob>
'''

templateFRMSlurm  = '''
module unload python3/3.7 pytom/dev/python3

cd {d[0]}

mpiexec --tag-output -n 16 pytom {d[1]}/frm/FRMAlignment.py -j {d[2]} -v

'''

templateGLocal    = '''export PYTHONPATH=/cm/local/apps/cuda/libs/current/pynvml
export PATH=/cm/local/apps/cuda/libs/current/bin:/cm/shared/apps/cuda80/sdk/8.0.61/bin/x86_64/linux/release:/cm/shared/apps/cuda80/toolkit/8.0.61/bin:/cm/shared/apps/utilities/bin:/cm/shared/apps/slurm/17.02.2/sbin:/cm/shared/apps/slurm/17.02.2/bin:/usr/lib64/qt-3.3/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/usr/sbin:/cm/local/apps/environment-modules/3.2.10/bin 

cd {d[0]}

mpirun -n 20 {d[1]}/bin/pytom {d[2]}/bin/GLocalJob.py \\
--particleList {d[3]} \\
--mask {d[5]} \\
--numberIterations {d[6]} \\
--pixelSize {d[7]} \\
--particleDiameter {d[8]} \\
--binning {d[9]}\\ 
--destination ./ \\
--SphericalMask \\
--angleShells 3 \\
--angleIncrement 3.\\
{d[4]}'''

templateCCC       = """. unload_modules_pytomGUI.sh
export PYTHONPATH=/cm/local/apps/cuda/libs/current/pynvml
export PATH=/cm/local/apps/cuda/libs/current/bin:/cm/shared/apps/cuda80/sdk/8.0.61/bin/x86_64/linux/release:/cm/shared/apps/cuda80/toolkit/8.0.61/bin:/cm/shared/apps/utilities/bin:/cm/shared/apps/slurm/17.02.2/sbin:/cm/shared/apps/slurm/17.02.2/bin:/usr/lib64/qt-3.3/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/usr/sbin:/cm/local/apps/environment-modules/3.2.10/bin

cd {d[0]}

mpiexec --tag-output -n 16 {d[1]}/bin/pytom {d[1]}/classification/calculate_correlation_matrix.py -p {d[2]} -m {d[3]} -f {d[4]} -b {d[5]}
"""

templateCPCA      = """export PYTHONPATH=/cm/local/apps/cuda/libs/current/pynvml
export PATH=/cm/local/apps/cuda/libs/current/bin:/cm/shared/apps/cuda80/sdk/8.0.61/bin/x86_64/linux/release:/cm/shared/apps/cuda80/toolkit/8.0.61/bin:/cm/shared/apps/utilities/bin:/cm/shared/apps/slurm/17.02.2/sbin:/cm/shared/apps/slurm/17.02.2/bin:/usr/lib64/qt-3.3/bin:/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/usr/sbin:/cm/local/apps/environment-modules/3.2.10/bin

cd {d[0]}

{d[1]}/bin/pytom {d[1]}/bin/classifyCPCA.py -p {d[2]} -o {d[3]} -c {d[4]} -e {d[5]} -n {d[6]} -a {d[7]}
"""

templateAC        = '''cd {d[0]}

mpirun -c 20 {d[1]}/bin/pytom {d[1]}/classification/auto_focus_classify.py \\
-p {d[2]} \\
-m {d[3]} \\
-c {d[4]} \\
-k {d[5]} \\
-f {d[6]} \\
-i {d[7]} \\
-s {d[8]} \\
-n {d[9]} \\
-g {d[10]}\\
-t {d[11]}\\
'''

templateTM        = '''cd {d[0]}

mpiexec --tag-output -n 16 pytom /cm/shared/apps/pytom/0.971/pytom/bin/localization.py {d[2]} 4 4 1 '''


createParticleList = 'coords2PL.py -c {d[0]}  -s {d[1]} -w {d[2]},{d[3]} -p {d[4]} {d[5]}'

extractParticles = '''cd {d[8]}

reconstructWB.py --particleList {d[0]} \\
--projectionDirectory {d[1]} \\
--coordinateBinning {d[2]} \\
--size {d[3]} \\
--applyWeighting {d[9]} \\
--projBinning {d[4]} \\
--recOffset {d[5]},{d[6]},{d[7]} \\
--metafile {d[10]}'''

multiple_alignment = '''cd {d[0]}

{d[1]}/bin/pytom {d[1]}/gui/additional/multi_tilt_alignment.py \\
--start {d[2]} \\
--end {d[3]} \\
--numberProcesses {d[4]} \\
--tiltSeriesName {d[5]} \\
--markerFile {d[6]} \\
--projectionTargets {d[7]} \\
--tomogramFolder {d[8]} \\
--firstIndex {d[9]} \\
--lastIndex {d[10]} \\
--referenceIndex {d[11]} \\
--weightingType {d[12]} \\
--projIndices \\
--fnames {d[13]}'''

templateExtractCandidates = '''cd {d[0]}

{d[1]}/bin/pytom {d[1]}/bin/extractCandidates.py \\
--jobFile {d[2]} \\
--result {d[3]} \\
--orientation {d[4]} \\
--particleList {d[5]} \\
--particlePath {d[6]} \\
--size {d[7]} \\
--numberCandidates {d[8]} \\
--minimalScoreValue {d[9]}'''

ParamsFileCTFPlotter = '''#
InputStack           {d[0]}
AngleFile            {d[1]}
DefocusFile          {d[2]}
{d[15]}           {d[3]}
AxisAngle            {d[4]}
PixelSize            {d[5]}
ExpectedDefocus      {d[6]}
AngleRange           {d[7]} {d[8]}
Voltage              {d[9]}
SphericalAberration  {d[10]}
AmplitudeContrast    {d[11]}
DefocusTol           200
PSResolution         101
TileSize             256
LeftDefTol           2000.0
RightDefTol          2000.0
FindAstigPhaseCuton  {d[12]} {d[13]} {d[14]}
Offset 0.02
'''

templateCTFPlotter = '''cd {d[0]}

ctfplotter -pa {d[1]}'''

templateCTFCorrection = '''cd {d[0]}

{d[1]}/bin/pytom {d[1]}/gui/ctfCorrection.py \\
-u {d[2]} \\
-c {d[3]} \\
--metafile {d[4]} \\
--gridSpacing {d[5]} \\
--fieldSize {d[6]} \\
--binningFactor {d[7]}'''
