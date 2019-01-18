from PyQt4 import QtCore, QtGui

import widget_mod


import sys,os
try:
    import dicom
except:
    import pydicom as dicom
import numpy
#import matplotlib.pyplot as plt
from datetime import datetime
from math import exp, log
import shutil
import subprocess

#current_dir=os.path.dirname(os.path.realpath(__file__))
current_dir=os.getcwd()



#in_folder=os.path.join(current_dir,'in')
#f=open('input_directory.txt','r')
#global in_folder=f.readline()
#f.close()
#print in_folder
out_folder=os.path.join(current_dir,'out')
donor=dicom.read_file(os.path.join(current_dir,'donor.ima'))

TEW_sensitivity=0.00000974



class qsGui(QtGui.QMainWindow, widget_mod.Ui_MainWindow):
    def __init__(self, parent=None):
        super(qsGui,self).__init__(parent)
        #self.move(QtGui.QApplication.desktop().screen().rect().center()- self.rect().center())###
        
        self.setupUi(self)
        self.connectActions()
        
        #self.textBrowser.append('Text')
        
    def connectActions(self):
        a=1
        self.pushButton_process.clicked.connect(self.process)
        self.pushButton_confirm.clicked.connect(self.confirm)
        self.pushButton_reload.clicked.connect(self.reload_ims)
        self.pushButton_clear.clicked.connect(self.clear)
        self.pushButton_save_settings.clicked.connect(self.save_settings)
        self.pushButton_default_settings.clicked.connect(self.default_settings)


    def process(self):
        #self.label_patient.setText("Patient: Processing!")
        #self.textBrowser.append('Processing')
        #print 'Process pushed...'
        in_folder=str(self.label_input_dir_path.text())
        try:
            InjDate=str(self.lineEdit_InjDate.text())
            print InjDate
            if len(InjDate.split('/'))==3:
                year=InjDate.split('/')[-1]
                print year
                if len(year)<4:
                  year='20'+year
                day=InjDate.split('/')[0]
                if len(day)<2:
                    day='0'+day
                print day
                month=InjDate.split('/')[1]
                if len(month)<2:
                    month='0'+month
                print month
                #print InjDate
            else:
                year='20'+InjDate[4:6]
                day=InjDate[0:2]
                month=InjDate[2:4]
            if InjDate=='':
                self.textBrowser.append('Check Injection Date (blank)')
                return
        except:
            self.textBrowser.append('Check Injection Date (exception)')
            return
        try:
            InjTime=str(self.lineEdit_InjTime.text())
            if len(InjTime.split(':'))==2:
                InjH=InjTime.split(':')[0]
                InjM=InjTime.split(':')[1]
            else:
                InjH=InjTime[0:2]
                InjM=InjTime[2:4]
                InjS='00'
        except:
            self.textBrowser.append('Check Injection Time')
            return
        
        try:    
            injectiontime=datetime(int(year),int(month),int(day),int(InjH),int(InjM))
        except:
            self.textBrowser.append('Check Injection Date/Time')
            return
        #####Fix for nested subdirectories
        filelist=[]
        for (directory,_,files) in os.walk(in_folder):
            for name in files:
                path=os.path.join(directory,name)
                ext=path.split('.')[-1]
                if ext.lower()=='dcm' or ext.lower()=='ima':
                   filelist.append(os.path.join(directory,name))
        #filelist=os.listdir(in_folder)

        datalist=[]
        i=0
        n_tomos=0
        for name in filelist:
            #filepath=os.path.join(in_folder,name)
            filepath=name
            dcm=dicom.read_file(filepath)
            if i>0:
                if dcm.StudyInstanceUID!=last_study_uid:
                    self.textBrowser.append('Multiple Studies Detected!\nClear QSPECT Directory and Reload images...')
                    return
            last_study_uid=dcm.StudyInstanceUID
            image_type=dcm.ImageType
            recon=False
            total_counts=dcm.pixel_array.sum()
            for s in image_type:
                if 'recon' in s.lower():
                    recon=True
            if recon==True:
                print 'FOUND!:',image_type
                SPECTcount77=dcm.pixel_array[0:77,:,:].sum()  ###0:77 is pelvis, 155: is head
                if dcm.pixel_array.shape[0]>155:
                    SPECTcount155=dcm.pixel_array[0:155,:,:].sum()
                SPECTcount=dcm.pixel_array.sum()
                SOPInstandUID=dcm.SOPInstanceUID
                #plt.imshow(dcm.pixel_array[155:,64,:])
                #plt.show()
                Time=dcm.AcquisitionTime
                Date=dcm.AcquisitionDate
                image_array=dcm.pixel_array
                n_slices=dcm.pixel_array.shape[0]
            else:
                print 'Not Found:', image_type
                n_tomos+=1
                StepDur=float(dcm.RotationInformationSequence[0].ActualFrameDuration)
                NbStep=int(dcm.RotationInformationSequence[0].NumberOfFramesInRotation)*2
                AcDur=int((StepDur*NbStep)/1000)
                print AcDur
            StudyUID=dcm.StudyInstanceUID
            IPP=dcm.DetectorInformationSequence[0].ImagePositionPatient
            
            datalist.append([filepath,recon,StudyUID,float(IPP[2]),total_counts,''])

            i+=1
            if i==1:
                a=1
        if n_slices>100 and n_tomos<2:
            self.textBrowser.append('Not enough TOMO bed steps for # of axial slices in recon\nPlease recheck input files...')
            return
        if n_slices>170 and n_tomos<3:
            self.textBrowser.append('Not enough TOMO bed steps for # of axial slices in recon\nPlease recheck input files...')
            return
                #break
        tomolist=[]
        for item in datalist:
            if item[1]==False:
                tomolist.append(item)
        order_arr=numpy.zeros([n_tomos,2])

        AcqH=Time[0:2]
        AcqM=Time[2:4]
        AcqS=Time[4:6]
        try:
            DoseMBq=float(self.lineEdit_activity.text())
        except:
            self.textBrowser.append('Check injected Dose...')
        Dose=str(float(DoseMBq)*1000000)
        iyear=Date[0:4]
        iday=Date[6:8]
        imonth=Date[4:6]
        imagetime=datetime(int(iyear),int(imonth),int(iday),int(AcqH),int(AcqM))
        image_justday=datetime(int(iyear),int(imonth),int(iday))
        injection_justday=datetime(int(year),int(month),int(day))
        delta_justday=image_justday-injection_justday
        justday=str(delta_justday.days)
        print 'justday: ', justday
        
        delta=imagetime-injectiontime
        DecayTime=delta.days*24*3600.+delta.seconds
        Day=str(delta.days)
        hours_pi=int(DecayTime/3600)
        halflife=579744
        DecayFactor=exp(log(2)*DecayTime/float(halflife))
        RemDose=float(Dose)/float(DecayFactor)

        for i in range(n_tomos):
            order_arr[i,0]=i
            order_arr[i,1]=tomolist[i][3]
        sort=numpy.argsort(order_arr[:,1])###array([2,1,0]) that when iterated will yield the tomo series from z-position
                                            ###low to high
        symbia=False
        for item in datalist:
            if item[1]==True:
                for version in dcm.SoftwareVersions:
                    if 'T6' in version:
                        symbia=True
                        print 'Symbia T6 detected...'

        deadtimes=numpy.array([])
        for i in range(len(tomolist)):
            counts=tomolist[sort[i]][4]
            count_rate=counts/float(AcDur)
            self.textBrowser.append('Tomo Wide Spectrum Count Rate: '+str(count_rate))
            if symbia==True:
                a=0.16
                b=400000
                c=1E-8
                d=20000
                deadtime=0.85+a*exp(float(count_rate)/b)+c*exp(float(count_rate)/d)
            else:
                a=0.047
                b=240000
                c=1E-16
                d=11000        
                deadtime=0.96+a*exp(float(count_rate)/b)+c*exp(float(count_rate)/d)
            self.textBrowser.append('Dead Time: '+str(deadtime))
            deadtimes=numpy.append(deadtimes,deadtime)

        if symbia==True:
            sensitivity=0.00001025
        else:
            sensitivity=0.00000974



        #### Higher z-position value indicates head end
        #### For spect pixel array [z,x,y] z index low-to-high is similarly feet-to-head

        print datalist
        print order_arr

        #Create Header for Output Dicom Images

        if n_tomos==1:
            image_array=image_array*deadtimes[0]
            print '1 Tomo series detected. Correcting with deadtime factor: ', deadtimes[0]
        if n_tomos==2:
            image_array[0:77,:,:]=image_array[0:77,:,:]*deadtimes[0]
            image_array[77:,:,:]=image_array[77:,:,:]*deadtimes[1]
            print '2 Tomo series detected. Correcting with deadtime factors: ', deadtimes[0],deadtimes[1]
        if n_tomos==3:
            image_array[0:77,:,:]=image_array[0:77,:,:]*deadtimes[0]
            image_array[77:155,:,:]=image_array[77:155,:,:]*deadtimes[1]
            image_array[155:,:,:]=image_array[155:,:,:]*deadtimes[2]
            print '3 Tomo series detected. Correcting with deadtime factors: ', deadtimes[0],deadtimes[1],deadtimes[2]

        n=1

        for item in datalist:
            if item[1]==True:
                #recon image
                dcm=dicom.read_file(item[0])

        voxel_volume=float(dcm.PixelSpacing[0])*float(dcm.PixelSpacing[0])*float(dcm.SliceThickness)/1000
        count_array=image_array
        image_array=image_array/(sensitivity*AcDur*voxel_volume)
        total_activity=image_array.sum()*voxel_volume
        print total_activity
        self.textBrowser.append('Day: '+str(justday)+' post-injection')
        self.textBrowser.append("Hours post-injection: "+str(hours_pi))
        self.textBrowser.append('Lu-177 Decay Factor: '+str(DecayFactor))
        self.textBrowser.append('Imaged Activity (MBq): '+str(int(total_activity/1E6)))
        percent_retention=(total_activity)*100/float(RemDose)
        self.textBrowser.append('Percent Retention: '+str(percent_retention))

        for item in datalist:
            if item[1]==True:
                #recon image
                dcm=dicom.read_file(item[0])
                dcm.SOPClassUID='1.2.840.10008.5.1.4.1.1.128'
                dcm.ImageType=['ORIGINAL', 'PRIMARY', 'AXIAL']

                #Fix with random # and iterate
                SOPInstanceUID=str(dcm.SOPInstanceUID)[:-10]+str(round(numpy.random.rand(),10)).split('.')[-1]
                SOPInstanceUID_start=SOPInstanceUID[:-4]
                SOPInstanceUID_end=SOPInstanceUID[-4:]
                SeriesInstanceUID=str(dcm.SeriesInstanceUID)[:-10]+str(round(numpy.random.rand(),10)).split('.')[-1]
                SeriesInstanceUID_start=SeriesInstanceUID[:-4]
                SeriesInstanceUID_end=SeriesInstanceUID[-4:]
                
                #dcm.SOPInstanceUID=

                dcm.Modality='PT'

                #need day #
                
                dcm.SeriesDescription='WB QSPECT SUV D'+justday
                self.lineEdit_description.setText('WB QSPECT SUV D'+str(justday))
                

                #if patient size and weight aren't input already:
                dcm.PatientSize=''
                dcm.PatientWeight=''

                try:
                    del dcm.SpacingBetweenSlices
                except:
                    a=1
                dcm.SeriesNumber=str(int(dcm.SeriesNumber)+1000)

                #need to iterate dcm.InstanceNumber from '1' to n+1
                dcm.InstanceNumber=str(n)

                #Image position and orientation are nested in detector information sequence
                IPP=dcm.DetectorInformationSequence[0].ImagePositionPatient
                IOP=dcm.DetectorInformationSequence[0].ImageOrientationPatient
                dcm.ImagePositionPatient=''#needs to be adjusted for z-position of each slice
                dcm.SliceLocation=IPP[2]  #same z-value as above
                dcm.ImageOrientationPatient=IOP
                try:
                    del dcm.FrameIncrementPointer
                except:
                    a=1
                #dcm.NumberOfSlices=int(dcm.NumberOfFrames)  #already included
                try:
                    del dcm.NumberOfFrames
                except:
                    a=1
                dcm.ImageComments='Symbia 7000 MBq on 20160114 at 11:00  -  Retention (Percent ID): 24.1\\WSC Tomo:19430924.517376\\52937458.31936\\Sens:0.00001025\\Tp:0.0000011860\\Tnp:0.0000004583\\CalDate:20140901'
                dcm.CorrectedImage=['NORM', 'DTIM', 'ATTN', 'SCAT', 'DECY']
                dcm.RescaleIntercept='0'
                RescaleSlope=1
                dcm.RescaleSlope=RescaleSlope  ##take from uint16 scaling
                dcm.RadiopharmaceuticalInformationSequence=donor.RadiopharmaceuticalInformationSequence
                dcm.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime=Time ####Update
                dcm.RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose=str(RemDose)####'6349825674.67765' ###Dose in Bq, decay adjusted for scan time (not actual injected value)
                dcm.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartDateTime='YYYYMMDDHHMMSS.00000' ##Just copy from scan time and decay correct dose above
                try:
                    del dcm.SliceVector
                except:
                    a=1

                dcm.SeriesType=['STATIC', 'IMAGE']
                dcm.Units='BQML'
                dcm.CountsSource='EMISSION'
                dcm.AttenuationCorrectionMethod='measured,AC_CT'
                dcm.DecayCorrection='START'
                dcm.ReconstructionMethod='3DOSEM,4i,8s'
                dcm.ScatterCorrectionMethod='DEW'
                dcm.FrameReferenceTime='0'
                dcm.DecayFactor=str(DecayFactor)###'1.10239246849172'
                dcm.DoseCalibrationFactor=str(1/sensitivity)###'97560.9756097561'  ##?????? InvSens 1/%Sensitivity%   (sens symbia:0.00001025, intevo:0.00000974
                dcm.DeadTimeFactor=str(deadtimes[0])  #Depends on TOMO factor
                dcm.ImageIndex=n #n equals slice #
                
                ### Check Symbia or Intevo
                for version in dcm.SoftwareVersions:
                    if 'T6' in version:
                        symbia=True
                        print 'Symbia T6 detected...'





    def confirm(self):
        #self.label_patient.setText("Patient: Processing!")
        #self.textBrowser.append('Processing')
        #print 'Process pushed...'
        if str(self.lineEdit_description.text())=='':
            self.textBrowser.append('No series description. Please retry')
            return
        qspect_ae=str(self.lineEdit_from_ae.text())
        to_ae=str(self.lineEdit_to_ae.text())
        ip_address=str(self.lineEdit_ip.text())
        port=str(self.lineEdit_port.text())
        transfer=bool(str(self.checkBox_delete_in.isChecked()))
        delete_in=str(self.checkBox_delete_in.isChecked())
        delete_temp=str(self.checkBox_delete_temp.isChecked())
        save_local=str(self.checkBox_save_local.isChecked())
        backup_dir=str(self.lineEdit_output_dir.text())
        in_folder=str(self.label_input_dir_path.text())
        try:
            shutil.rmtree(out_folder)
        except:
            a=1
        try:
            os.mkdir(out_folder)
        except:
            a=1
        try:
            InjDate=str(self.lineEdit_InjDate.text())
            print InjDate
            if len(InjDate.split('/'))==3:
                year=InjDate.split('/')[-1]
                print year
                if len(year)<4:
                  year='20'+year
                day=InjDate.split('/')[0]
                print day
                month=InjDate.split('/')[1]
                print month
                #print InjDate
            else:
                year='20'+InjDate[4:6]
                day=InjDate[0:2]
                month=InjDate[2:4]
            if InjDate=='':
                self.textBrowser.append('Check Injection Date (blank)')
                return
        except:
            self.textBrowser.append('Check Injection Date (exception)')
            return
        try:
            InjTime=str(self.lineEdit_InjTime.text())
            if len(InjTime.split(':'))==2:
                InjH=InjTime.split(':')[0]
                InjM=InjTime.split(':')[1]
            else:
                InjH=InjTime[0:2]
                InjM=InjTime[2:4]
                InjS='00'
        except:
            self.textBrowser.append('Check Injection Time')
            return
        
        try:    
            injectiontime=datetime(int(year),int(month),int(day),int(InjH),int(InjM))
        except:
            self.textBrowser.append('Check Injection Date/Time')
            return
        #####Fix for nested subdirectories
        filelist=[]
        for (directory,_,files) in os.walk(in_folder):
            for name in files:
                path=os.path.join(directory,name)
                ext=path.split('.')[-1]
                if ext.lower()=='dcm' or ext.lower()=='ima':
                   filelist.append(os.path.join(directory,name))
        #filelist=os.listdir(in_folder)

        try:
            height=str(self.lineEdit_height.text())
            if height=='':
                self.textBrowser.append('Check patient Height')
                return
        except:
            self.textBrowser.append('Check patient Height')
        try:
            weight=str(self.lineEdit_weight.text())
            if weight=='':
                self.textBrowser.append('Check patient Weight')
                return
        except:
            self.textBrowser.append('Check patient Weight')
            
                




        datalist=[]
        i=0
        n_tomos=0
        for name in filelist:
            #filepath=os.path.join(in_folder,name)
            filepath=name
            dcm=dicom.read_file(filepath)
            if i>0:
                if dcm.StudyInstanceUID!=last_study_uid:
                    self.textBrowser.append('Multiple Studies Detected!\nClear QSPECT Directory and Reload images...')
                    return
            last_study_uid=dcm.StudyInstanceUID
            image_type=dcm.ImageType
            recon=False
            total_counts=dcm.pixel_array.sum()
            for s in image_type:
                if 'recon' in s.lower():
                    recon=True
            if recon==True:
                print 'FOUND!:',image_type
                SPECTcount77=dcm.pixel_array[0:77,:,:].sum()  ###0:77 is pelvis, 155: is head
                if dcm.pixel_array.shape[0]>155:
                    SPECTcount155=dcm.pixel_array[0:155,:,:].sum()
                SPECTcount=dcm.pixel_array.sum()
                SOPInstandUID=dcm.SOPInstanceUID
                #plt.imshow(dcm.pixel_array[155:,64,:])
                #plt.show()
                Time=dcm.AcquisitionTime
                Date=dcm.AcquisitionDate
                image_array=dcm.pixel_array
                n_slices=dcm.pixel_array.shape[0]
            else:
                print 'Not Found:', image_type
                n_tomos+=1
                StepDur=float(dcm.RotationInformationSequence[0].ActualFrameDuration)
                NbStep=int(dcm.RotationInformationSequence[0].NumberOfFramesInRotation)*2
                AcDur=int((StepDur*NbStep)/1000)
                print AcDur
            StudyUID=dcm.StudyInstanceUID
            IPP=dcm.DetectorInformationSequence[0].ImagePositionPatient
            
            datalist.append([filepath,recon,StudyUID,float(IPP[2]),total_counts,''])

            i+=1
            if i==1:
                a=1
                #break
        if n_slices>100 and n_tomos<2:
            self.textBrowser.append('Not enough TOMO bed steps for # of axial slices in recon\nPlease recheck input files...')
            return
        if n_slices>170 and n_tomos<3:
            self.textBrowser.append('Not enough TOMO bed steps for # of axial slices in recon\nPlease recheck input files...')
            return
        tomolist=[]
        for item in datalist:
            if item[1]==False:
                tomolist.append(item)
        order_arr=numpy.zeros([n_tomos,2])

        AcqH=Time[0:2]
        AcqM=Time[2:4]
        AcqS=Time[4:6]
        try:
            DoseMBq=float(self.lineEdit_activity.text())
        except:
            self.textBrowser.append('Check injected Dose...')
        Dose=str(float(DoseMBq)*1000000)
        iyear=Date[0:4]
        iday=Date[6:8]
        imonth=Date[4:6]
        imagetime=datetime(int(iyear),int(imonth),int(iday),int(AcqH),int(AcqM))
        image_justday=datetime(int(iyear),int(imonth),int(iday))
        injection_justday=datetime(int(year),int(month),int(day))
        delta_justday=image_justday-injection_justday
        justday=str(delta_justday.days)
        print 'justday: ', justday
        
        delta=imagetime-injectiontime
        DecayTime=delta.days*24*3600.+delta.seconds
        Day=str(delta.days)
        hours_pi=int(DecayTime/3600)
        halflife=579744
        DecayFactor=exp(log(2)*DecayTime/float(halflife))
        RemDose=float(Dose)/float(DecayFactor)

        for i in range(n_tomos):
            order_arr[i,0]=i
            order_arr[i,1]=tomolist[i][3]
        sort=numpy.argsort(order_arr[:,1])###array([2,1,0]) that when iterated will yield the tomo series from z-position
                                            ###low to high
        symbia=False
        for item in datalist:
            if item[1]==True:
                for version in dcm.SoftwareVersions:
                    if 'T6' in version:
                        symbia=True
                        print 'Symbia T6 detected...'

        deadtimes=numpy.array([])
        for i in range(len(tomolist)):
            counts=tomolist[sort[i]][4]
            count_rate=counts/float(AcDur)
            #self.textBrowser.append('Tomo Wide Spectrum Count Rate: '+str(count_rate))
            if symbia==True:
                a=0.16
                b=400000
                c=1E-8
                d=20000
                deadtime=0.85+a*exp(float(count_rate)/b)+c*exp(float(count_rate)/d)
            else:
                a=0.047
                b=240000
                c=1E-16
                d=11000        
                deadtime=0.96+a*exp(float(count_rate)/b)+c*exp(float(count_rate)/d)
            #self.textBrowser.append('Dead Time: '+str(deadtime))
            deadtimes=numpy.append(deadtimes,deadtime)

        if symbia==True:
            sensitivity=0.00001025
        else:
            sensitivity=0.00000974



        #### Higher z-position value indicates head end
        #### For spect pixel array [z,x,y] z index low-to-high is similarly feet-to-head

        print datalist
        print order_arr

        #Create Header for Output Dicom Images

        if n_tomos==1:
            image_array=image_array*deadtimes[0]
            print '1 Tomo series detected. Correcting with deadtime factor: ', deadtimes[0]
        if n_tomos==2:
            image_array[0:77,:,:]=image_array[0:77,:,:]*deadtimes[0]
            image_array[77:,:,:]=image_array[77:,:,:]*deadtimes[1]
            print '2 Tomo series detected. Correcting with deadtime factors: ', deadtimes[0],deadtimes[1]
        if n_tomos==3:
            image_array[0:77,:,:]=image_array[0:77,:,:]*deadtimes[0]
            image_array[77:155,:,:]=image_array[77:155,:,:]*deadtimes[1]
            image_array[155:,:,:]=image_array[155:,:,:]*deadtimes[2]
            print '3 Tomo series detected. Correcting with deadtime factors: ', deadtimes[0],deadtimes[1],deadtimes[2]

        n=1

        for item in datalist:
            if item[1]==True:
                #recon image
                dcm=dicom.read_file(item[0])

        voxel_volume=float(dcm.PixelSpacing[0])*float(dcm.PixelSpacing[0])*float(dcm.SliceThickness)/1000
        count_array=image_array
        image_array=image_array/(sensitivity*AcDur*voxel_volume)
        total_activity=image_array.sum()*voxel_volume
        print total_activity
        #self.textBrowser.append('Day: '+str(justday)+' post-injection')
        #self.textBrowser.append("Hours post-injection: "+str(hours_pi))
        #self.textBrowser.append('Lu-177 Decay Factor: '+str(DecayFactor))
        #self.textBrowser.append('Imaged Activity (MBq): '+str(int(total_activity/1E6)))
        percent_retention=(total_activity)*100/float(RemDose)
        #self.textBrowser.append('Percent Retention: '+str(percent_retention))
        self.textBrowser.append('Saving output files...')
        
        for item in datalist:
            if item[1]==True:
                #recon image
                dcm=dicom.read_file(item[0])
                dcm.file_meta.MediaStorageSOPClassUID='1.2.840.10008.5.1.4.1.1.128'
                dcm.SOPClassUID='1.2.840.10008.5.1.4.1.1.128'
                dcm.ImageType=['ORIGINAL', 'PRIMARY', 'AXIAL']

                #Fix with random # and iterate
                SOPInstanceUID=str(dcm.SOPInstanceUID)[:-10]+str(round(numpy.random.rand(),10)).split('.')[-1]
                SOPInstanceUID_start=SOPInstanceUID[:-4]
                SOPInstanceUID_end=SOPInstanceUID[-4:]
                SeriesInstanceUID=str(dcm.SeriesInstanceUID)[:-10]+str(round(numpy.random.rand(),10)).split('.')[-1]
                SeriesInstanceUID_start=SeriesInstanceUID[:-4]
                SeriesInstanceUID_end=SeriesInstanceUID[-4:]
                
                #dcm.SOPInstanceUID=

                dcm.Modality='PT'

                #need day #
                #dcm.SeriesDescription='WB QSPECT SUV D'+justday
                dcm.SeriesDescription=str(self.lineEdit_description.text())
                #if patient size and weight aren't input already:
                dcm.PatientSize=height
                dcm.PatientWeight=weight

                try:
                    del dcm.SpacingBetweenSlices
                except:
                    a=1
                dcm.SeriesNumber=str(int(dcm.SeriesNumber)+1000)

                #need to iterate dcm.InstanceNumber from '1' to n+1
                dcm.InstanceNumber=str(n)

                #Image position and orientation are nested in detector information sequence
                IPP=dcm.DetectorInformationSequence[0].ImagePositionPatient
                IOP=dcm.DetectorInformationSequence[0].ImageOrientationPatient
                dcm.ImagePositionPatient=''#needs to be adjusted for z-position of each slice
                dcm.SliceLocation=IPP[2]  #same z-value as above
                #dcm.ImageOrientationPatient=IOP
                dcm.ImageOrientationPatient=['1', '0', '0', '0', '1', '0']
                try:
                    del dcm.FrameIncrementPointer
                except:
                    a=1
                #dcm.NumberOfSlices=int(dcm.NumberOfFrames)  #already included
                try:
                    del dcm.NumberOfFrames
                except:
                    a=1
                if len(month)<2:
                    month='0'+month
                if len(day)<2:
                    day='0'+day
                dcm.ImageComments='Symbia '+str(DoseMBq)+' MBq on '+str(year)+str(month)+str(day)+' at '+str(InjH)+':'+str(InjM)+'  -  Retention (Percent ID): +'+str(percent_retention)
                dcm.CorrectedImage=['NORM', 'DTIM', 'ATTN', 'SCAT', 'DECY']
                dcm.RescaleIntercept='0'
                RescaleSlope=1
                dcm.RescaleSlope=RescaleSlope  ##take from uint16 scaling
                dcm.RadiopharmaceuticalInformationSequence=donor.RadiopharmaceuticalInformationSequence
                dcm.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartTime=Time ####Update
                dcm.RadiopharmaceuticalInformationSequence[0].RadionuclideTotalDose=str(RemDose)####'6349825674.67765' ###Dose in Bq, decay adjusted for scan time (not actual injected value)
                startdatetime=dcm.AcquisitionDate+dcm.AcquisitionTime #'YYYYMMDDHHMMSS.00000'
                dcm.RadiopharmaceuticalInformationSequence[0].RadiopharmaceuticalStartDateTime=startdatetime ##Just copy from scan time and decay correct dose above
                try:
                    del dcm.SliceVector
                except:
                    a=1

                dcm.SeriesType=['STATIC', 'IMAGE']
                dcm.Units='BQML'
                dcm.CountsSource='EMISSION'
                dcm.AttenuationCorrectionMethod='measured,AC_CT'
                dcm.DecayCorrection='START'
                dcm.ReconstructionMethod='3DOSEM,4i,8s'
                dcm.ScatterCorrectionMethod='DEW'
                dcm.FrameReferenceTime='0'
                dcm.DecayFactor=str(DecayFactor)###'1.10239246849172'
                dcm.DoseCalibrationFactor=str(1/sensitivity)###'97560.9756097561'  ##?????? InvSens 1/%Sensitivity%   (sens symbia:0.00001025, intevo:0.00000974
                dcm.DeadTimeFactor=str(deadtimes[0])  #Depends on TOMO factor
                #dcm.ImageIndex=n #n equals slice #
                
                ### Check Symbia or Intevo
                for version in dcm.SoftwareVersions:
                    if 'T6' in version:
                        symbia=True
                        print 'Symbia T6 detected...'
                max_val=image_array.max()
                min_val=image_array.min()
                print max_val,min_val
                rescale_slope=(max_val-min_val)/32000
                rescale_intercept=min_val
                scaled_array=(image_array-min_val)/rescale_slope
                print scaled_array.max()
                print scaled_array.min(), rescale_slope, rescale_intercept
                scaled_array=scaled_array.astype('uint16')
                dcm.ActualFrameDuration=str(int(AcDur)*1000)
                dcm.RescaleSlope=str(rescale_slope)
                dcm.RescaleIntercept=str(rescale_intercept)
                dcm.remove_private_tags()
                dcm.RescaleType='BQML'

        SOP_uid_end=dcm.SOPInstanceUID[-4:]
        SOP_uid_start=dcm.SOPInstanceUID[:-4]

        SeriesInstanceUID=str(dcm.SeriesInstanceUID)[:-6]+str(round(numpy.random.rand(),6)).split('.')[-1]
        SeriesInstanceUID_start=SeriesInstanceUID[:-4]
        SeriesInstanceUID_end=SeriesInstanceUID[-4:]

        slice_home=IPP[2]
        thickness=float(dcm.SliceThickness)
        
        for i in range(image_array.shape[0]):
            dcm.ImageIndex=i+1
            dcm.InstanceNumber=str(i+1)
            
            current_instance_uid=SOPInstanceUID_start+str(int(SOPInstanceUID_end)+i).zfill(4)
            dcm.SeriesInstanceUID=SeriesInstanceUID
            dcm.file_meta.MediaStorageSOPInstanceUID=current_instance_uid
            dcm.SOPInstanceUID=current_instance_uid
            dcm.SliceLocation=str(slice_home+i*thickness)
            #print dcm.SliceLocation
            dcm.ImagePositionPatient=[IPP[0],IPP[1],str(slice_home+i*thickness)]
            #print dcm.ImagePositionPatient
            dcm.PixelData=scaled_array[i,:,:].tostring()
            #filename=str(i+1).zfill(4)+'.dcm'
            filename=str(current_instance_uid)+'.dcm'
            dcm.save_as(os.path.join(out_folder,filename))
            if i%50==0:
                self.textBrowser.append('Slice #: '+str(i))
        clear_in=self.checkBox_delete_in.isChecked()
        print clear_in
        if clear_in==True:
            try:
                shutil.rmtree(in_folder)
            except:
                a=1
            try:
                os.mkdir(in_folder)
            except:
                a=1
        transfer=self.checkBox_transfer.isChecked()
        print transfer
        if transfer==True:
            self.textBrowser.append('Transferring images to:')
            to_ae=str(self.lineEdit_to_ae.text())
            ip=str(self.lineEdit_ip.text())
            port=str(self.lineEdit_port.text())
            self.textBrowser.append(to_ae+'   '+ip+'   '+port)
            self.textBrowser.append('Please be patient...')
            call='storescu -v -aet '+qspect_ae+' -aec '+to_ae+' '+ip+' '+port+' out\\*'
            print call
            self.textBrowser.append(subprocess.Popen(call, shell=False, stdout=subprocess.PIPE).stdout.read())
        else:
            self.textBrowser.append('Transfer deactivated. Images will not be sent to dicom database')
        save_local=self.checkBox_save_local.isChecked()
        if save_local==True:
            self.textBrowser.append('Saving local backup to:')
            bu_full=os.path.join(backup_dir,dcm.PatientName+'_'+dcm.AcquisitionDate)
            self.textBrowser.append(bu_full)
            if os.path.exists(bu_full):
                self.textBrowser.append('Backup already exists... overwriting')
                shutil.rmtree(bu_full)
            shutil.copytree(out_folder,bu_full)
            
        self.textBrowser.append('Complete!')


            
    def reload_ims(self):
        print 'reloading...'
        self.label_patient.setText("Patient: ")
        self.label_AcqDate.setText("Acquisition Date: ")
        self.label_AcqTime.setText('Acquisition Time: ')
        self.label_n_tomos.setText('# of Tomos: ')
        self.label_n_slices.setText('Axial Slices: ')
        self.label_TomoSteps.setText('Tomo Steps: ')
        self.label_StepDur.setText('Step Duration (s): ')
        self.label_AcqDur.setText('Time Per Bed Position (m): ')
        self.label_camera.setText('Camera:')
        self.textBrowser.clear()
        self.lineEdit_activity.setText('')
        self.lineEdit_InjDate.setText('')
        self.lineEdit_InjTime.setText('')
        self.lineEdit_height.setText('')
        self.lineEdit_weight.setText('')
        self.lineEdit_activity.setText('')
        self.lineEdit_description.setText('')
        in_folder=str(self.label_input_dir_path.text())
        print(in_folder)
        #####Fix for nested subdirectories
        filelist=[]
        for (directory,_,files) in os.walk(in_folder):
            for name in files:
                path=os.path.join(directory,name)
                ext=path.split('.')[-1]
                if ext.lower()=='dcm' or ext.lower()=='ima':
                   filelist.append(os.path.join(directory,name))
        #filelist=os.listdir(in_folder)
        print(os.listdir(in_folder))
        print(filelist)
        if len(filelist)==0:
            self.textBrowser.append('No input files detected...')
            return
        datalist=[]
        i=0
        n_tomos=0
        for name in filelist:
            #filepath=os.path.join(in_folder,name)
            filepath=name
            print(filepath)
            dcm=dicom.read_file(filepath)
            if i>0:
                if dcm.StudyInstanceUID!=last_study_uid:
                    self.textBrowser.append('Multiple Studies Detected!\nClear QSPECT Directory and Reload images...')
                    return
            last_study_uid=dcm.StudyInstanceUID
            image_type=dcm.ImageType
            recon=False
            total_counts=dcm.pixel_array.sum()
            for s in image_type:
                if 'recon' in s.lower():
                    recon=True
            if recon==True:
                print 'FOUND!:',image_type
                SPECTcount77=dcm.pixel_array[0:77,:,:].sum()  ###0:77 is pelvis, 155: is head
                if dcm.pixel_array.shape[0]>155:
                    SPECTcount155=dcm.pixel_array[0:155,:,:].sum()
                SPECTcount=dcm.pixel_array.sum()
                n_slices=dcm.pixel_array.shape[0]
                SOPInstandUID=dcm.SOPInstanceUID
                #plt.imshow(dcm.pixel_array[155:,64,:])
                #plt.show()
                Time=dcm.AcquisitionTime
                Date=dcm.AcquisitionDate
                image_array=dcm.pixel_array
            else:
                print 'Not Found:', image_type
                n_tomos+=1
                #try:
                StepDur=float(dcm.RotationInformationSequence[0].ActualFrameDuration)
                #except:
                #    StepDur=float(15000)
                NbStep=int(dcm.RotationInformationSequence[0].NumberOfFramesInRotation)*2
                AcDur=int((StepDur*NbStep)/1000)
                print AcDur
            StudyUID=dcm.StudyInstanceUID
            IPP=dcm.DetectorInformationSequence[0].ImagePositionPatient
            print(IPP)
            
            datalist.append([filepath,recon,StudyUID,float(IPP[2]),total_counts,''])

            i+=1
            if i==1:
                a=1
                #break
        tomolist=[]
        for item in datalist:
            if item[1]==False:
                tomolist.append(item)
        order_arr=numpy.zeros([n_tomos,2])

        AcqH=Time[0:2]
        AcqM=Time[2:4]
        AcqS=Time[4:6]
        #Dose=str(float(DoseMBq)*1000000)
        iyear=Date[0:4]
        iday=Date[6:8]
        imonth=Date[4:6]
        imagetime=datetime(int(iyear),int(imonth),int(iday),int(AcqH),int(AcqM))
        #delta=imagetime-injectiontime
        #DecayTime=delta.days*24*3600.+delta.seconds
        #Day=str(delta.days)
        #hours_pi=int(DecayTime/3600)
        #halflife=579744
        #DecayFactor=exp(log(2)*DecayTime/float(halflife))
        #RemDose=float(Dose)/float(DecayFactor)

        for i in range(n_tomos):
            order_arr[i,0]=i
            order_arr[i,1]=tomolist[i][3]
        sort=numpy.argsort(order_arr[:,1])###array([2,1,0]) that when iterated will yield the tomo series from z-position
                                            ###low to high
        symbia=False
        for item in datalist:
            if item[1]==True:
                for version in dcm.SoftwareVersions:
                    if 'T6' in version:
                        symbia=True
                        print 'Symbia T6 detected...'
        print datalist
        for i in range(len(datalist)):
            if datalist[i][2]!=datalist[0][2]:
                self.textBrowser.append("Non-matching studies, clear QSPECT folder & reload series'")
    
            print datalist[i][2]
        self.label_patient.setText("Patient: "+dcm.PatientName)
        self.label_AcqDate.setText("Acquisition Date: "+iday+'/'+imonth+'/'+iyear[-2:])
        self.label_AcqTime.setText('Acquisition Time: '+AcqH+':'+AcqM)
        self.label_n_tomos.setText('# of Tomos: '+str(n_tomos))
        self.label_n_slices.setText('Axial Slices: '+str(n_slices))
        self.label_TomoSteps.setText('Tomo Steps: '+str(NbStep))
        self.label_StepDur.setText('Step Duration (s): '+str(int(StepDur/1000)))
        self.label_AcqDur.setText('Time Per Bed Position (m): '+str(AcDur/60))
        if symbia==True:
            self.label_camera.setText('Camera: Symbia')
        else:
            self.label_camera.setText('Camera: Intevo')
        try:
            self.lineEdit_height.setText(str(dcm.PatientSize))
        except:
            a=1
        try:
            self.lineEdit_weight.setText(str(dcm.PatientWeight))
        except:
            a=1
        if n_slices>100 and n_tomos<2:
            self.textBrowser.append('Not enough TOMO bed steps for # of axial slices in recon\nPlease recheck input files...')
            return
        if n_slices>170 and n_tomos<3:
            self.textBrowser.append('Not enough TOMO bed steps for # of axial slices in recon\nPlease recheck input files...')
            return

    def clear(self):
        in_folder=str(self.label_input_dir_path.text())
        shutil.rmtree(in_folder)
        try:
            os.mkdir(in_folder)
        except:
            a=1
        self.textBrowser.append('Input files cleared...')
        

    def save_settings(self):
        qspect_ae=self.lineEdit_from_ae.text()
        to_ae=self.lineEdit_to_ae.text()
        ip_address=self.lineEdit_ip.text()
        port=self.lineEdit_port.text()
        transfer=str(self.checkBox_transfer.isChecked())
        delete_in=str(self.checkBox_delete_in.isChecked())
        delete_temp=str(self.checkBox_delete_temp.isChecked())
        save_local=str(self.checkBox_save_local.isChecked())
        #input_dir=self.lineEdit_input_dir.text()
        backup_dir=self.lineEdit_output_dir.text()
        f=open(os.path.join(current_dir,'startup.txt'),'wt')
        f.write('qspect_ae="'+qspect_ae+'"\n')
        f.write('to_ae="'+to_ae+'"\n')
        f.write('ip_address="'+ip_address+'"\n')
        f.write('port="'+port+'"\n')
        f.write('transfer="'+transfer+'"\n')
        f.write('delete_in="'+delete_in+'"\n')
        f.write('delete_temp="'+delete_temp+'"\n')
        f.write('save_local="'+save_local+'"\n')
        #f.write('input_dir="'+input_dir+'"\n')
        f.write('backup_dir="'+backup_dir+'"\n')
        f.close()

    def default_settings(self):
        f=open(os.path.join(current_dir,'backup.txt'))
        exec f.read()
        f.close()
        self.lineEdit_from_ae.setText(qspect_ae)
        self.lineEdit_to_ae.setText(to_ae)
        self.lineEdit_ip.setText(ip_address)
        self.lineEdit_port.setText(port)
        if transfer=="False":
            self.checkBox_transfer.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_transfer.setChecked(QtCore.Qt.Checked)
        if delete_in=="False":
            self.checkBox_delete_in.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_delete_in.setChecked(QtCore.Qt.Checked)
        if delete_temp=="False":
            self.checkBox_delete_temp.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_delete_temp.setChecked(QtCore.Qt.Checked)
        if save_local=="False":
            self.checkBox_save_local.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_save_local.setChecked(QtCore.Qt.Checked)
        #self.lineEdit_input_dir.setText(input_dir)
        self.lineEdit_output_dir.setText(backup_dir)


    def startup_settings(self):
        print 'Loading startup settings...'
        f=open(os.path.join(current_dir,'startup.txt'))
        exec f.read()
        f.close()
        self.lineEdit_from_ae.setText(qspect_ae)
        self.lineEdit_to_ae.setText(to_ae)
        self.lineEdit_ip.setText(ip_address)
        self.lineEdit_port.setText(port)
        if transfer=="False":
            self.checkBox_transfer.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_transfer.setChecked(QtCore.Qt.Checked)
        if delete_in=="False":
            self.checkBox_delete_in.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_delete_in.setChecked(QtCore.Qt.Checked)
        if delete_temp=="False":
            self.checkBox_delete_temp.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_delete_temp.setChecked(QtCore.Qt.Checked)
        if save_local=="False":
            self.checkBox_save_local.setChecked(QtCore.Qt.Unchecked)
        else:
            self.checkBox_save_local.setChecked(QtCore.Qt.Checked)
        #self.label_input_dir_path.setText(input_dir)
        #self.lineEdit_input_dir.setText(input_dir)
        self.lineEdit_output_dir.setText(backup_dir)
        f=open('input_directory.txt','r')
        input_dir=f.readline()
        f.close()
        self.label_input_dir_path.setText(input_dir)


    def main(self):
        self.show()
        self.startup_settings()
        self.reload_ims()
    	
if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    QSGui=qsGui()
    QSGui.main()
    app.exec_()
