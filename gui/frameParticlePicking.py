import sys
import os
import random
import glob
import numpy
import time


from ftplib import FTP_TLS, FTP
from os.path import dirname, basename
from multiprocessing import Manager, Event, Process

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets

from pytom.gui.guiStyleSheets import *
from pytom.gui.fiducialAssignment import FiducialAssignment
from pytom.gui.guiStructures import * #GuiTabWidget, CommonFunctions, SimpleTable, ParticlePicker, CreateMaskFile, ConvertEM2PDB
from pytom.gui.guiFunctions import avail_gpu
import pytom.gui.guiFunctions as guiFunctions
from pytom.gui.guiSupportCommands import *
from pytom.basic.structures import ParticleList
from pytom.basic.files import read
from copy import deepcopy
from pytom_numpy import vol2npy

def convertCoords2PLold(coordinate_files, particleList_file, subtomoPrefix=None, wedgeAngles=None):
    pl = ParticleList()
    for n, coordinate_file in enumerate(coordinate_files):
        wedgeAngle = wedgeAngles[2*n:2*(n+1)]

        pl.loadCoordinateFile(filename=coordinate_file, name_prefix=subtomoPrefix[n], wedgeAngle=wedgeAngle)
    pl.toXMLFile(particleList_file)

def convertCoords2PL(coordinate_files, particleList_file, subtomoPrefix=None, wedgeAngles=None, angleList=False):
    pl = ParticleList()
    for n, coordinate_file in enumerate(coordinate_files):
        wedgeAngle = wedgeAngles[2*n:2*(n+1)]
        sourceInfo = pl.loadCoordinateFileHeader(coordinate_file)
        pl.loadCoordinateFile(filename=coordinate_file, name_prefix=subtomoPrefix[n], wedgeAngle=wedgeAngle,
                              sourceInfo=sourceInfo)
        try:
            z1, z2, x = random.choice(angleList)
            pl[-1].setRotation(rotation=Rotation(z1=z1, z2=z2, x=x, paradigm='ZXZ'))
        except:
            pass
    pl.toXMLFile(particleList_file)

class ParticlePick(GuiTabWidget):
    '''Collect Preprocess Widget'''
    def __init__(self, parent=None):
        super(ParticlePick, self).__init__(parent)
        self.stage='v03_'
        self.pytompath = self.parent().pytompath
        self.projectname = self.parent().projectname
        self.templatematchfolder = os.path.join( self.projectname, '04_Particle_Picking/Template_Matching' )
        self.pickpartfolder = os.path.join(self.projectname, '04_Particle_Picking/Picked_Particles')
        self.subtomofolder = os.path.join(self.projectname, '05_Subtomogram_Analysis')

        headers = ["Pick Particles","Create Particle List"]
        subheaders  = [['Manual Picking','Template Matching'],['Single','Batch']]
        self.addTabs(headers=headers,widget=GuiTabWidget, subheaders=subheaders)

        self.table_layouts = {}
        self.tables = {}
        self.pbs = {}
        self.ends = {}

        self.tabs = {'tab11': self.tab11, 'tab12': self.tab12,
                     'tab21': self.tab21, 'tab22': self.tab22}

        self.tab_actions = {'tab11': self.tab11UI, 'tab12': self.tab12UI,
                            'tab21': self.tab21UI, 'tab22': self.tab22UI}

        for i in range(len(headers)):
            t = 'tab{}'.format(i + 1)
            empty = 1 * (len(subheaders[i]) == 0)
            for j in range(len(subheaders[i]) + empty):
                tt = t + str(j + 1) * (1 - empty)
                if tt in ('tab11', 'tab12', 'tab21'):
                    self.table_layouts[tt] = QGridLayout()
                else:
                    self.table_layouts[tt] = QVBoxLayout()
                button = QPushButton('Refresh Tab')
                button.setSizePolicy(self.sizePolicyC)
                button.clicked.connect(self.tab_actions[tt])

                self.tables[tt] = QWidget()
                self.pbs[tt] = QWidget()
                self.ends[tt] = QWidget()
                self.ends[tt].setSizePolicy(self.sizePolicyA)

                if tt in ('tab22'):
                    self.table_layouts[tt].addWidget(button)
                    self.table_layouts[tt].addWidget(self.ends[tt])

                if not tt in ('tab22'):
                    self.tab_actions[tt]()

                tab = self.tabs[tt]
                tab.setLayout(self.table_layouts[tt])

    def tab11UI(self):
        key = 'tab11'
        self.no_image = False
        parent = self.table_layouts[key]
        parent.setAlignment(self, Qt.AlignTop)
        mode = self.stage + 'manualpp_'

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows


        self.insert_label_line_push(parent, 'Tomogram', mode + 'tomogramFname',
                                    'Select the particle list.', mode='file', filetype=['mrc','em'],cstep=-1)
        self.insert_pushbutton(parent, 'Pick!', tooltip='Select the folder with the aligned tilt images.',
                               rstep=1, cstep=2, action=self.insert_image, params = [parent])

        self.insert_label(parent, cstep=-self.column, sizepolicy=self.sizePolicyA,rstep=1)
        self.insert_label(parent, cstep=1, rstep=1, sizepolicy=self.sizePolicyB,width=200)

    def insert_image(self,params):
        if self.no_image == False:
            self.partpick = ParticlePicker(self)
            self.partpick.show()
            #params[0].addWidget(self.partpick,self.row+1,0,4,4)

    def tab12UI(self):
        key = 'tab12'

        mode, mode2 = self.stage + 'TemplateMatch_', self.stage+ 'ExtractCandidates_'
        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        items += list(self.create_expandable_group(self.templateMatch, self.sizePolicyB, 'Template Matching',
                                                   mode=mode))
        items[-1].setVisible(False)

        items += list(self.create_expandable_group(self.extractCandidates, self.sizePolicyB, 'Extract Candidates',
                                                   mode=mode2))
        items[-1].setVisible(False)



        for n, item in enumerate(items):
            grid.addWidget(item, n, 0, 1, 3)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n + 1, 0, Qt.AlignRight)

    def templateMatch(self, mode):
        title = "Template Matching"
        tooltip = 'Run pytom template matching routine.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        w=170

        self.ccfolder = os.path.join(self.templatematchfolder,'cross_correlation')

        self.insert_label_line_push(parent, 'Tomogram file', wname=mode+'tomoFname',width=w,
                                    tooltip='Select the tomogram file used for template matching.',
                                    filetype=['em','mrc'], mode='file')
        self.insert_label_line_push(parent, 'Template file', wname=mode + 'templateFname',width=w,
                                    tooltip='Select the tomogram file used for template matching.',
                                    filetype=['em', 'mrc'], mode='file', rstep=0,cstep=1)
        #self.insert_label(parent, 'PDB2EM', cstep=2, alignment=Qt.AlignRight)
        self.insert_pushbutton(parent, 'Create', action=self.pdb2em, params=[mode + 'templateFname', mode], cstep=-3, rstep=1)
        self.insert_label_line_push(parent, 'Mask file', wname=mode+'maskFname',width=w,
                                    tooltip='Select the tomogram file used for template matching.',
                                    filetype=['em', 'mrc'], mode='file',cstep=1,rstep=0)
        #self.insert_label(parent,'Create Mask',cstep=2, alignment=Qt.AlignRight)
        self.insert_pushbutton(parent,'Create',action=self.create_maskfile,params=[mode+'maskFname'],cstep=-3,rstep=1)

        self.insert_label_spinbox(parent, mode + 'Wedge1', 'Wedge Angle1 (degrees)',width=w,
                                  value=30, stepsize=1,minimum=0, maximum=90,
                                  tooltip='Angle between 90 and the highest tilt angle.')
        self.insert_label_spinbox(parent,  mode + 'Wedge2', 'Wedge Angle2 (degrees)',width=w, cstep=-1,
                                  value=30, stepsize=1, minimum=0, maximum=90,
                                  tooltip='Angle between -90 and the lowest tilt angle.')
        self.insert_label_combobox(parent,'Angular Sampling Filename',mode+'angleFname',
                                   labels=os.listdir(os.path.join( self.parent().pytompath, 'gui/angleLists') ),
                                   tooltip='Select the file that describes the angular sampling of the template model',
                                   width=w,cstep=0)

        self.widgets[mode + 'tomoFname'].textChanged.connect(lambda d, m=mode: self.updateTM(m))

        self.execfilenameTM = os.path.join( self.templatematchfolder, 'templateMatch.sh')
        self.xmlfilename  = os.path.join( self.templatematchfolder, 'job.xml')
        self.widgets[mode+'outfolderTM'] = QLineEdit()
        self.widgets[mode + 'outfolderTM'].setText(self.ccfolder)

        paramsSbatch = guiFunctions.createGenericDict()
        paramsSbatch['fname'] = 'TemplateMatching'
        paramsSbatch[ 'folder' ] = self.ccfolder

        self.insert_gen_text_exe(parent, mode, jobfield=True, exefilename=self.execfilenameTM, paramsSbatch=paramsSbatch,
                                 paramsXML=[mode+'tomoFname', mode + 'templateFname', mode+'maskFname', mode + 'Wedge1',
                                            mode + 'Wedge2',mode+'angleFname', mode + 'outfolderTM', templateXML],
                                 paramsCmd=[mode+'outfolderTM', self.pytompath, 'job.xml' ,templateTM],
                                 xmlfilename=self.xmlfilename)

        self.insert_label(parent, cstep=-self.column, sizepolicy=self.sizePolicyA,rstep=1)

        setattr(self, mode + 'gb_TMatch', groupbox)
        return groupbox

    def updateTM(self,mode):
        tomoname = os.path.basename(self.widgets[mode + 'tomoFname'].text())
        if not tomoname: return
        filename, file_extension = os.path.splitext(tomoname)
        if not os.path.exists(os.path.join(self.templatematchfolder, 'cross_correlation', filename)):
            os.mkdir(os.path.join(self.templatematchfolder, 'cross_correlation', filename))
        self.execfilenameTM = os.path.join( self.templatematchfolder, 'cross_correlation', filename, 'templateMatch.sh')
        self.xmlfilename = os.path.join(self.templatematchfolder, 'cross_correlation', filename, 'job.xml')
        self.widgets[mode + 'outfolderTM'].setText(os.path.dirname(self.xmlfilename))

    def extractCandidates(self,mode):
        title = "Extract Candidates"
        tooltip = 'Run pytom extractCandidates.py'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)
        self.row, self.column = 0, 2
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        w=170

        self.insert_label_line_push(parent, 'Job File', wname=mode + 'jobXML', width=w,
                                    tooltip='Localization job XML file.',
                                    filetype='xml', mode='file')
        self.insert_label_line_push(parent, 'Score File', wname=mode + 'scoreFile', width=w,
                                    tooltip='File with score coefficients (score.em).',
                                    filetype=['em','mrc'], mode='file')
        self.insert_label_line_push(parent, 'Angles File', wname=mode + 'anglesFile', width=w,
                                    tooltip='File with orientation indices (angles.em).',
                                    filetype=['em', 'mrc'], mode='file')
        self.insert_label_line_push(parent, 'File Name Particle List', wname=mode + 'particleList', width=w,
                                    tooltip='Select the angles.em file produced by template matching.',
                                    filetype=['xml'], mode='file')
        self.insert_label_line(parent, 'Prefix', mode + 'particlePath', width=w,
                               tooltip='Path prepended to each particle.')

        self.insert_label_spinbox(parent, mode + 'Size', 'Size particle (px)', width=w, cstep=-1,
                                  value=10, stepsize=1, minimum=0, maximum=90,
                                  tooltip='Radius around potential candidate that will be ignored during further processing.')
        self.insert_label_spinbox(parent, mode + 'NumberOfCandidates', 'Number of Candidates', width=w, cstep=-1,
                                  value=1000, stepsize=100, minimum=0, maximum=5000,
                                  tooltip='Number of candidates to extract.')
        self.insert_label_spinbox(parent, mode + 'MinimalScoreValue', 'Minimal Score Value', width=w, cstep=0,
                                  value=0., stepsize=0.1, minimum=0, maximum=1.,wtype=QDoubleSpinBox,
                                  tooltip='Minimal score value to which to extract.')

        self.widgets[mode + 'jobXML'].textChanged.connect(lambda d, m=mode: self.jobXMLChanged(m))
        self.widgets[mode + 'particleList'].textChanged.connect(lambda d, m=mode: self.particleListChanged(m))
        self.jobXMLChanged(mode)


        execfilename = os.path.join( self.templatematchfolder, 'extractCandidates.sh')
        paramsSbatch = guiFunctions.createGenericDict()
        paramsSbatch['fname'] = 'ExtractCandidates'
        paramsSbatch[ 'folder' ] = self.templatematchfolder

        paramsCmd=[self.templatematchfolder, self.pytompath, mode+'jobXML', mode+'scoreFile', mode+'anglesFile',
                   mode+'particleList', mode+'particlePath', mode+'Size', mode+'NumberOfCandidates',
                   mode+'MinimalScoreValue', templateExtractCandidates]

        self.insert_gen_text_exe(parent, mode, jobfield=False, exefilename=execfilename, paramsSbatch=paramsSbatch,
                                 paramsCmd=paramsCmd)

        self.insert_label(parent, cstep=-self.column, sizepolicy=self.sizePolicyA,rstep=1)

        setattr(self, mode + 'gb_TMatch', groupbox)
        return groupbox
        self.insert_label(parent, cstep=-self.column, sizepolicy=self.sizePolicyA,rstep=1)
        setattr(self, mode + 'gb_extractCandidates', groupbox)
        return groupbox

    def jobXMLChanged(self, mode):
        jobXML = self.widgets[mode+'jobXML'].text()
        if not jobXML: return
        folder = os.path.basename(jobXML)[:-4]


        particleList = os.path.join(self.ccfolder, folder, 'particleList_{}.xml'.format(folder))
        if not os.path.exists(os.path.dirname(particleList)): os.mkdir(os.path.dirname(particleList))
        self.widgets[mode + 'particleList'].setText(particleList)

    def particleListChanged(self, mode):
        particleList = self.widgets[mode + 'particleList'].text()
        if not particleList: return
        folder = os.path.basename(particleList)[:-4]
        self.widgets[mode + 'particlePath'].setText('Subtomograms/{}/particle_'.format(folder))

    def create_maskfile(self,params):
        maskfilename = CreateMaskFile(self,maskfname=params[-1])

    def pdb2em(self, params):
        print(params)
        ConvertEM2PDB(self, emfname=params[0],folder=self.widgets[params[1]+'outfolderTM'].text())

    def tab21UI(self):
        key = 'tab21'
        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        items += list( self.create_expandable_group(self.createParticleList, self.sizePolicyB, 'Create Particle List',
                                                    mode=self.stage+'partlist_') )
        items[-1].setVisible(False)
        #items += list( self.create_expandable_group(self.createSubtomograms, self.sizePolicyB, 'Extract Subtomograms',
        #                                            mode=self.stage+'extract_') )
        #items[-1].setVisible(False)

        for n, item in enumerate(items):
            grid.addWidget(item, n, 0)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n+1, 0, Qt.AlignRight)

    def createSubtomograms(self, mode=''):
        title = "Create Subtomograms"
        tooltip = 'Tick this box to extract subtomgorams from a particlelist file.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 0
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows



        self.insert_label(parent, cstep=1, sizepolicy=self.sizePolicyB)
        self.insert_label_line_push(parent, 'Particle List', mode + 'particlelist',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line_push(parent, 'Folder with aligned tilt images', mode + 'AlignedTiltDir',
                                    'Select the folder with the aligned tilt images.')

        self.insert_label_line(parent, 'Binning factor used in the reconstruction.', mode + 'BinFactorReconstruction',
                               'Defines the binning factor used in the reconstruction of the tomogram from which'+
                               'the particles are selected.', validator=QIntValidator(),value=8)

        self.insert_label_line(parent, 'Apply Weighting (0/1)', mode + 'WeightingFactor',
                               'Sets the weighting scheme applied to the tilt images.\n'+
                               '0: no weighting.\n1: ramp filter.', validator=QIntValidator(),value=0)

        self.insert_label_line(parent, 'Size subtomograms.', mode+'SizeSubtomos', 'Sets the size of the subtomograms.',
                               validator=QIntValidator(),value=128)

        self.insert_label_line(parent, 'Binning Factor Subtomograms.', mode+'BinFactorSubtomos',
                               'Sets the binning factor of the subtomograms.',validator=QIntValidator(),rstep=1,
                               value=1)

        self.insert_label_line(parent, 'Offset in x-dimension', mode + 'OffsetX',
                               'Has the tomogram been cropped in the x-dimension?\n'+
                               'If so, add the cropped magnitude as an offset.\nExample: 200 for 200 px cropping'+
                               ' in the x-dimension.', cstep=-1, value='0',validator=QIntValidator(), rstep=1)
        self.insert_label_line(parent, 'Offset in y-dimension', mode + 'OffsetY',
                               'Has the tomogram been cropped in the y-dimension?\n'+
                               'If so, add the cropped magnitude as an offset.\nExample: 200 for 200 px cropping'+
                               ' in the y-dimension.', cstep=-1, value='0',validator=QIntValidator(),rstep=1)
        self.insert_label_line(parent, 'Offset in z-dimension', mode + 'OffsetZ',
                               'Has the tomogram been cropped in the z-dimension?\n'+
                               'If so, add the cropped magnitude as an offset.\nExample: 200 for 200 px cropping'+
                               ' in the z-dimension.', cstep=0, value='0',validator=QIntValidator(),rstep=1)


        self.insert_gen_text_exe(parent, mode, paramsCmd=[mode+'particlelist', mode+'AlignedTiltDir',
                                                          mode + 'BinFactorReconstruction',
                                                          mode+'SizeSubtomos', mode+'BinFactorSubtomos',
                                                          mode+'OffsetX', mode+'OffsetY', mode+'OffsetZ',
                                                          extractParticles])

        setattr(self, mode + 'gb_create_subtomos', groupbox)
        return groupbox

    def createParticleList(self, mode=''):
        title = "Create Particle List"
        tooltip = 'Tick this box to create a particle list from the selected coordinate file.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 2
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows

        self.insert_label(parent, cstep=1, sizepolicy=self.sizePolicyB, width=200)

        self.insert_label_line_push(parent, 'Coordinate File', mode + 'CoordinateFile',mode='file',filetype='txt',
                                    initdir=self.pickpartfolder,
                                    tooltip='Select the coordinate file which contains the x,y,z coordinates of the particles.')

        self.insert_label_line(parent, 'Prefix Subtomograms', mode + 'PrefixSubtomo', value='Subtomograms/',
                               tooltip='Define a prefix that is prepended to the particle name. A unique identifier makes it'+
                               'easier to track the respective particles.')

        self.insert_label_spinbox(parent, mode + 'Wedge1', 'Wedge degrees(positive)',
                               'Angle between 90 and the highest tilt angle.', stepsize=1, value=30, minimum=0, maximum=90)

        self.insert_label_spinbox(parent, mode + 'Wedge2','Wedge degrees(negative)',
                                  'Angle between -90 and the lowest tilt angle.',
                                  stepsize=1,minimum=0,maximum=90,value=30, cstep=-1,rstep=1)

        self.insert_label_line_push(parent, 'Filename particleList', mode+'FnameParticleList', cstep=-2, rstep=1,
                                    pushtext='Browse', width=150, action=self.setFnameParticleList)

        self.insert_label_checkbox(parent, mode+'Randomize', 'Randomize Particle Orientation', cstep=0, rstep=1,
                                   tooltip='Randomize the orientation angles of the particles in the particle list.')

        self.widgets[mode+'flagRandomize'] = QLineEdit()
        self.widgets[mode+'Randomize'].stateChanged.connect(lambda dummy, m=mode: self.update_flag(m) )
        self.widgets[ mode + 'CoordinateFile'].textChanged.connect(lambda d, mm=mode: self.update_prefix_pL(mm))


        execfilename = os.path.join( self.pickpartfolder, 'createParticleList.sh')
        paramsSbatch = guiFunctions.createGenericDict()
        paramsSbatch['fname'] = 'createPrtclLst'
        paramsSbatch[ 'folder' ] = self.pickpartfolder

        paramsCmd=[mode+'CoordinateFile', mode+'PrefixSubtomo', mode+'Wedge1', mode+'Wedge2', mode+'FnameParticleList',
                   mode+'flagRandomize', createParticleList]

        self.insert_gen_text_exe(parent,mode,paramsCmd=paramsCmd, exefilename=execfilename,paramsSbatch=paramsSbatch,
                                 action=self.createFolder,paramsAction=mode)

        setattr(self, mode + 'gb_create_particle_list', groupbox)
        return groupbox

    def createFolder(self,mode):
        prefix=self.widgets[mode+'PrefixSubtomo'].text()
        a = os.path.join(self.subtomofolder, os.path.dirname(prefix))
        if not os.path.exists(a): os.mkdir(a)

    def update_prefix_pL(self, mode):
        coords, prefixS = mode + 'CoordinateFile', mode + 'PrefixSubtomo'
        prefix = os.path.basename(self.widgets[coords].text())[:-4].replace('coords_', '')
        self.widgets[prefixS].setText(os.path.join('Subtomograms', prefix, 'particle_'))
        self.setFnameParticleList(['file',self.widgets[mode + 'FnameParticleList']], ask=False)

    def update_flag(self,mode):
        w1 = self.widgets[mode+'flagRandomize']
        w2 = self.widgets[mode+'Randomize']
        w1.setText(w2.isChecked()*'-r')

    def update_prefix(self,params):
        prefix = os.path.basename(self.widgets[params[0]].text())[:-4].replace('coords_','')
        self.widgets[params[1]].setText( os.path.join('Subtomograms', prefix) )

    def setFnameParticleList(self,params,ask=True):
        t = os.path.basename( self.widgets[ self.stage+'partlist_' + 'CoordinateFile'].text() )
        t = t.replace('coords_','').replace('.txt', '')
        initdir = os.path.join(self.projectname,'04_Particle_Picking/Picked_Particles', 'particleList_{}.xml'.format(t))

        if ask:
            particleListFname = str(QFileDialog.getSaveFileName(self,'Save particle list.', initdir, filter='*.xml')[0])
        else:
            particleListFname = initdir

        if particleListFname:
            if particleListFname.endswith('.xml'): params[1].setText(particleListFname)
            else: params[1].setText('')

    def tab22UI(self):

        try: self.particleLists.text()
        except: self.particleLists = QLineEdit()

        self.b = SelectFiles(self, initdir=self.projectname, search='file', filter=['.txt'], outputline=self.particleLists)

    def populate_batch_create(self):
        self.b.close()
        coordinateFiles = sorted( self.particleLists.text().split('\n') )

        id='tab22'

        headers = ["Filename Coordinate List", "Prefix Subtomograms", 'Wedge Angle 1', 'Wedge Angle 2', "Filename Particle List", 'Randomize Angles']
        types = ['txt', 'lineedit', 'lineedit', 'lineedit', 'lineedit', 'checkbox']
        sizes = [0, 80, 80, 0, 0, 0]


        tooltip = ['Name of coordinate files',
                   'Prefix used for subtomograms',
                   'Angle between 90 and the highest tilt angle.',
                   'Angle between -90 and the lowest tilt angle.',
                   'Filename of generate particle list file (xml)',
                   'Randomize angles in particleList']

        values = []

        for n, coordinateFile in enumerate( coordinateFiles ):
            if not coordinateFile: continue
            outfolder = os.path.join( self.projectname, '04_Particle_Picking/Picked_Particles' )

            try:
                tomogramNUM = int(coordinateFile.split('tomogram_')[-1][:3])
            except:
                tomogramNUM = n


            prefix = 'Subtomograms/{}/particle_'.format(os.path.basename(coordinateFile[:-4]))
            ff = os.path.join(self.subtomofolder,os.path.dirname(prefix))
            if not os.path.exists(ff): os.mkdir(ff)
            fname_plist = 'particleList_{}.xml'.format(os.path.basename(coordinateFile[:-4]))

            values.append( [coordinateFile, prefix, 30, 30, fname_plist, True] )

        self.fill_tab(id, headers, types, values, sizes, tooltip=tooltip)

        self.tab22_widgets = tw = self.tables[id].widgets

        for row in range(self.tables[id].table.rowCount()):
            val = values[row][1]
            widget1 = self.tab22_widgets['widget_{}_{}'.format(row,1)]
            widget2 = self.tab22_widgets['widget_{}_{}'.format(row,4)]
            widget1.textChanged.connect(lambda d, w1=widget1, w2=widget2: self.update_change_tab22_table(w1, w2))

        self.pbs[id].clicked.connect(lambda dummy, pid=id, v=values: self.mass_convert_txt2xml(pid, v))
        pass

    def update_change_tab22_table(self,widget1, widget2):
        widget2.setText('particleList_{}.xml'.format(widget1.text()))

    def mass_convert_txt2xml(self,pid,values):
        fname = str(QFileDialog.getSaveFileName(self, 'Save particle list.', self.pickpartfolder, filter='*.xml')[0])
        if not fname: return
        if not fname.endswith('.xml'):fname+='.xml'

        conf = [[],[],[],[],[]]
        for row in range(self.tables[pid].table.rowCount()):
            if 1:
                c = values[row][0]
                p = self.tab22_widgets['widget_{}_{}'.format(row, 1)].text()
                w1 = float(self.tab22_widgets['widget_{}_{}'.format(row,2)].text() )
                w2 = float(self.tab22_widgets['widget_{}_{}'.format(row,3)].text() )
                pl = self.tab22_widgets['widget_{}_{}'.format(row,4)].text()
                pl = os.path.join(self.pickpartfolder, pl)
                r = self.tab22_widgets['widget_{}_{}'.format(row,5)].isChecked()
                #print(createParticleList.format(d=[c, p, w1, w2, pl]))
                wedge = [w1,w2]
                for n, inp in enumerate((c, pl, p, w1, w2)):
                    if n==4: n=3
                    conf[n].append(inp)
                pFolder = os.path.join(self.subtomofolder, os.path.basename(p))
                if not os.path.exists(pFolder): os.mkdir(pFolder)

                angleList = os.path.join(self.pytompath, 'angles/angleLists/angles_18_3040.em')*r

                if angleList:
                    if not os.path.exists(angleList):
                        raise Exception('Angle List is not existing.')
                        angleList = None
                    elif not angleList.split('.')[-1] in ('em', 'mrc'):
                        raise Exception('File format should be mrc or em.')
                        angleList = None
                    else:
                        vol = read(angleList)
                        angleList = deepcopy(vol2npy(vol)).T.astype(numpy.float32)
                        rotation = random.choice(angleList)
                        if len(rotation) != 3 or type(rotation[0]) != numpy.float32:
                            raise Exception('AngleList should contain three floats per row.')
                            angleList = None

                convertCoords2PL([c], pl, subtomoPrefix=[p], wedgeAngles=wedge, angleList=angleList)
                #os.system(createParticleList.format(d=[c, p, wedge, pl]))

            else:
                print('Writing {} failed.'.format(os.path.basename(fname)))
                return

        convertCoords2PL(conf[0], fname, subtomoPrefix=conf[2], wedgeAngles=conf[3])



