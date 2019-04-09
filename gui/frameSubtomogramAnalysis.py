import sys
import os
import random
import glob
import numpy
import time

from multiprocessing import Manager, Event, Process
from ftplib import FTP_TLS, FTP
from os.path import dirname, basename

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets

from pytom.gui.guiStyleSheets import *
from pytom.gui.guiSupportCommands import *
from pytom.gui.guiStructures import *
from pytom.gui.fiducialAssignment import FiducialAssignment
from pytom.gui.guiFunctions import avail_gpu
import pytom.gui.guiFunctions as guiFunctions

class SubtomoAnalysis(GuiTabWidget):
    '''Collect Preprocess Widget'''
    def __init__(self, parent=None):
        super(SubtomoAnalysis, self).__init__(parent)
        self.stage          = 'v04_'
        self.pytompath      = self.parent().pytompath
        self.projectname    = self.parent().projectname
        self.subtomodir     = self.parent().subtomo_folder
        self.frmdir         = os.path.join(self.subtomodir,'Alignment/FRM')
        self.glocaldir      = os.path.join(self.subtomodir, 'GLocal/FRM')
        self.cpcadir        = os.path.join(self.subtomodir, 'Classification/CPCA')
        self.acdir          = os.path.join(self.subtomodir, 'Classification/AutoFocus')
        self.pickpartdir    = self.parent().particlepick_folder+'/Picked_Particles'

        headers = ["Reconstruct Subtomograms","Align Subtomograms","Classify Subtomograms"]
        subheaders = [['Single Reconstruction','Batch Reconstruction'],['FRM Alignment','GLocal'],['CPCA','Auto Focus']]

        self.addTabs(headers=headers,widget=GuiTabWidget, subheaders=subheaders)

        self.widgets = {}
        self.table_layouts = {}
        self.tables = {}
        self.pbs = {}
        self.ends = {}

        self.tabs = {'tab11': self.tab11, 'tab12': self.tab12,
                     'tab21': self.tab21, 'tab22': self.tab22,
                     'tab31': self.tab31, 'tab32': self.tab32,}

        self.tab_actions = {'tab11': self.tab11UI, 'tab12': self.tab12UI,
                            'tab21': self.tab21UI, 'tab22': self.tab22UI,
                            'tab31': self.tab31UI, 'tab32': self.tab32UI}

        for i in range(len(headers)):
            t = 'tab{}'.format(i + 1)
            empty = 1 * (len(subheaders[i]) == 0)
            for j in range(len(subheaders[i]) + empty):
                tt = t + str(j + 1) * (1 - empty)
                if tt in ('tab11', 'tab21', 'tab22', 'tab31', 'tab32'):
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

                if tt in ('tab12'):
                    self.table_layouts[tt].addWidget(button)
                    self.table_layouts[tt].addWidget(self.ends[tt])

                if not tt in ('tab12'):
                    self.tab_actions[tt]()

                tab = self.tabs[tt]
                tab.setLayout(self.table_layouts[tt])

    def tab11UI(self):
        key = 'tab11'
        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        t0 = self.stage + 'SingleReconstruction_'

        items += list(self.create_expandable_group(self.createSubtomograms, self.sizePolicyB, 'Single Reconstruction',
                                                   mode=t0))
        items[-1].setVisible(False)

        for n, item in enumerate(items):
            grid.addWidget(item, n, 0, 1, 3)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n + 1, 0, Qt.AlignRight)

    def tab12UI(self):
        try: self.extractLists.text()
        except: self.extractLists = QLineEdit()

        self.b = SelectFiles(self, initdir=self.projectname, search='file', filter=['.xml'], outputline=self.extractLists)
        pass

    def tab21UI(self):
        key = 'tab21'
        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        t0, t1, t2 =  self.stage + 'inputFiles_', self.stage + 'frmSetttings_',self.stage + 'sampleInformation_'

        items += list(self.create_expandable_group(self.inputFiles, self.sizePolicyB, 'FRM Alignment',
                                                   mode=t0))
        items[-1].setVisible(False)


        for n, item in enumerate(items):
            grid.addWidget(item, n, 0,1,4)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n + 1, 0, Qt.AlignRight)

    def tab22UI(self):
        key = 'tab22'

        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        items += list(self.create_expandable_group(self.glocal, self.sizePolicyB, 'GLocal Alignment',
                                                   mode=self.stage + 'gLocal_'))
        items[-1].setVisible(False)
        # items += list( self.create_expandable_group(self.createSubtomograms, self.sizePolicyB, 'Extract Subtomograms',
        #                                            mode=self.stage+'extract_') )
        # items[-1].setVisible(False)

        for n, item in enumerate(items):
            grid.addWidget(item, n, 0)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n + 1, 0, Qt.AlignRight)

    def tab31UI(self):
        key = 'tab31'
        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        t0, t1 = self.stage + 'CCC_', self.stage + 'CPCA_'

        items += list(self.create_expandable_group(self.CCC, self.sizePolicyB, 'Pairwise Cross Correlation',
                                                   mode=t0))
        items[-1].setVisible(False)

        items += list(self.create_expandable_group(self.CPCA, self.sizePolicyB, 'CPCA',
                                                   mode=t1))
        items[-1].setVisible(False)
        # items += list(self.create_expandable_group(self.sampleInformation, self.sizePolicyB, 'Sample Information',
        #                                           mode=t2))
        # items[-1].setVisible(False)

        for n, item in enumerate(items):
            grid.addWidget(item, n, 0, 1, 3)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n + 1, 0, Qt.AlignRight)

    def tab32UI(self):
        key = 'tab32'
        grid = self.table_layouts[key]
        grid.setAlignment(self, Qt.AlignTop)

        items = []

        t0, t1 = self.stage + 'AC_', self.stage + 'CPCA_'

        items += list(self.create_expandable_group(self.ac, self.sizePolicyB, 'Autofocussed Classification',
                                                   mode=t0))
        items[-1].setVisible(False)

        for n, item in enumerate(items):
            grid.addWidget(item, n, 0, 1, 3)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        grid.addWidget(label, n + 1, 0, Qt.AlignRight)

    def createSubtomograms(self, mode=''):

        title = "Single Reconstruction"
        tooltip = ''
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        w = 170

        self.insert_label(parent, cstep=1, sizepolicy=self.sizePolicyB)
        self.insert_label_line_push(parent, 'Particle List', mode + 'particlelist',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line_push(parent, 'Folder with aligned tilt images', mode + 'AlignedTiltDir',
                                    'Select the folder with the aligned tilt images.')

        self.insert_label_spinbox(parent, mode + 'BinFactorReconstruction', 'Binning factor used in the reconstruction.',
                                  'Defines the binning factor used in the reconstruction of the tomogram from which'+
                                  'the particles are selected.',
                                  minimum=1,stepsize=1,value=8)

        self.insert_label_spinbox(parent,  mode + 'WeightingFactor', 'Apply Weighting (0/1)',
                                  'Sets the weighting scheme applied to the tilt images.\n'+
                                  '0: no weighting.\n1: ramp filter.', minimum=-5, maximum=5, stepsize=1,value=0)

        self.insert_label_spinbox(parent,mode+'SizeSubtomos', 'Size subtomograms.','Sets the size of the subtomograms.',
                                  minimum=10,maximum=1000,stepsize=1,value=128)

        self.insert_label_spinbox(parent, mode+'BinFactorSubtomos', 'Binning Factor Subtomograms.',
                                  'Sets the binning factor of the subtomograms.',rstep=1,
                                  value=1, stepsize=1,minimum=1)

        self.insert_label_spinbox(parent,  mode + 'OffsetX', 'Offset in x-dimension',
                                  'Has the tomogram been cropped in the x-dimension?\n'+
                                  'If so, add the cropped magnitude as an offset.\nExample: 200 for 200 px cropping'+
                                  ' in the x-dimension.', cstep=-1, rstep=1,
                                  value=0, stepsize=1,minimum=0, maximum=1000)
        self.insert_label_spinbox(parent, mode + 'OffsetY', 'Offset in y-dimension',
                                  'Has the tomogram been cropped in the y-dimension?\n'+
                                  'If so, add the cropped magnitude as an offset.\nExample: 200 for 200 px cropping'+
                                  ' in the y-dimension.', cstep=-1,rstep=1,
                                  value=0, stepsize=1,minimum=0, maximum=1000)
        self.insert_label_spinbox(parent, mode + 'OffsetZ', 'Offset in z-dimension',
                                  'Has the tomogram been cropped in the z-dimension?\n'+
                                  'If so, add the cropped magnitude as an offset.\nExample: 200 for 200 px cropping'+
                                  ' in the z-dimension.', cstep=0, rstep=1,
                                  value=0, stepsize=1, minimum=0, maximum=1000)


        execfilename = os.path.join( self.subtomodir, 'extractSubtomograms.sh')
        paramsSbatch = guiFunctions.createGenericDict(fname='subtomoExtract', folder=self.subtomodir)
        paramsCmd = [mode+'particlelist', mode+'AlignedTiltDir', mode + 'BinFactorReconstruction',
                     mode+'SizeSubtomos', mode+'BinFactorSubtomos', mode+'OffsetX', mode+'OffsetY', mode+'OffsetZ',
                     self.subtomodir, mode+'WeightingFactor', extractParticles]

        self.insert_gen_text_exe(parent, mode, paramsCmd=paramsCmd, exefilename=execfilename,paramsSbatch=paramsSbatch)
        setattr(self, mode + 'gb_inputFiles', groupbox)
        return groupbox

    def populate_batch_create(self):
        self.b.close()
        particleFiles = sorted( self.extractLists.text().split('\n') )
        id='tab12'
        headers = ["Filename particleList", "Reference marker", 'Bin factor recon', 'Weighting', "Size subtomos", "Bin factor subtomos", "Offset X", "Offset Y", "Offset Y"]
        types = ['txt', 'combobox', 'lineedit', 'lineedit', 'lineedit','lineedit', 'lineedit', 'lineedit', 'lineedit']
        a=40
        sizes = [0, 80, 80, a, a, a, a, a, a, a]

        tooltip = ['Name of coordinate files',
                   'Prefix used for subtomograms',
                   'Angle between 90 and the highest tilt angle.',
                   'Angle between -90 and the lowest tilt angle.',
                   'Filename of generate particle list file (xml)','','','','']

        values = []

        for n, particleFile in enumerate( particleFiles ):
            if not particleFile: continue
            #outfolder = os.path.join( self.projectname, '04_Particle_Picking/Picked_Particles' )



            #prefix = 'tomogram_{:03d}'.format(n)
            #fname_plist = 'particleList_{}.xml'.format(prefix)

            values.append( [os.path.basename(particleFile), ['0','1','closest'], 8, 0, 132, 1, 0, 0, 0] )

        self.fill_tab(id, headers, types, values, sizes, tooltip=tooltip)

        pass

    def inputFiles(self, mode=None):
        title = "FRM Alignment"
        tooltip = ''
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)
        #groupbox.setEnabled(True)
        #groupbox.setVisible(True)
        #groupbox.setCheckable(False)

        self.row, self.column = 0, 0
        rows, columns = 40, 20
        self.items = [['', ] * columns, ] * rows

        self.insert_label(parent, cstep=1, sizepolicy=self.sizePolicyB)
        self.insert_label_line_push(parent, 'Particle List', mode + 'particleList', initdir=self.pickpartdir,
                                    tooltip='Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line_push(parent, 'Filename Mask', mode + 'filenameMask', initdir=self.frmdir,
                                    tooltip='Select the mask file.', mode='file',filetype=['em','mrc'],cstep=1,rstep=0)
        self.insert_pushbutton(parent,'Create',rstep=1,cstep=-3,action=self.gen_mask,params=[mode+'filenameMask'])
        self.insert_label_line_push(parent, 'Filename Average', mode + 'filenameAverage',initdir=self.frmdir,
                                    tooltip='Choose a filename for the average of all particles.', mode='file',
                                    filetype=['em','mrc'],cstep=1,rstep=0)
        self.insert_pushbutton(parent, 'Average', rstep=1, cstep=-3, action=self.gen_average,
                               params=[mode + 'particleList', mode + 'filenameAverage', mode + 'outputDir'])

        self.insert_label_line_push(parent, 'Output Directory', mode + 'outputDir',
                                    'Folder in which the output will be written.')
        self.insert_label(parent,rstep=1,cstep=0)
        self.insert_label_spinbox(parent, mode + 'bwMin', 'Min Order Zernike Polynomial',
                                  value=8,minimum=0,stepsize=1,
                                  tooltip='The minimal order of the Zernike polynomial used for spherical harmonics alignment.')
        self.insert_label_spinbox(parent, mode + 'bwMax', 'Max Order Zernike Polynomial',
                                  value=64, minimum=0, stepsize=1,
                                  tooltip='The maximal order of the Zernike polynomial used for spherical harmonics alignment.')
        self.insert_label_spinbox(parent, mode + 'frequency', 'Frequency (px)',
                                  value=8, minimum=0, stepsize=1,
                                  tooltip='The minimal frequency used for reconstruction.')
        self.insert_label_spinbox(parent,  mode + 'maxIterations', 'Maximum Iterations',
                                  value=8, minimum=1, stepsize=1,
                                  tooltip='Sets the maximal number of iterations of alignmment.')
        self.insert_label_spinbox(parent, mode + 'peakOffset', 'Peak Offset',
                                  value=0, minimum=0, stepsize=1,
                                   tooltip='Sets the peak offset.')
        self.insert_label(parent, rstep=1, cstep=0)
        self.insert_label_spinbox(parent,mode+'pixelSize', 'Pixel Size (A)',
                                  wtype=QDoubleSpinBox,minimum=0.1,stepsize=0.1,value=1.75)
        self.insert_label_spinbox(parent,mode+ 'particleDiameter','Particle Diameter (A)',rstep=1,cstep=0,
                                  minimum=10, stepsize=1, value=300, maximum=10000, width=150)

        self.widgets[mode + 'particleList'].textChanged.connect(lambda d, m=mode: self.updateFRM(m))

        rscore = 'False'
        weightedAv = 'False'
        weighting = ''
        binning_mask = '1'
        sphere = 'True'
        ad_res = '0.00'
        fsc = '0.50'

        jobfilename = os.path.join(self.frmdir, 'job_description.xml')
        exefilename = os.path.join(self.frmdir, 'frmAlignment.sh')

        paramsSbatch = guiFunctions.createGenericDict(fname='FRMAlign', folder=self.frmdir)
        paramsJob = [mode+'bwMin',mode+'bwMax',mode+'frequency',mode+'maxIterations', mode+'peakOffset',
                     rscore, weightedAv, mode+'filenameAverage', weighting, mode+'filenameMask', binning_mask, sphere,
                     mode+'pixelSize', mode+'particleDiameter', mode+'particleList', self.frmdir]
        paramsCmd = [ self.subtomodir, self.pytompath, jobfilename, templateFRMSlurm]

        self.insert_gen_text_exe(parent, self.stage, xmlfilename=jobfilename, jobfield=True, exefilename=exefilename,
                                 paramsXML=paramsJob + [templateFRMJob], paramsCmd=paramsCmd,
                                 paramsSbatch=paramsSbatch)

        setattr(self, mode + 'gb_inputFiles', groupbox)
        return groupbox

    def updateFRM(self,mode):
        item = self.widgets[mode + 'particleList'].text()
        if not item:
            return
        folder, ext = os.path.splitext( os.path.basename(item))
        outputDir = os.path.join(self.frmdir, folder.replace('particleList_', ''))
        if not os.path.exists(outputDir): os.mkdir(outputDir)
        self.widgets[mode+'outputDir'].setText(outputDir)

    def gen_average(self, params):
        key_particleList, key_filename_average, key_outputDir = params
        particleList = self.widgets[key_particleList].text()
        if not particleList:
            self.popup_messagebox('Warning', 'Averaging Failed', 'Averaging did not succeed. No particle list selected.')
            return
        folder = self.widgets[key_outputDir].text()
        if not os.path.exists(folder): os.mkdir(folder)
        output_name = os.path.join( folder, 'average.em')
        out = os.popen('cd {}; average.py -p {} -a {} >& /dev/null&'.format(self.subtomodir, particleList, output_name)).read()
        if not os.path.exists(output_name):
            self.popup_messagebox('Warning', 'Averaging Failed',
                                  'Averaging did not succeed, please try again.')
            return
        self.widgets[key_filename_average].setText(output_name)

    def gen_mask(self,params):
        maskfilename = CreateMaskFile(self, maskfname=params[-1])
        maskfilename.show()

    def referenceUpdate(self, mode):
        if self.widgets[mode + 'referenceModel'].text():
            self.widgets['referenceCommand'].setText( "--reference " + self.widgets[mode + 'referenceModel'].text())
        else:
            self.widgets['referenceCommand'].setText("")

    def glocal(self,mode):
        title = "GLocal alignment"
        tooltip = 'Run pytom GLocal routine.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        w = 170

        self.insert_label_line_push(parent, 'Particle List', mode + 'particleList',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line_push(parent, 'Initial reference model', mode + 'referenceModel', mode='file', filetype='xml',
                                    tooltip='Reference : the initial reference - if none provided average of particle list')
        self.widgets[mode + 'referenceModel'].textChanged.connect(lambda dummy,mode=mode: self.referenceUpdate(mode))
        self.widgets['referenceCommand'] = QLineEdit(self)
        self.widgets['referenceCommand'].setVisible(False)
        self.insert_label_line_push(parent, 'Filename Mask', mode + 'filenameMask',mode='file', filetype=['em', 'mrc'],
                                    tooltip='Select the mask file.', cstep=1, rstep=0)
        self.insert_pushbutton(parent, 'Create', rstep=1, cstep=-3, action=self.gen_mask,
                               params=[mode + 'filenameMask'])
        self.insert_label_spinbox(parent, mode + 'numIterations', 'Number of Iterations',
                                  minimum=1, value=4, stepsize=1,
                                  tooltip='Sets the number of iterations.')
        self.insert_label_spinbox(parent, mode + 'pixelSize', 'Pixel Size (A)',
                                  wtype=QDoubleSpinBox, minimum=0.1, value=1.75, stepsize=0.1,
                                  tooltip='Pixelsize in Angstrom ')
        self.insert_label_spinbox(parent, mode+'particleDiameter', 'Particle Diameter (A)',
                                  minimum=10, stepsize=1, value=300, maximum=10000,
                                  rstep=1, cstep=-1, tooltip='Particle diameter in Angstrom.')
        self.insert_label_spinbox(parent, mode + 'binning', 'Binning Factor', rstep=1, cstep=0,
                                  stepsize=1,minimum=1,value=1,
                                  tooltip='Perform binning (downscale) of subvolumes by factor. Default=1.')


        glocalpath = os.path.join(self.subtomodir, 'Alignment/GLocal')
        exefilename = os.path.join(glocalpath, 'GLocal_Alignment.sh')
        paramsSbatch = guiFunctions.createGenericDict(fname='GLocal', folder=glocalpath)
        paramsCmd = [self.subtomodir, self.pytompath, self.pytompath, mode+'particleList', 'referenceCommand',
                     mode+'filenameMask', mode+'numIterations', mode+'pixelSize', mode+'particleDiameter',
                     mode+'binning', glocalpath, templateGLocal]

        self.insert_gen_text_exe(parent, mode, jobfield=False, exefilename=exefilename, paramsCmd=paramsCmd,
                                 paramsSbatch=paramsSbatch)

        setattr(self, mode + 'gb_GLocal', groupbox)
        return groupbox

    def CPCA(self,mode=''):
        title = "Classify CPCA"
        tooltip = 'The CCC is further used for classification. This script computes the eigenvectors of the CCC and projects the data on the first neig eigenvectors. Subsequently, these multidimensional vectors are clustered into nclass groups using a kmeans algorithm.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows

        self.insert_label_line_push(parent, 'Particle List', mode + 'particlelist',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line(parent, 'Output Filename', mode + 'outputFilename',
                               tooltip='Filename for generated XML file that includes the assigned classes for each particle. No full path needed.')
        self.insert_label_line_push(parent, 'CCC File', mode + 'cccFile',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_spinbox(parent, mode + 'numEig', text='Number of Eigenvectors',
                                  value=4, minimum=1, stepsize=1,
                                  tooltip='Sets the number of eigenvectors (corresponding to largest eigenvectors) used for clustering.')
        self.insert_label_spinbox(parent, mode + 'numClasses', 'Number of Classes',
                                  value=4, minimum=1,stepsize=1,
                                  tooltip='Number of classes used for kmeans classification.')

        self.insert_label_line(parent, 'Prefix', mode + 'prefix', rstep=1, cstep=0,
                               tooltip='Root for generated averages of the corresponding classes. The files will be called "Prefix"_iclass.em.')


        exefilename = os.path.join(self.cpcadir, 'CPCA_Classification.sh')
        paramsSbatch = guiFunctions.createGenericDict(fname='CPCA', folder=self.cpcadir)
        paramsCmd = [self.subtomodir, self.pytompath, mode + 'particleList', mode + 'outputFilename',
                     mode + 'cccFile', mode + 'numEig', mode+'numClasses', mode+'prefix',  templateCPCA]

        self.insert_gen_text_exe(parent, mode, jobfield=False, exefilename=exefilename, paramsCmd=paramsCmd,
                                 paramsSbatch=paramsSbatch)

        setattr(self, mode + 'gb_CPCA', groupbox)
        return groupbox

    def CCC(self,mode=''):
        title = "Pairwise Constrained Cross Correlation"
        tooltip = 'Calculate the pairwise constrained cross correlation.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows

        self.insert_label_line_push(parent, 'Particle List', mode + 'particlelist',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line_push(parent, 'Filename Mask', mode + 'filenameMask',mode='file', filetype=['em', 'mrc'],
                                    tooltip='Select the mask file.', cstep=1, rstep=0)
        self.insert_pushbutton(parent, 'Create', rstep=1, cstep=-3, action=self.gen_mask,
                               params=[mode + 'filenameMask'])
        self.insert_label_spinbox(parent, mode + 'lowpass', 'Lowpass (px)',
                                  minimum=0, maximum=1024, stepsize=1, value=0,
                                  tooltip='Frequency of lowpass filter. The lowpass filter is applied to all subtomograms after binning.')
        self.insert_label_spinbox(parent, mode + 'maxIterations', 'Number Of Iterations',
                                  value=10, minimum=1, stepsize=1,
                                  tooltip='Sets the maximal number of iterations of alignmment.')

        self.insert_label_spinbox(parent, mode + 'binning', 'Binning Factor', rstep=1, cstep=0,
                                  minimum=1, stepsize=1, value=1,
                                  tooltip='Perform binning (downscale) of subvolumes by factor. Default=1.')


        self.cpcadir = os.path.join(self.parent().subtomo_folder, 'Classification/CPCA')
        exefilename = os.path.join(self.cpcadir, 'CCC_Classification.sh')
        paramsSbatch = guiFunctions.createGenericDict(fname='CCC_Class', folder=self.cpcadir)
        paramsCmd = [self.subtomodir, self.pytompath, mode + 'particleList', mode + 'filenameMask',
                     mode + 'lowpass', mode + 'binning', templateCCC]

        self.insert_gen_text_exe(parent, mode, jobfield=False, exefilename=exefilename, paramsCmd=paramsCmd,
                                 paramsSbatch=paramsSbatch)

        setattr(self, mode + 'gb_CCC', groupbox)
        return groupbox

    def ac(self,mode):
        title = "Autofocussed Classification"
        tooltip = 'Run autofocussed classification.'
        sizepol = self.sizePolicyB
        groupbox, parent = self.create_groupbox(title, tooltip, sizepol)

        self.row, self.column = 0, 1
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows

        self.insert_label_line_push(parent, 'Particle List', mode + 'particleList',
                                    'Select the particle list.', mode='file', filetype='xml')
        self.insert_label_line_push(parent, 'Focussed Mask', mode + 'filenameMask1', mode='file', filetype=['em', 'mrc'],
                                    tooltip='This mask is used for constraining the calculation of the focused mask. (Optional)', cstep=1, rstep=0)
        self.insert_pushbutton(parent, 'Create', rstep=1, cstep=-3, action=self.gen_mask,
                               params=[mode + 'filenameMask1'])
        self.insert_label_line_push(parent, 'Alignment Mask', mode + 'filenameMask', mode='file', filetype=['em', 'mrc'],
                                    tooltip='This mask is only used for the alignment purpose. Only specify it if the particle list is not aligned.', cstep=1, rstep=0)
        self.insert_pushbutton(parent, 'Create', rstep=1, cstep=-3, action=self.gen_mask,
                               params=[mode + 'filenameMask'])
        self.insert_label_spinbox(parent, mode + 'numClasses', 'Number of Classes', stepsize=1, value=4, minimum=2,
                                  tooltip='Number of classes used for kmeans classification.')
        self.insert_label_spinbox(parent, mode + 'maxIterations', 'Number Of Iterations',stepsize=1,value=10, minimum=1,
                                  tooltip='Sets the maximal number of iterations of alignmment.')
        self.insert_label_spinbox(parent, mode + 'bwMax', 'Max Bandwidth Reconstruction (px)',
                                  minimum=1, maximum=1024, stepsize=1, value=20,
                                  tooltip='The maximal frequency used for reconstruction.')
        self.insert_label_spinbox(parent, mode + 'peakOffset', 'Max Peak Offset', stepsize=1,value=10, minimum=1,
                                  tooltip='Sets the peak offset.')
        self.insert_label_spinbox(parent, mode+'noisePercentage', 'Noise Percentage',
                                  wtype=QDoubleSpinBox, value=0.1, stepsize=.1,
                                  tooltip='Noise percentage (between 0 and 1). If you estimate your dataset contains certain amount of noise outliers, specify it here.')
        self.insert_label_spinbox(parent, mode + 'partDensThresh', 'Particle Density Threshold',
                                  wtype=QDoubleSpinBox, value=0., minimum=-6.0, maximum=6.0, stepsize=.1,
                                  tooltip='Particle density threshold for calculating the difference map (optional, by default 0). Two other most common choise are -2 and 2. -2 means all the values of the subtomogram below the -2 sigma will be used for calculating the difference mask (negative values count). 2 means all the values of the subtomogram above the 2 sigma will be used for calculating the difference mask (positive values count). Finally, 0 means all the values are used for the calculation.')
        self.insert_label_spinbox(parent, mode + 'stdDiffMap', 'STD Threshold Diff Map', rstep=1, cstep=0,
                                  wtype=QDoubleSpinBox, stepsize=.1, minimum=0, maximum=1, value=0.4,
                                  tooltip='STD threshold for the difference map (optional, by default 0.4). This value should be between 0 and 1. 1 means only the place with the peak value will be set to 1 in the difference map (too much discriminative ability). 0 means all the places with the value above the average of STD will be set to 1 (not enough discriminative ability).')


        acpath = os.path.join(self.parent().subtomo_folder, 'Classification/AutoFocus')
        exefilename = os.path.join(acpath, 'AC_Classification.sh')

        paramsSbatch = guiFunctions.createGenericDict(fname='AutoFocus', folder=acpath)

        paramsCmd = [self.subtomodir, self.pytompath, mode + 'particleList', mode + 'filenameMask1', mode + 'filenameMask',
                     mode + 'numClasses', mode + 'bwMax', mode + 'maxIterations', mode + 'peakOffset',
                     mode + 'noisePercentage', mode + 'partDensThresh', mode + 'stdDiffMap', templateAC]

        self.insert_gen_text_exe(parent, mode, jobfield=False, exefilename=exefilename, paramsCmd=paramsCmd,
                                 paramsSbatch=paramsSbatch)

        setattr(self, mode + 'gb_AC', groupbox)
        return groupbox
