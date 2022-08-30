import FreeCAD
import FreeCADGui
import Fem
import os.path
import shutil
from fembygen import Common
import csv
import numpy as np
import itertools
import PySide

def makeGenerate():
    try:
        obj=FreeCAD.ActiveDocument.Generate
        obj.isValid()
    except:
        obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Generate")
        FreeCAD.ActiveDocument.Generative_Design.addObject(obj)
    Generate(obj)
    if FreeCAD.GuiUp:
        ViewProviderGen(obj.ViewObject)
    return obj


class Generate:
    """ Finite Element Analysis """
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Generate"
        self.initProperties(obj)

    def initProperties(self, obj):
        # obj.supportedProperties()
        # ['App::PropertyBool', 'App::PropertyBoolList', 'App::PropertyFloat', 'App::PropertyFloatList',
        #  'App::PropertyFloatConstraint', 'App::PropertyPrecision', 'App::PropertyQuantity',
        #  'App::PropertyQuantityConstraint', 'App::PropertyAngle', 'App::PropertyDistance', 'App::PropertyLength',
        #  'App::PropertyArea', 'App::PropertyVolume', 'App::PropertySpeed', 'App::PropertyAcceleration',
        #  'App::PropertyForce', 'App::PropertyPressure', 'App::PropertyInteger', 'App::PropertyIntegerConstraint',
        #  'App::PropertyPercent', 'App::PropertyEnumeration', 'App::PropertyIntegerList', 'App::PropertyIntegerSet',
        #  'App::PropertyMap', 'App::PropertyString', 'App::PropertyUUID', 'App::PropertyFont',
        #  'App::PropertyStringList', 'App::PropertyLink', 'App::PropertyLinkChild', 'App::PropertyLinkGlobal',
        #  'App::PropertyLinkSub', 'App::PropertyLinkSubChild', 'App::PropertyLinkSubGlobal', 'App::PropertyLinkList',
        #  'App::PropertyLinkListChild', 'App::PropertyLinkListGlobal', 'App::PropertyLinkSubList',
        #  'App::PropertyLinkSubListChild', 'App::PropertyLinkSubListGlobal', 'App::PropertyMatrix',
        #  'App::PropertyVector', 'App::PropertyVectorDistance', 'App::PropertyPosition', 'App::PropertyDirection',
        #  'App::PropertyVectorList', 'App::PropertyPlacement', 'App::PropertyPlacementList',
        #  'App::PropertyPlacementLink', 'App::PropertyColor', 'App::PropertyColorList', 'App::PropertyMaterial',
        #  'App::PropertyMaterialList', 'App::PropertyPath', 'App::PropertyFile', 'App::PropertyFileIncluded',
        #  'App::PropertyPythonObject', 'App::PropertyExpressionEngine', 'Part::PropertyPartShape',
        #  'Part::PropertyGeometryList', 'Part::PropertyShapeHistory', 'Part::PropertyFilletEdges',
        #  'Fem::PropertyFemMesh', 'Fem::PropertyPostDataObject']
        pass



class GenerateCommand():
    """Produce part generations"""

    def GetResources(self):
        return {'Pixmap': 'fembygen/Generate.svg',  # the name of a svg file available in the resources
                'Accel': "Shift+G",  # a default shortcut (optional)
                'MenuText': "Generate",
                'ToolTip': "Produce part generations"}

    def Activated(self):
        obj=makeGenerate()
        # panel = GeneratePanel(obj)
        # FreeCADGui.Control.showDialog(panel)
        doc = FreeCADGui.ActiveDocument
        if not doc.getInEdit():
            doc.setEdit(obj.ViewObject.Object.Name)
        else:
            FreeCAD.Console.PrintError('Existing task dialog already open\n')
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return FreeCAD.ActiveDocument is not None


class GeneratePanel():
    def __init__(self, object):

        self.obj=object
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/FEMbyGEN/fembygen/Generate.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(
            FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        readyText = "Ready"
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

        # Connect the button procedures
        self.form.generateButton.clicked.connect(self.generateParts)
        self.form.viewGenButton.clicked.connect(self.viewGeneration)
        self.form.deleteGensButton.clicked.connect(self.deleteGenerations)
        self.form.nextGen.clicked.connect(lambda: self.nextG(numGens))
        self.form.previousGen.clicked.connect(
            lambda: self.previousG(numGens))
        self.updateParametersTable()
        
    def meshing(self, doc):
            # Remeshing new generation
            if doc.Analysis.Content.find("Netgen") > 0:
                mesh = doc.FEMMeshNetgen
                mesh.FemMesh = Fem.FemMesh()  # cleaning old meshes
                mesh.recompute()
            elif doc.Analysis.Content.find("Gmsh") > 0:
                from femmesh.gmshtools import GmshTools as gt
                mesh = doc.FEMMeshGmsh
                mesh.FemMesh = Fem.FemMesh()  # cleaning old meshes
                gmsh_mesh = gt(mesh)
                gmsh_mesh.create_mesh()

    def generateParts(self):
        doc = FreeCAD.ActiveDocument
        doc.save()  # saving the prepared masterfile
        docPath = doc.FileName
        docName = doc.Name

        # Getting spreadsheet from FreeCAD
        self.paramNames = []
        mins = []
        maxs = []
        numberofgen = []
        self.detection = []
        self.inumber = []

        # Getting number of parameters
        try:
            for i in range(99):
                self.detection.append(doc.Parameters.get(f'C{i+2}'))
        except:
            self.inumber.append(i)

        self.param = []

        #  Getting datas from Spreadsheet
        for i in range(self.inumber[0]):
            self.paramNames.append(doc.Parameters.get(f'B{i+2}'))
            mins = float(doc.Parameters.get(f'C{i+2}'))
            maxs = float(doc.Parameters.get(f'D{i+2}'))
            numberofgen = int(doc.Parameters.get(f'E{i+2}'))
            self.param.append(np.linspace(mins, maxs, numberofgen))

        self.form.progressBar.setStyleSheet("QProgressBar::chunk "
                    "{"
                    "background-color: green;"
                  "}")
        # Combination of all parameters
        self.numgenerations = list(itertools.product(*self.param))
        print(self.form)
        for i in range(len(self.numgenerations)):
            # Regenerate the part and save generation as FreeCAD doc
            try:
                os.mkdir(self.workingDir + f"/Gen{i+1}")
            except:
                print(
                    f"Please delete earlier generations: Gen{i+1} already exist in the folder")
                self.form.progressBar.setValue(100)
                self.form.progressBar.setStyleSheet("QProgressBar::chunk "
                    "{"
                    "background-color: red;"
                  "}")
                self.form.readyLabel.setText("Delete earlier generations")
                return

            filename = f"Gen{i+1}.FCStd"
            filePath = self.workingDir + f"/Gen{i+1}/" + filename
            shutil.copy(docPath, filePath)
            shutil.copy(filePath, filePath+".backup")

            doc=FreeCAD.open(filePath, hidden=True)

            # Produce part generation
            for k in range(self.inumber[0]):
                doc.Parameters.set(
                    f'C{k+2}', f'{self.numgenerations[i][k]}')
                doc.Parameters.clear(f'D1:D{k+2}')
                doc.Parameters.clear(f'E1:E{k+2}')
            doc.recompute()

            self.meshing(doc)
            FreeCAD.closeDocument(filename[:-6])
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
        for i in range(1, numGens+1):
            # Delete analysis directories
            try:
                shutil.rmtree(self.workingDir + f"/Gen{i}/")
                print(self.workingDir + f"/Gen{i}/ deleted")
            except FileNotFoundError:
                print("INFO: Generation " + str(i) +
                      " analysis data not found")
                pass
            except:
                print(
                    "Error while trying to delete analysis folder for generation " + str(i))

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
        while os.path.isdir(self.workingDir + "/Gen" + str(numGens)):
            numGens += 1
        self.resetViewControls(numGens-1)

        return numGens-1

    def saveGenParamsToFile(self):
        filePath = self.workingDir + "/GeneratedParameters.txt"
        with open(filePath, "w", newline='') as my_csv:
            csvWriter = csv.writer(my_csv, delimiter=',')
            csvWriter.writerow(self.paramNames)
            csvWriter.writerows(self.numgenerations)

    def nextG(self, numGens):
        index = self.form.selectGenBox.currentIndex()
        if index >= numGens-1:
            index = -1
        self.form.selectGenBox.setCurrentIndex(index+1)
        self.viewGeneration()

    def previousG(self, numGens):
        index = self.form.selectGenBox.currentIndex()
        if index <= 0:
            index = numGens
        self.form.selectGenBox.setCurrentIndex(index-1)
        self.viewGeneration()

    def viewGeneration(self):
        # Close the generation that the user might be viewing previously
        if self.selectedGen > 0:
            docName = f"Gen{self.selectedGen}"
            FreeCAD.closeDocument(docName)

        # Find which generation is selected in the combo box
        self.selectedGen = self.form.selectGenBox.currentText()
        self.selectedGen = int(str(self.selectedGen).split()[-1])

        # Open the generation
        docPath = self.workingDir + \
            f"/Gen{self.selectedGen}/Gen{self.selectedGen}.FCStd"
        docName = f"Gen{self.selectedGen}"
        FreeCAD.open(docPath)
        FreeCAD.setActiveDocument(docName)

    def resetViewControls(self, numGens):
        comboBoxItems = []

        if numGens > 0:
            self.form.viewGenButton.setEnabled(True)
            self.form.selectGenBox.setEnabled(True)
            self.form.nextGen.setEnabled(True)
            self.form.previousGen.setEnabled(True)

            for i in range(1, numGens+1):
                comboBoxItems.append("Generation " + str(i))

            self.form.selectGenBox.clear()
            self.form.selectGenBox.addItems(comboBoxItems)
        else:
            self.form.viewGenButton.setEnabled(False)
            self.form.selectGenBox.setEnabled(False)
            self.form.nextGen.setEnabled(False)
            self.form.previousGen.setEnabled(False)
            self.form.selectGenBox.clear()

    def updateParametersTable(self):
        tableModel = Common.GenTableModel(
            self.form, self.parameterValues, self.parameterNames)
        tableModel.layoutChanged.emit()
        self.form.parametersTable.setModel(tableModel)
        self.form.parametersTable.clicked.connect(Common.showGen)
    
    def accept(self):
        doc = FreeCADGui.getDocument(self.obj.Document)
        doc.resetEdit()
        doc.Document.recompute()


    def reject(self):
        doc = FreeCADGui.getDocument(self.obj.Document)
        doc.resetEdit()

class ViewProviderGen:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        icon_path = 'fembygen/Generate.svg'
        return icon_path

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

    def updateData(self, obj, prop):
        return

    def onChanged(self, vobj, prop):
        return

    def doubleClicked(self, vobj):
        doc = FreeCADGui.getDocument(vobj.Object.Document)
        if not doc.getInEdit():
            doc.setEdit(vobj.Object.Name)
        else:
            FreeCAD.Console.PrintError('Existing task dialog already open\n')
        return True

    def setEdit(self, vobj, mode):
        taskd =  GeneratePanel(vobj)
        taskd.obj = vobj.Object
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        FreeCADGui.Control.closeDialog()
        return

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

FreeCADGui.addCommand('Generate', GenerateCommand())
