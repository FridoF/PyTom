import sys
import os
import random
import glob
import numpy
import time
import shutil

from os.path import dirname, basename
from ftplib import FTP_TLS, FTP
from multiprocessing import Manager, Event, Process

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, QtWidgets

from pytom.gui.guiStyleSheets import *
from pytom.gui.fiducialAssignment import FiducialAssignment
from pytom.gui.guiStructures import *
from pytom.gui.guiFunctions import avail_gpu, sort
from pytom.gui.guiSupportCommands import *
import pytom.gui.guiFunctions as guiFunctions

class TomographReconstruct(GuiTabWidget):
    '''Collect Preprocess Widget'''
    def __init__(self, parent=None):
        super(TomographReconstruct, self).__init__(parent)


        self.projectname = self.parent().projectname
        self.tomogram_folder = self.parent().tomogram_folder
        self.rawnanographs_folder = self.parent().rawnanographs_folder
        self.motioncor_folder = self.parent().motioncor_folder
        self.widgets = {}

        self.widgets['pytomPath'] = QLineEdit()
        self.widgets['pytomPath'].setText(self.parent().pytompath)

        self.pytompath = self.parent().pytompath
        headers = ["Select Tomograms", "Create Markerfile", "Alignment", 'Reconstruction']
        subheaders = [[], [], ['Individual Alignment', 'Batch Alignment'], ['INFR', 'WBP', 'Batch Reconstruction']]
        self.addTabs(headers=headers, widget=GuiTabWidget, subheaders=subheaders)

        self.table_layouts = {}
        self.tables = {}
        self.pbs = {}
        self.ends = {}

        self.tabs = {'tab1': self.tab1,
                     'tab2':  self.tab2,
                     'tab31': self.tab31, 'tab32': self.tab32,
                     'tab41': self.tab41, 'tab42': self.tab42, 'tab43': self.tab43}

        self.tab_actions = {'tab1':  self.tab1UI,
                            'tab2':  self.tab2UI,
                            'tab31': self.tab31UI, 'tab32': self.tab32UI,
                            'tab41': self.tab41UI, 'tab42': self.tab42UI, 'tab43': self.tab43UI}

        for i in range(len(headers)):
            t = 'tab{}'.format(i+1)
            empty = 1*(len(subheaders[i]) == 0)
            for j in range(len(subheaders[i])+empty):
                tt = t+str(j+1)*(1-empty)
                if tt in ('tab2', 'tab31', 'tab41', 'tab42'):
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

                if tt in ('tab1','tab32','tab43'):
                    self.table_layouts[tt].addWidget(button)
                    self.table_layouts[tt].addWidget(self.ends[tt])

                if tt in ('tab2','tab31','tab41','tab42'):
                    self.tab_actions[tt]()


                tab = self.tabs[tt]
                tab.setLayout(self.table_layouts[tt])
                #self.tab_actions[tt]()

    def startFidAssignment(self,parent=None):
        self.fidass = FiducialAssignment(self)
        self.fidass.show()
        pass

    def fill_tab(self, id, headers, types, values, sizes, tooltip=[],connect=0):
        try:
            self.tables[id].setParent(None)
            self.pbs[id].setParent(None)
            self.ends[id].setParent(None)
        except:
            pass

        self.tables[id] = SimpleTable(headers, types, values, sizes, tooltip=tooltip, connect=connect)
        self.widgets['v02_batch_aligntable{}'.format(id)] = self.tables[id]
        self.pbs[id] = QPushButton('Run')
        self.pbs[id].setSizePolicy(self.sizePolicyC)
        self.ends[id] = QWidget()
        self.ends[id].setSizePolicy(self.sizePolicyA)

        for a in (self.tables[id], self.pbs[id], self.ends[id]):
            self.table_layouts[id].addWidget(a)

    def tab1UI(self):
        id = 'tab1'

        self.filepath_tomodata = {}
        self.filepath_tomodata['Motion Corrected'] = self.motioncor_folder
        self.filepath_tomodata['Raw Nanographs']  = self.rawnanographs_folder

        headers = ["mdoc file", "create", 'pututive name',"input files", 'Name tomogram', 'redo', 'delete']
        types = ['txt', 'checkbox', 'txt', 'combobox', 'txt', 'checkbox', 'checkbox']
        sizes = [0, 80, 500, 0, 200, 80, 80]

        tooltip = ['Name of mdoc files. This file indicates which images belong together, as well as the tiltangles.',
                   'Create new tomogram folders.',
                   'Putative name of tomogram',
                   'Names of existing tomogram folder.',
                   'Redo the creation of a tomogram file.',
                   'Select items to delete tomogram folders.']

        processed = sorted(glob.glob('{}/tomogram_*/sorted/*.mdoc'.format(self.tomogram_folder)))
        processed_fn = [basename(line) for line in processed]
        unprocessed = numpy.array(sorted(glob.glob('{}/*.mdoc'.format(self.rawnanographs_folder))))
        unprocessed = unprocessed[[not (basename(u_item) in processed_fn) for u_item in unprocessed]]

        values = []

        for t in processed:
            values.append([t, False, '', ['Motion Corrected', 'Raw Nanographs'], t.split('/')[-3], True, True])
        for t in unprocessed:
            values.append([t, True, '', ['Raw Nanographs','Motion Corrected'], '', False, False])

        self.fill_tab(id, headers, types, values, sizes, tooltip=tooltip, connect=self.update_create_tomoname)
        #for row in range(self.tables[id].table.rowCount()):

        #   if self.tables[id].table.item(row,2):
        #        for d in dir(self.tables[id].table.item(row,2) ):
        #            for d in dir(self.tables[id].table): print d
        #            print self.tables[id].table.item(row,2).property('isChecked')
        #            break
        #self.tables[id].table.cellChanged.connect(lambda d, ID=id: self.update_create_tomoname(ID))

        self.pbs[id].clicked.connect(lambda dummy, pid=id, v=values: self.create_tomogram_folders(pid, v))


    def update_create_tomoname(self, id):
        n = len(sorted(glob.glob('{}/tomogram_*/sorted/*.mdoc'.format(self.tomogram_folder))))
        table = self.tables['tab1'].table
        widgets = self.tables['tab1'].widgets
        for row in range(table.rowCount()):
            wname = 'widget_{}_{}'.format(row,1)
            if wname in widgets.keys() and widgets[wname]:
                if widgets[wname].isChecked():
                    widgets['widget_{}_{}'.format(row, 2)].setText('tomogram_{:03d}'.format(n))
                    n+=1
                else:
                    widgets['widget_{}_{}'.format(row, 2)].setText('')

        table.resizeColumnsToContents()

    def create_tomogram_folders(self, id, values):
        n = len(sorted(glob.glob('{}/tomogram_*/sorted/*.mdoc'.format(self.tomogram_folder))))
        table = self.tables['tab1'].table
        widgets = self.tables['tab1'].widgets
        for row in range(table.rowCount()):
            wname = 'widget_{}_{}'.format(row, 1)

            # Create
            if wname in widgets.keys() and widgets[wname].isChecked():
                tomofoldername = widgets['widget_{}_{}'.format(row, 2)].text()
                mdocfile = values[row][0]
                folder = self.filepath_tomodata[widgets['widget_{}_{}'.format(row, 3)].currentText()]
                self.create_tomodir_instance(tomofoldername,mdocfile,folder)

            # Redo
            wname = 'widget_{}_{}'.format(row, 5)
            if wname in widgets.keys() and widgets[wname].isChecked():
                tomofoldername = widgets['widget_{}_{}'.format(row, 4)].text()
                mdocfile = os.path.basename(values[row][0])
                folder = self.filepath_tomodata[widgets['widget_{}_{}'.format(row, 3)].currentText()]
                mdocfile = os.path.join( self.filepath_tomodata[folder], mdocfile )
                shutil.rmtree( os.path.join(self.tomogram_folder, tomofoldername) )
                self.create_tomodir_instance(tomofoldername,mdocfile,folder)

            # Delete
            wname = 'widget_{}_{}'.format(row, 6)
            if wname in widgets.keys() and widgets[wname].isChecked():
                tomofoldername = widgets['widget_{}_{}'.format(row, 4)].text()
                shutil.rmtree( os.path.join(self.tomogram_folder, tomofoldername) )
                # self.create_tomodir_instance(tomofoldername,mdocfile,folder)
        self.update_create_tomoname(id,values)

    def create_tomodir_instance(self, tomofoldername, mdocfile, folder):
        src = os.path.join(self.tomogram_folder, '.tomoname')
        num_subprocesses = 10
        dst = os.path.join(self.tomogram_folder, tomofoldername)
        if os.path.exists(dst):
            print('{} exists: QUIT'.format(dst))
            return
        shutil.copytree(src, dst)
        mdoc_dst = os.path.join(dst, 'sorted', os.path.basename(mdocfile))
        os.link(mdocfile, mdoc_dst)

        # tif_files = [ line for line in open(os.path.join(mdoc_dst) ,'r').readlines() if line.strip(' ').startswith('SubFramePath')]
        tif_files = [line for line in os.popen('cat {} | grep SubFramePath '.format(mdocfile)).readlines()]
        tiltangles = [float(line.split()[-1]) for line in
                      os.popen('cat {} | grep TiltAngle '.format(mdocfile)).readlines()]

        if len(tif_files) == 0: return

        for n in range(len(tif_files)):
            tif_files[n] = [line.replace('.tif', '.mrc') for line in repr(tif_files[n]).split('\\') if '.' in line][-1]
        name_angle = list(zip(tif_files, tiltangles))

        sort(name_angle, 1)

        procs = []
        newstack_in = '{:d}\n'.format(len(name_angle))
        for n, (tif, angle) in enumerate(name_angle):
            while len(procs) >= num_subprocesses:
                time.sleep(0.5)
                procs = [proc for proc in procs if proc.is_alive()]

            src_mcor = os.path.join(folder, tif)
            dst_mcor = os.path.join(os.path.dirname(mdoc_dst), 'sorted_{:02d}.mrc'.format(n))

            if os.path.exists(src_mcor):
                shutil.copyfile(src_mcor, dst_mcor)
                proc = Process(target=square_mrc, args=([dst_mcor]))
                procs.append(proc)
                proc.start()
                # out = square_mrc(dst_mcor)

    def tab2UI(self):
        id = 'tab2'
        self.row, self.column = 0, 0
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows

        parent = self.table_layouts[id]

        last, reftilt = 10, 5

        #self.insert_label(parent, text='Start Assignment', cstep=1, rstep=1, sizepolicy=self.sizePolicyB, width=200)
        self.insert_pushbutton(parent,cstep=1,text='Create Markerfile',action=self.startFidAssignment, params=[parent],
                               wname='startFidAss',rstep=1)
        self.widgets['startFidAss'].setSizePolicy(self.sizePolicyC)
        self.insert_label(parent,sizepolicy=self.sizePolicyA)
        pass

    def tab31UI(self):
        id = 'tab31'
        self.row, self.column = 0,0
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        parent = self.table_layouts[id]
        h = mode = 'v02_Align_'

        last, reftilt = 10, 5
        self.insert_label(parent,cstep=1,sizepolicy=self.sizePolicyB,width=400 )
        self.insert_label_line_push(parent,'Folder Sorted Tilt Images', 'v02_Align_FolderSorted',
                                    'Select the folder where the sorted tiltimages are located.\n')
        self.insert_label_spinbox(parent, mode+'FirstIndex', text='First Index', tooltip='Index of first image.',
                                  value=1,minimum=1,stepsize=1)
        self.insert_label_spinbox(parent, mode +'LastIndex', text='Last Index', tooltip='Index of last image.',
                                  value=last, minimum=2,stepsize=1)
        self.insert_label_spinbox(parent, mode +'RefTiltIndex', text='Reference Tilt Image', value=reftilt,minimum=1,
                                  tooltip='Index of reference tilt image. Typically zeros degree image.')
        self.insert_label_spinbox(parent, mode +'RefMarkerIndex', text='Reference Marker', value=1,
                                  tooltip='Index of reference marker. See previous step.')
        self.insert_label_spinbox(parent, mode + 'BinningFactor', text='Binning Factor',value=8, cstep=0,
                                  tooltip='Binning factor used for reconstruction')
        #self.insert_label(parent,'Orientation tilt axis', rstep=1, cstep=1,
        #                  tooltip='Orientation of the tiltaxis with respect to the orientation of the camera.'+
        #                 'The point of the arrow indicates the rotation direction, following the left hand rule.')
        self.widgets[mode + 'tomofolder'] = QLineEdit()
        self.widgets[mode + 'tomogramNR'] = QLineEdit()
        self.widgets[mode + 'FolderSorted'].textChanged.connect(lambda dummy, m=mode: self.updateTomoFolder(m))
        self.updateTomoFolder(mode)

        execfilename = [mode + 'tomofolder', 'alignment/alignment.sh']
        paramsSbatch = guiFunctions.createGenericDict(fname='Alignment',folder=execfilename)
        paramsCmd    = [mode + 'tomofolder', self.parent().pytompath, mode + 'FirstIndex', mode + 'LastIndex',
                        mode + 'RefTiltIndex', mode + 'RefMarkerIndex', mode + 'BinningFactor', templateAlignment]

        self.insert_gen_text_exe(parent, mode, jobfield=False, exefilename=execfilename, paramsSbatch = paramsSbatch,
                                 paramsCmd=paramsCmd, action=self.convert_em, paramsAction=[mode,'alignment','sorted'])
        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        self.table_layouts[id].addWidget(label)

    def tab32UI(self):
        id='tab32'
        headers = ["name tomogram", "align", 'First Index',"Last Index", 'Reference Image', 'Reference Marker']
        types = ['txt', 'checkbox', 'lineedit', 'lineedit', 'lineedit', 'combobox']
        sizes = [0, 80, 0, 0, 0, 0, 0]

        tooltip = ['Names of existing tomogram folders.',
                   'Do alignment.',
                   'First index of tiltimages',
                   'Last index of tiltimages',
                   'Reference image number.',
                   'Redo the creation of a tomogram file.',
                   'Select items to delete tomogram folders.']

        tomodir = 'Juliette/03_Tomographic_Reconstruction'

        markerfiles = sorted(glob.glob('{}/tomogram_*/sorted/markerfile.em'.format(tomodir)))


        values = []

        for markerfile in markerfiles:
            qmarkerfile = markerfile.replace('markerfile.em','*.mdoc')
            qsortedfiles = markerfile.replace('markerfile.em','sorted_*.mrc')
            mdocfile = glob.glob( qmarkerfile )[0]
            tangs = numpy.abs(numpy.array(sorted([float(line.split()[-1]) for line in
                                        os.popen('cat {} | grep TiltAngle '.format(mdocfile)).readlines()])) )

            sortedfiles = glob.glob(qsortedfiles)
            last_frame = len(sortedfiles)
            index_zero_angle = 0
            mm = 9999
            for n, sortedfile in enumerate(sortedfiles):
                index_s = int(sortedfile.split('_')[-1].split('.')[0])
                if tangs[index_s] < mm:
                    mm = tangs[index_s]
                    index_zero_angle = n+1

            data = read_em(markerfile)
            options_reference = map(str, range(1, data.shape[2] + 1)) + ['all']
            values.append( [markerfile, True, 1, last_frame, index_zero_angle, options_reference] )

        self.fill_tab(id, headers, types, values, sizes, tooltip=tooltip)

    def tab41UI(self):
        id = 'tab41'
        alg = 'INFR'
        mode = 'v02_{}_'.format(alg)
        self.row, self.column = 0,0
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        parent = self.table_layouts[id]


        last,reftilt = 10, 5
        self.insert_label(parent,cstep=1,sizepolicy=self.sizePolicyB,width=400 )
        self.insert_label_line_push(parent,'Folder Sorted Tilt Images', mode+'FolderSorted',
                                    'Select the folder where the sorted tiltimages are located.\n')
        self.insert_label_spinbox(parent, mode+'FirstIndex', text='First Index', tooltip='Index of first image.',
                                  value=1,minimum=1,stepsize=1)
        self.insert_label_spinbox(parent, mode +'LastIndex', text='Last Index', tooltip='Index of last image.',
                                  value=last, minimum=2,stepsize=1)
        self.insert_label_spinbox(parent, mode +'RefTiltIndex', text='Reference Tilt Image', value=reftilt,minimum=1,
                                  tooltip='Index of reference tilt image. Typically zeros degree image.')
        self.insert_label_spinbox(parent, mode +'RefMarkerIndex', text='Reference Marker', value=1,
                                  tooltip='Index of reference marker. See previous step.')
        self.insert_label_spinbox(parent, mode + 'BinningFactor', text='Binning Factor',value=8, cstep=0,
                                  tooltip='Binning factor used for reconstruction')

        #self.insert_label(parent,'Orientation tilt axis', rstep=1, cstep=1,
        #                  tooltip='Orientation of the tiltaxis with respect to the orientation of the camera.'+
        #                 'The point of the arrow indicates the rotation direction, following the left hand rule.')

        self.widgets[mode + 'tomofolder'] = QLineEdit()
        self.widgets[mode + 'tomogramNR'] = QLineEdit()
        self.widgets[mode + 'FolderSorted'].textChanged.connect(lambda dummy, m=mode: self.updateTomoFolder(m))
        self.updateTomoFolder(mode)

        execfilename = [mode+'tomofolder','reconstruction/INFR/INFR_reconstruction.sh']
        paramsSbatch = guiFunctions.createGenericDict()
        paramsSbatch['fname'] = 'ReconstructionINFR'
        paramsSbatch['folder'] = execfilename

        self.insert_gen_text_exe(parent,mode,jobfield=False,action=self.convert_em,paramsAction=[mode,'reconstruction/INFR','sorted'],
                                 exefilename=execfilename, paramsSbatch=paramsSbatch,
                                 paramsCmd=[mode+'tomofolder',self.parent().pytompath,mode+'FirstIndex',mode+'LastIndex',
                                            mode + 'RefTiltIndex',mode + 'RefMarkerIndex',mode+'BinningFactor',
                                            self.parent().pytompath, mode + 'tomogramNR', templateINFR])

        #self.insert_label_action_label(parent,'Generate command',cstep=-2, sizepolicy=self.sizePolicyB)
        #self.insert_textfield(parent, h+'CommandText', columnspan=3, rstep=1, cstep=2)
        #self.insert_label_action_label(parent,'Execute command', rstep=1)
        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        self.table_layouts[id].addWidget(label)

    def updateTomoFolder(self, mode):

        folderSorted = self.widgets[mode+'FolderSorted'].text()
        print(folderSorted)
        if not folderSorted: return
        t = folderSorted.replace('/sorted','')
        self.widgets[mode+'tomofolder'].setText(t)
        self.widgets[mode+ 'tomogramNR'].setText( os.path.basename(t) )

        files = [line for line in os.listdir(folderSorted) if line.startswith('sorted') and line.endswith('.mrc')]
        lastIndex = len(files)
        self.widgets[mode+'LastIndex'].setValue(lastIndex)
        mdocfiles = [line for line in os.listdir(folderSorted) if line.endswith('.mdoc')]

        if len(mdocfiles) ==1:
            mdocfile = mdocfiles[0]
            angles = []
            for line in [line for line in open(f'{folderSorted}/{mdocfile}','r').readlines()]:
                if line.startswith('TiltAngle = '):
                    angles.append( float(line[len('TiltAngle = '):]))
            angles = numpy.array(sorted(angles))

            for i in range(len(files)):
                if not 'sorted_{:02d}.mrc'.format(i) in files:
                    angles[i]+=10000

            refIndex = 1 + abs(angles).argmin()
            self.widgets[mode+'RefTiltIndex'].setValue(refIndex)

    def tab42UI(self):
        id = 'tab42'
        alg = 'WBP'
        h =  mode = 'v02_{}_'.format(alg)
        self.row, self.column = 0,0
        rows, columns = 20, 20
        self.items = [['', ] * columns, ] * rows
        parent = self.table_layouts[id]


        last,reftilt = 10, 5
        self.insert_label(parent,cstep=1,sizepolicy=self.sizePolicyB,width=400 )
        self.insert_label_line_push(parent,'Folder Sorted Tilt Images', h+'FolderSorted',
                                    'Select the folder where the sorted tiltimages are located.\n')
        self.insert_label_spinbox(parent, mode+'FirstIndex', text='First Index', tooltip='Index of first image.',
                                  value=1,minimum=1,stepsize=1)
        self.insert_label_spinbox(parent, mode +'LastIndex', text='Last Index', tooltip='Index of last image.',
                                  value=last, minimum=2,stepsize=1)
        self.insert_label_spinbox(parent, mode +'RefTiltIndex', text='Reference Tilt Image', value=reftilt,minimum=1,
                                  tooltip='Index of reference tilt image. Typically zeros degree image.')
        self.insert_label_spinbox(parent, mode +'RefMarkerIndex', text='Reference Marker', value=1,
                                  tooltip='Index of reference marker. See previous step.')
        self.insert_label_spinbox(parent, mode + 'BinningFactor', text='Binning Factor',value=8, cstep=0,
                                  tooltip='Binning factor used for reconstruction')

        self.widgets[h + 'tomofolder'] = QLineEdit()
        self.widgets[h + 'tomogramNR'] = QLineEdit()
        self.widgets[h + 'FolderSorted'].textChanged.connect(lambda dummy, m=mode: self.updateTomoFolder(m))
        self.updateTomoFolder(mode)

        execfilename = [mode + 'tomofolder', 'reconstruction/WBP/WBP_reconstruction.sh']

        paramsSbatch = guiFunctions.createGenericDict()
        paramsSbatch['fname'] = 'ReconstructionWBP'
        paramsSbatch[ 'folder' ] = execfilename

        paramsCmd = [mode + 'tomofolder', self.parent().pytompath, mode + 'FirstIndex',
                     mode + 'LastIndex',
                     mode + 'RefTiltIndex', mode + 'RefMarkerIndex', mode + 'BinningFactor',
                     mode + 'tomogramNR', '.em', '464', templateWBP]

        self.insert_gen_text_exe(parent,mode, jobfield=False, action=self.convert_em, exefilename=execfilename,
                                 paramsAction=[mode,'reconstruction/WBP','sorted'],paramsSbatch=paramsSbatch,
                                 paramsCmd=paramsCmd)

        label = QLabel()
        label.setSizePolicy(self.sizePolicyA)
        self.table_layouts[id].addWidget(label)

    def convert_em(self,params):
        mode = params[0]
        directory = self.widgets[mode+'tomofolder'].text()
        output_folder = '{}/{}'.format(directory, params[1])
        prefix = params[2]
        sorted_folder = self.widgets[mode+'FolderSorted'].text()
        try: os.system(f'cp {directory}/sorted/markerfile.em {output_folder}/markerfile.em')
        except: pass


        if not os.path.exists(f'{output_folder}/temp_files_unweighted'): os.mkdir(f'{output_folder}/temp_files_unweighted')

        if len([line for line in os.listdir(output_folder) if line.startswith(prefix.split('/')[-1])]):
            os.system('rm {}/sorted*.em'.format(output_folder))


        guiFunctions.conv_mrc2em(self.widgets[mode+'FolderSorted'].text(), output_folder)
        guiFunctions.renumber_gui2pytom(output_folder, prefix.split('/')[-1])
        #print (self.pytompath)
        #print ('{}/bin/pytom rename_renumber.py {} {} {}'.format(self.pytompath, sorted_folder, output_folder, prefix))


        # print '{}/reconstruction/{}/reconstruction.sh'.format(tomofolderpath,p)
        try:
            if os.path.exists('{}/reconstruction.sh'.format(output_folder)):
                for i in range(1000):
                    if not os.path.exists('{}/backup'.format(output_folder)): os.mkdir(
                        '{}/backup'.format(output_folder))
                    fname = "{}/backup/reconstruction_{:03d}".format(output_folder, i)
                    if os.path.exists(fname): continue

                    os.mkdir(fname)
                    for f in ('temp_files_binned', 'temp_files_unweighted', 'temp_files_weighted', 'tomogram.em',
                              'reconstruction.sh', 'markerfile.em'):
                        if os.path.exists('{}/{}'.format(output_folder, f)): os.system(
                            'mv {}/{} {}/'.format(output_folder, f, fname))
                        if f != 'tomogram.em' and f != 'reconstruction.sh':
                            if not os.path.exists("{}/{}".format(output_folder, f)): os.mkdir(
                                "{}/{}".format(output_folder, f))
                    break
        except:
            pass


    def tab43UI(self):
        id='tab43'
        headers = ["name tomogram", "INFR", 'WBP', 'First Index', "Last Index", 'Reference Image', 'Reference Marker',
                   'Binning Factor']
        types = ['txt', 'checkbox', 'checkbox', 'lineedit', 'lineedit', 'lineedit', 'lineedit', 'lineedit']
        sizes = [0, 80, 80, 0, 0, 0, 0, 0]

        tooltip = ['Names of existing tomogram folders.',
                   'Do INFR Reconstruction.',
                   'Do WBP Reconstruction.',
                   'First index of tiltimages',
                   'Last index of tiltimages',
                   'Reference Image number.',
                   'Reference Marker number.',
                   'Binning factor applied to images.']

        tomodir = 'Juliette/03_Tomographic_Reconstruction'

        markerfiles = sorted(glob.glob('{}/tomogram_*/sorted/markerfile.em'.format(tomodir)))

        values = []

        for markerfile in markerfiles:
            qmarkerfile = markerfile.replace('markerfile.em','*.mdoc')
            qsortedfiles = markerfile.replace('markerfile.em','sorted_*.mrc')
            mdocfile = glob.glob( qmarkerfile )[0]
            tangs = numpy.abs(numpy.array(sorted([float(line.split()[-1]) for line in
                                        os.popen('cat {} | grep TiltAngle '.format(mdocfile)).readlines()])) )

            sortedfiles = glob.glob(qsortedfiles)
            last_frame = len(sortedfiles)
            index_zero_angle = 0
            mm = 9999
            for n, sortedfile in enumerate(sortedfiles):
                index_s = int(sortedfile.split('_')[-1].split('.')[0])
                if tangs[index_s] < mm:
                    mm = tangs[index_s]
                    index_zero_angle = n+1

            values.append( [markerfile, True, True, 1, last_frame, index_zero_angle, 1, 8] )

        self.fill_tab(id, headers, types, values, sizes, tooltip=tooltip)

        pass
