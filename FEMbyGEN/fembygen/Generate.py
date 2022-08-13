from genericpath import isdir
import FreeCAD, FreeCADGui, Part, Mesh
import os.path
import shutil
from random import random
import PySide
import operator
from fembygen import Common
import csv
import numpy as np

class GenerateCommand():
    """Produce part generations"""

    def GetResources(self):
        return {'Pixmap'  : 'Generate.svg', # the name of a svg file available in the resources
                'Accel' : "Shift+G", # a default shortcut (optional)
                'MenuText': "Generate",
                'ToolTip' : "Produce part generations"}

    def Activated(self):
        panel = GeneratePanel()
        FreeCADGui.Control.showDialog(panel)
        """Do something here"""
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class GeneratePanel():
    def __init__(self):
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/FEMbyGEN/fembygen/Generate.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        

        # Data variables for parameter table
        self.parameterNames = []
        self.parameterValues = []  
        

        for i in range(3):
            a=FreeCAD.activeDocument().Parameters.get(f'B{i+2}')
            self.parameterNames.append(a)

        for i in range(3):
            b=FreeCAD.activeDocument().Parameters.get(f'C{i+2}')
            self.parameterValues.append(b)

        readyText = "Ready"

        # First check if generations have already been made from GeneratedParameters.txt
        (self.parameterNames, self.parameterValues) = Common.checkGenParameters()
        print(self.parameterNames)
        print(self.parameterValues)
        

        # Check if any generations have been made already, and up to what number
        numGens = self.checkGenerations()

        self.form.numGensLabel.setText(str(numGens) + " generations produced")
        self.form.readyLabel.setText(readyText)
        self.selectedGen = -1

        ## Connect the button procedures
        self.form.generateButton.clicked.connect(self.generateParts)
        self.form.viewGenButton.clicked.connect(self.viewGeneration)
        self.form.deleteGensButton.clicked.connect(self.deleteGenerations)

        self.updateParametersTable()

    def generateParts(self):

        docPath = FreeCAD.ActiveDocument.FileName
        docName = FreeCAD.ActiveDocument.Name


        
        # Getting spreadsheet from FreeCAD
        self.paramsheet=FreeCAD.activeDocument().getObject("Spreadsheet")

        self.paramNames = []
        self.mins = []
        self.maxs = []
        self.numberofgen=[]
        self.numgenerations=[]
        self.detection=[]
        self.inumber=[]
        
        # Getting number of parameters
        try:
            for i in range(99):
                self.detection.append(FreeCAD.activeDocument().Parameters.get(f'C{i+2}'))
        except:          
            self.inumber.append(i)
       
        # self.param=[] 
        
        #  Getting datas from Spreadsheet
        for i in range(self.inumber[0]):
            self.paramNames.append(FreeCAD.activeDocument().Parameters.get(f'B{i+2}'))
            self.mins.append(float(FreeCAD.activeDocument().Parameters.get(f'C{i+2}')))
            self.maxs.append(float(FreeCAD.activeDocument().Parameters.get(f'D{i+2}')))
            self.numberofgen.append(int(FreeCAD.activeDocument().Parameters.get(f'E{i+2}')))
            # self.param.append(np.linspace(self.mins[i],self.maxs[i],self.numberofgen[i]))
        self.a=np.linspace(self.mins[0],self.maxs[0],self.numberofgen[0])
        self.b=np.linspace(self.mins[1],self.maxs[1],self.numberofgen[1])
        self.c=np.linspace(self.mins[2],self.maxs[2],self.numberofgen[2])
        
        # Generating new values
        for i in range(len(self.a)):
            for j in range(len(self.b)):
                for k in range(len(self.c)):
                    numbers=[self.a[i],self.b[j],self.c[k]]
                    self.numgenerations.append(numbers)
                    
            

        
        for i in range(len(self.numgenerations)):
            FreeCAD.open(docPath)
            FreeCAD.setActiveDocument(docName)

            # Produce part generation
            for k in range(self.inumber[0]):
                    
                FreeCAD.activeDocument().Parameters.set(f'C{k+2}',f'{self.numgenerations[i][k]}')
                FreeCAD.activeDocument().Parameters.clear(f'D1:D{k+2}')
                FreeCAD.activeDocument().Parameters.clear(f'E1:E{k+2}')
            FreeCAD.ActiveDocument.recompute()
            
            ## Regenerate the part and save generation as FreeCAD doc

            try:        
                os.mkdir(self.workingDir + f"/Gen{i+1}")
            except:
                print(f"Please delete earlier generations: Gen{i+1} already exist in the folder")

            filename = f"/Gen{i+1}/" + f"Gen{i+1}.FCStd"
 
            filePath = self.workingDir + filename
            FreeCAD.ActiveDocument.saveAs(filePath)
 
            FreeCAD.closeDocument(docName)
        
            # Update progress bar
            progress = ((i+1)/len(self.numgenerations)) * 100
            self.form.progressBar.setValue(progress)

        # Reopen document again once finished
        FreeCAD.open(docPath)

        self.saveGenParamsToFile()
        self.updateParametersTable()

        # Update number of generations produced in window
        numGens = self.checkGenerations()
        self.form.numGensLabel.setText(str(numGens) + " generations produced")
        self.form.readyLabel.setText("Finished")

        print("Generation done successfully!")

    def deleteGenerations(self):
        print("Deleting...")
        numGens = self.checkGenerations()
        for i in range(1,numGens):
            fileName = self.workingDir + f"/Gen{i}/" + f"Gen{i}"
            # print(fileName)
            # # Delete FreeCAD part and STL files
            # try:
            #     os.remove(fileName + ".FCStd")
            # except FileNotFoundError:
            #     print("INFO: Generation " + str(i) + " not found")
            # except:
            #     print("Error while trying to delete files for generation" + str(i))

            # # Delete FreeCAD backup part files
            # try:
            #     os.remove(fileName + ".FCStd1")
            # except FileNotFoundError:
            #     passprint(fileName)
            # # Delete FreeCAD part and STL files
            # try:
            #     os.remove(fileName + ".FCStd")
            # except FileNotFoundError:
            #     print("INFO: Generation " + str(i) + " not found")
            # except:
            #     print("Error while trying to delete files for generation" + str(i))

            # # Delete FreeCAD backup part files
            # try:
            #     os.remove(fileName + ".FCStd1")
            # except FileNotFoundError:
            #     pass
            # except:
            #     print("Error while trying to delete backup part files for generation" + str(i))
            # except:
            #     print("Error while trying to delete backup part files for generation" + str(i))

            # Delete analysis directories
            try:
                shutil.rmtree(self.workingDir + f"/Gen{i}/")
                print(self.workingDir + f"/Gen{i}/ silindi")
            except FileNotFoundError:
                print("INFO: Generation " + str(i) + " analysis data not found")
                pass
            except:
                print("Error while trying to delete analysis folder for generation " + str(i))

        # Delete the GeneratedParameters.txt file
        try:
            os.remove(self.workingDir + "/GeneratedParameters.txt")
        except FileNotFoundError:
            #print("INFO: GeneratedParameters.txt is missing")
            pass
        except:
            print("Error while trying to delete GeneratedParameters.txt")

        # Delete the AnalysisStatus.txt file
        try:
            os.remove(self.workingDir + "/AnalysisStatus.txt")
        except FileNotFoundError:
            #print("INFO: AnalysisStatus.txt is missing")
            pass
        except:
            print("Error while trying to delete AnalysisStatus.txt")

        # Delete the RefinementResults.txt file
        try:
            os.remove(self.workingDir + "/RefinementResults.txt")
        except FileNotFoundError:
            #print("INFO: RefinementResults.txt is missing")
            pass
        except:
            print("Error while trying to delete RefinementResults.txt")

        # Delete the FEAMetrics.npy file
        try:
            os.remove(self.workingDir + "/FEAMetrics.npy")
        except FileNotFoundError:
            #print("INFO: FEAMetrics.npy is missing")
            pass
        except:
            print("Error while trying to delete FEAMetrics.npy")

        # self.updateParametersTable()
        #self.tableModel.updateHeader([])
        #self.tableModel.updateData([None])
        # Refresh the TableView control
        # self.form.parametersTable.clearSelection()
        #self.form.parametersTable.dataChanged.emit(self.index(0, 0), self.index(0, 0))

    def checkGenerations(self):
        numGens = 1
        while os.path.isdir(self.workingDir + "/Gen" + str(numGens) ):
            numGens += 1


        self.resetViewControls(numGens)

        return numGens

    def saveGenParamsToFile(self):
        filePath = self.workingDir + "/GeneratedParameters.txt"
        with open(filePath, "w", newline='') as my_csv:
            csvWriter = csv.writer(my_csv, delimiter=',')
            csvWriter.writerow(self.paramNames)
            csvWriter.writerows(self.numgenerations)


    def viewGeneration(self):
        # Close the generation that the user might be viewing previously
        if self.selectedGen >= 0:
            docName = "Gen" +str(self.selectedGen)
            FreeCAD.closeDocument(docName)

        # Find which generation is selected in the combo box
        self.selectedGen = self.form.selectGenBox.currentText()
        self.selectedGen = int(str(self.selectedGen).split()[-1])

        # Open the generation
        docPath = self.workingDir + "/Gen" + str(self.selectedGen) + ".FCStd"
        docName = "Gen" +str(self.selectedGen)
        FreeCAD.open(docPath)
        FreeCAD.setActiveDocument(docName)


    def resetViewControls(self, numGens):
        comboBoxItems = []

        if numGens > 0:
            self.form.viewGenButton.setEnabled(True)
            self.form.selectGenBox.setEnabled(True)

            for i in range(numGens):
                comboBoxItems.append("Generation " + str(i))

            self.form.selectGenBox.clear()
            self.form.selectGenBox.addItems(comboBoxItems)
        else:
            self.form.viewGenButton.setEnabled(False)
            self.form.selectGenBox.setEnabled(False)
            self.form.selectGenBox.clear()

    def updateParametersTable(self):
        self.tableModel = Common.GenTableModel(self.form, self.parameterValues, self.parameterNames)
        self.form.parametersTable.setModel(self.tableModel)
        #self.form.parametersTable.resizeColumnsToContents()

    def getStandardButtons(self, *args):
        #return PySide.QtWidgets.QDialogButtonBox.Ok
        #return QDialogButtonBox.Close | QDialogButtonBox.Ok
        pass

FreeCADGui.addCommand('Generate', GenerateCommand())