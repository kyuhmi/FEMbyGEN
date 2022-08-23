from genericpath import isdir
import FreeCAD, FreeCADGui, Part, Mesh, Fem
import os.path
import shutil
from random import random
import PySide
import operator
from fembygen import Common
import csv
import numpy as np
import itertools

class GenerateCommand():
    """Produce part generations"""

    def GetResources(self):
        return {'Pixmap'  : 'fembygen/Generate.svg', # the name of a svg file available in the resources
                'Accel' : "Shift+G", # a default shortcut (optional)
                'MenuText': "Generate",
                'ToolTip' : "Produce part generations"}

    def Activated(self):
        panel = GeneratePanel()
        FreeCADGui.Control.showDialog(panel)
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
        try:
            self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        except:
            print("Please open a file and create parameters spreadsheet by initialize button")
        readyText="Ready"
        # Data variables for parameter table
        self.parameterNames = []
        self.parameterValues = []  
        
        # First check if generations have already been made from GeneratedParameters.txt
        (self.parameterNames, self.parameterValues) = Common.checkGenParameters()
       
        # Check if any generations have been made already, and up to what number
  
        numGens = self.checkGenerations()
        
        self.form.numGensLabel.setText(f"{numGens} generations produced")
        self.form.readyLabel.setText(readyText)

        self.selectedGen = -1

        ## Connect the button procedures
        self.form.generateButton.clicked.connect(self.generateParts)
        self.form.viewGenButton.clicked.connect(self.viewGeneration)
        self.form.deleteGensButton.clicked.connect(self.deleteGenerations)
        self.updateParametersTable()

        

    def generateParts(self):
        doc = FreeCAD.ActiveDocument
        doc.save()     #saving the prepared masterfile
        docPath = doc.FileName
        docName = doc.Name

        # Getting spreadsheet from FreeCAD
        self.paramNames = []
        mins = []
        maxs = []
        numberofgen=[]
        self.detection=[]
        self.inumber=[]
        
        # Getting number of parameters
        try:
            for i in range(99):
                self.detection.append(doc.Parameters.get(f'C{i+2}'))
        except:          
            self.inumber.append(i)
       
        self.param=[] 
        
        #  Getting datas from Spreadsheet
        for i in range(self.inumber[0]):
            self.paramNames.append(doc.Parameters.get(f'B{i+2}'))
            mins=float(doc.Parameters.get(f'C{i+2}'))
            maxs=float(doc.Parameters.get(f'D{i+2}'))
            numberofgen=int(doc.Parameters.get(f'E{i+2}'))
            self.param.append(np.linspace(mins,maxs,numberofgen))
        
        # Combination of all parameters
        self.numgenerations=list(itertools.product(*self.param))             
         
        for i in range(len(self.numgenerations)):
            FreeCAD.open(docPath, hidden=True)
            FreeCAD.setActiveDocument(docName)
            doc = FreeCAD.ActiveDocument
            # Produce part generation
            for k in range(self.inumber[0]):
                    
                FreeCAD.activeDocument().Parameters.set(f'C{k+2}',f'{self.numgenerations[i][k]}')
                FreeCAD.activeDocument().Parameters.clear(f'D1:D{k+2}')
                FreeCAD.activeDocument().Parameters.clear(f'E1:E{k+2}')
            doc.recompute()      
            
            # Remeshing new generation
            if doc.Analysis.Content.find("Netgen") >0:
                mesh=FreeCAD.ActiveDocument.FEMMeshNetgen
                mesh.FemMesh = Fem.FemMesh()  #cleaning old meshes
                mesh.recompute()
            elif doc.Analysis.Content.find("Gmsh") >0: 
                from femmesh.gmshtools import GmshTools as gt 
                mesh=FreeCAD.ActiveDocument.FEMMeshGmsh   
                mesh.FemMesh = Fem.FemMesh()   #cleaning old meshes
                gmsh_mesh = gt(mesh)
                gmsh_mesh.create_mesh()
                    
            ## Regenerate the part and save generation as FreeCAD doc
            try:        
                os.mkdir(self.workingDir + f"/Gen{i+1}")
            except:
                print(f"Please delete earlier generations: Gen{i+1} already exist in the folder")

            filename = f"/Gen{i+1}/" + f"Gen{i+1}.FCStd"
 
            filePath = self.workingDir + filename
            FreeCAD.ActiveDocument.saveAs(filePath)
            shutil.copy(filePath,filePath+".backup")
 
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
        (self.parameterNames, self.parameterValues) = Common.checkGenParameters()
        self.updateParametersTable()
        print("Generation done successfully!")

    def deleteGenerations(self):
        print("Deleting...")
        numGens = self.checkGenerations()
        for i in range(1,numGens+1):
            # Delete analysis directories
            try:
                shutil.rmtree(self.workingDir + f"/Gen{i}/")
                print(self.workingDir + f"/Gen{i}/ deleted")
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
        (self.parameterNames, self.parameterValues) = Common.checkGenParameters()
        self.updateParametersTable()

    def checkGenerations(self):
        numGens = 1
        while os.path.isdir(self.workingDir + "/Gen" + str(numGens) ):
            numGens += 1
        self.resetViewControls(numGens-1)

        return numGens-1

    def saveGenParamsToFile(self):
        filePath = self.workingDir + "/GeneratedParameters.txt"
        with open(filePath, "w", newline='') as my_csv:
            csvWriter = csv.writer(my_csv, delimiter=',')
            csvWriter.writerow(self.paramNames)
            csvWriter.writerows(self.numgenerations)


    def viewGeneration(self):
        # Close the generation that the user might be viewing previously
        if self.selectedGen > 0:
            docName = f"Gen{self.selectedGen}" 
            FreeCAD.closeDocument(docName)

        # Find which generation is selected in the combo box
        self.selectedGen = self.form.selectGenBox.currentText()
        self.selectedGen = int(str(self.selectedGen).split()[-1])

        # Open the generation
        docPath = self.workingDir + f"/Gen{self.selectedGen}/Gen{self.selectedGen}.FCStd"
        docName = f"Gen{self.selectedGen}" 
        FreeCAD.open(docPath)
        FreeCAD.setActiveDocument(docName)


    def resetViewControls(self, numGens):
        comboBoxItems = []

        if numGens > 0:
            self.form.viewGenButton.setEnabled(True)
            self.form.selectGenBox.setEnabled(True)

            for i in range(1,numGens+1):
                comboBoxItems.append("Generation " + str(i))

            self.form.selectGenBox.clear()
            self.form.selectGenBox.addItems(comboBoxItems)
        else:
            self.form.viewGenButton.setEnabled(False)
            self.form.selectGenBox.setEnabled(False)
            self.form.selectGenBox.clear()

    def updateParametersTable(self):
        tableModel = Common.GenTableModel(self.form, self.parameterValues, self.parameterNames)
        tableModel.layoutChanged.emit()
        self.form.parametersTable.setModel(tableModel)     

FreeCADGui.addCommand('Generate', GenerateCommand())