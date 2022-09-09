import FreeCAD
import FreeCADGui
import PySide
import os.path
import numpy as np
from fembygen import Common
import glob


def makeResult():
    try:
        obj = FreeCAD.ActiveDocument.Results
        obj.isValid()
    except:
        obj = FreeCAD.ActiveDocument.addObject(
            "App::DocumentObjectGroupPython", "Results")
        FreeCAD.ActiveDocument.Generative_Design.addObject(obj)
    Result(obj)
    if FreeCAD.GuiUp:
        ViewProviderResult(obj.ViewObject)
    return obj


class Result:
    """ The CFD Physics Model """

    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "Result"
        self.initProperties(obj)
        obj.FEAMetrics = []

    def initProperties(self, obj):
        try:
            obj.addProperty("App::PropertyPythonObject", "FEAMetrics", "Base",
                            "Result lists")
        except:
            pass


class ResultsCommand():
    """Show results of analysed generations"""

    def GetResources(self):
        return {'Pixmap': os.path.join(FreeCAD.getUserAppDataDir() +'Mod/FEMbyGEN/fembygen/Results.svg'),  # the name of a svg file available in the resources
                'Accel': "Shift+R",  # a default shortcut (optional)
                'MenuText': "Show Results",
                'ToolTip': "Show results of analysed generations"}

    def Activated(self):
        obj = makeResult()
        doc = FreeCADGui.getDocument(obj.ViewObject.Object.Document)
        if not doc.getInEdit():
            doc.setEdit(obj.ViewObject.Object.Name)
        else:
            FreeCAD.Console.PrintError('Existing task dialog already open\n')
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return FreeCAD.ActiveDocument is not None


class ResultsPanel:
    def __init__(self, object):
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/FEMbyGEN/fembygen/Results.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(
            object.Object.Document.FileName.split('/')[0:-1])
        self.numGenerationsi = Common.checkGenerations(self.workingDir)
        self.obj = object

        self.doc= object.Object.Document
        if self.doc.Results.FEAMetrics == []:
            FreeCAD.Console.PrintMessage("Calculating metrics...")
            self.calcAndSaveFEAMetrics()
            FreeCAD.open(object.Object.Document.FileName)
        # Load metrics from file
        table = self.doc.Results.FEAMetrics

        # Split into header and table data, then update table
        self.metricNames = table[0]
        self.metrics = table[1:]

        # Add configuration controls
        self.addConfigControls()

        self.updateResultsTable()
        # self.doc.save()

    def updateResultsTable(self):
        header = self.metricNames
        items = self.metrics
        stats, numAnalysed = Common.checkAnalyses(self.doc)
        gen, lc= len(stats), len(stats[0])
        index=[]
        for i in range(gen):
            for j in range(lc):
                index.append([f"{i+1}.{j+1}"])
        print(index)
        print(len(index))
        table=np.hstack((index,items))
        table=table.tolist()
        header=["Gen"]+header

        colours = self.generateColourScalesFromMetrics()
        self.tableModel = Common.GenTableModel(
            self.form, table, header, colours)
        self.form.resultsTable.setModel(self.tableModel)
        self.form.resultsTable.resizeColumnsToContents()
        self.form.resultsTable.horizontalHeader().setResizeMode(PySide.QtGui.QHeaderView.ResizeToContents)

        self.form.resultsTable.clicked.connect(self.showGen)

    def showGen(self,item):
        global old
        old = FreeCAD.ActiveDocument.Name
        if old[:3] == "Gen":
            FreeCAD.closeDocument(old)
        if item=="close":
            return
        index = item.row()//self.doc.FEA.NumberOfLoadCase+1
        # Open the generation
        workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        docPath = workingDir + \
            f"/Gen{index}/Gen{index}.FCStd"
        docName = f"Gen{index}"
        FreeCAD.open(docPath)
        FreeCAD.setActiveDocument(docName)

    def addConfigControls(self):
        self.configControls = []

        for name in self.metricNames:
            # Create instances of controls
            paramCheck = PySide.QtGui.QCheckBox(name, self.form)
            redGreenRadio = PySide.QtGui.QRadioButton(self.form)
            gradientRadio = PySide.QtGui.QRadioButton(self.form)
            radioGroup = PySide.QtGui.QButtonGroup()
            minBox = PySide.QtGui.QDoubleSpinBox(self.form)
            maxBox = PySide.QtGui.QDoubleSpinBox(self.form)

            # Configure control parameters
            paramCheck.setChecked(True)
            minBox.setMaximum(999999.99)
            maxBox.setMaximum(999999.99)
            gradientRadio.setChecked(True)
            radioGroup.addButton(redGreenRadio)
            radioGroup.addButton(gradientRadio)

            (minVal, maxVal) = self.getMetricValueRange(name)
            minBox.setValue(minVal)
            maxBox.setValue(maxVal)

            # Create and link callback functions
            def valueChanged(value):
                colours = self.generateColourScalesFromMetrics()
                self.updateResultsTableColours(colours)
                pass

            minBox.valueChanged.connect(valueChanged)
            maxBox.valueChanged.connect(valueChanged)

            controls = [paramCheck, redGreenRadio,
                        gradientRadio, radioGroup, minBox, maxBox]
            self.configControls.append(controls)

            # Add widgets to form
            configGrid = self.form.configGrid
            numRows = configGrid.rowCount()
            configGrid.addWidget(paramCheck, numRows, 0)
            configGrid.addWidget(redGreenRadio, numRows, 1)
            configGrid.addWidget(gradientRadio, numRows, 2)
            configGrid.addWidget(minBox, numRows, 3)
            configGrid.addWidget(maxBox, numRows, 4)

    def updateResultsTableColours(self, colours):
        self.tableModel.updateColours(colours)
        # self.form.resultsTable.update()
        self.form.resultsTable.activated.emit(1)

    def getMetricValueRange(self, metricName):
        i = self.metricNames.index(metricName)
        height = len(self.metrics)
        # Gather all the values in a column
        values = [self.metrics[y][i] for y in range(height)]

        # Make new column of values that doesn't include numbers
        vals = []
        for item in values:
            try:
                vals.append(float(item))
            except ValueError:
                pass

        # Calculate value range
        minVal = min(vals)
        maxVal = max(vals)
        return (minVal, maxVal)

    def generateColourScalesFromMetrics(self):
        width = len(self.metricNames)
        height = len(self.metrics)
        colours = [[PySide.QtGui.QColor("white")
                    for x in range(width)] for y in range(height)]

        items = self.metrics

        for i in range(width):
            # Gather all the values in a column
            values = [items[y][i] for y in range(height)]

            # Make new column of values that doesn't include numbers
            vals = []
            for item in values:
                try:
                    vals.append(float(item))
                except ValueError:
                    pass

            # Calculate value range
            minVal = self.configControls[i][4].value()
            maxVal = self.configControls[i][5].value()

            # Calculate value range to calibrate colour scale
            valRange = maxVal - minVal

            for j, value in enumerate(values):
                try:
                    value = float(value)
                    if value > maxVal:
                        # If value is greater than maximum, set it to full intensity
                        normVal = 1.0
                    else:
                        if valRange != 0:
                            normVal = (value - minVal) / valRange
                        else:
                            normVal = 0

                    hue = 0.4
                    col = Common.hsvToRgb(hue, normVal, 1.0)
                    col = [int(col[0]*255), int(col[1]*255), int(col[2]*255)]
                    colours[j][i] = PySide.QtGui.QColor(
                        col[0], col[1], col[2], 255)
                except ValueError:
                    # Item was not a number. Likely a string because an error occured for analysis in this row
                    # so colour it pink
                    colours[j][i] = PySide.QtGui.QColor(230, 184, 184, 255)
                    pass

        return colours

    def calcAndSaveFEAMetrics(self):
        workingDir = '/'.join(self.doc.FileName.split('/')[0:-1])
        numGenerations = Common.checkGenerations(workingDir)
        if numGenerations > 0:
            table = [["Volume[mm^3]", "Internal Energy[Joule]", "Standard Dev. of En. Den","Mean Stress[MPa]", "Max Stress[MPa]", "Max Disp[mm]"]]

            result = self.calculateFEAMetric()
            table += result
            self.doc.Results.FEAMetrics = table

    def calculateFEAMetric(self):
        workingDir = '/'.join(self.doc.FileName.split('/')[0:-1])
        statuses,numgAnly,lc = Common.searchAnalysed(self.doc)
        result=[]
        for i, row in enumerate(statuses):   #TODO only for status is anlyzed other cases it will be none
            filename = f"Gen{i+1}"
            filePath = workingDir + f"/Gen{i+1}/{filename}.FCStd"
            for j, value in enumerate(row):
                resultPath= workingDir + f"/Gen{i+1}/loadCase{j+1}/" 
                doc = FreeCAD.open(filePath, hidden=True)
                mean=np.mean(doc.CCX_Results.vonMises)
                max=np.max(doc.CCX_Results.vonMises)
                maxDisp=np.max(doc.CCX_Results.DisplacementLengths)

                intData, totalInt, volData, totalVol, denData =self.IntEnergyandVolume(resultPath)
                energyDenStd=np.std(denData)

                result.append([f"{totalVol:.2e}", f"{totalInt:.2e}", f"{energyDenStd:.2e}", f"{mean:.2e}",
                                f"{max:.2e}",f"{maxDisp:.2e}"])

            self.getResultsToMaster(doc, i+1, j+1)
            FreeCAD.closeDocument(filename)
        return result

    def getResultsToMaster(self,doc, GenNo, loadNo):
                doc.CCX_Results.Label=f"Gen{GenNo}_Results"
                doc.ResultMesh.Label=f"Gen{GenNo}_Mesh"
                self.doc.copyObject(doc.CCX_Results, False)
                self.doc.copyObject(doc.ResultMesh, False)
                self.doc.getObjectsByLabel(f"Gen{GenNo}_Results")[0].Mesh=self.doc.getObjectsByLabel(f"Gen{GenNo}_Mesh")[0]
                self.doc.Results.addObject(self.doc.getObjectsByLabel(f"Gen{GenNo}_Results")[0])
                self.doc.getObjectsByLabel(f"Gen{GenNo}_Results")[0].Visibility=False
                self.doc.getObjectsByLabel(f"Gen{GenNo}_Mesh")[0].Visibility=False

    def IntEnergyandVolume(self,resultPath):
        """to get volume information and internal energy information from dat file"""
        name= glob.glob(resultPath + "*.dat")
        with open(name[0],"r") as datfile:
            text=datfile.read()
            
        # getting elemental internal energy results
        internal = text.find(" internal energy")
        internalStart =text.find("\n",internal)+2
        internalEnd = text.find(" total internal", internalStart)-1
        intData=np.fromstring(text[internalStart:internalEnd],sep="\n")
        intData=intData.reshape(len(intData)//2,2)

        # getting total internal energy
        totalIntStart=text.find("\n", internalEnd+1)+1
        totalIntEnd=text.find("volume", totalIntStart)-1
        totalInt=float(text[totalIntStart:totalIntEnd])

        # getting elemnts volume
        volStart=text.find("\n", totalIntEnd+1)+1
        volEnd=text.find("total volume", totalIntStart)-1
        volData=np.fromstring(text[volStart:volEnd],sep="\n")
        volData=volData.reshape(len(volData)//2,2)

        # getting total volume
        totalVolStart=text.find("\n", volEnd+1)+1
        totalVolEnd=text.find("internal energy density", totalVolStart)-1
        totalVol=float(text[totalVolStart:totalVolEnd])
        
        # getting density from file
        denStart=text.find("\n", totalVolEnd+1)+1
        denEnd=-1 # text.find("total volume", totalVolStart)
        denData=np.fromstring(text[denStart:denEnd],sep="\n")
        denData=denData.reshape(len(denData)//3,3)
        
        return intData[:,1]*1000, totalInt*1000, volData[:,1], totalVol, denData[:,2]*1000 # Joule , Joule, mm^3, mm^3, Joule

    def accept(self):
        doc = FreeCADGui.getDocument(self.obj.Document)
        doc.resetEdit()
        doc.Document.recompute()
        self.showGen("close") #closes the gen file If a generated file opened to check before

    def reject(self):
        doc = FreeCADGui.getDocument(self.obj.Document)
        doc.resetEdit()
        self.showGen("close") #closes the gen file If a generated file opened to check before


class ViewProviderResult:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        icon_path = os.path.join(FreeCAD.getUserAppDataDir() + 'Mod/FEMbyGEN/fembygen/Results.svg')
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
        taskd = ResultsPanel(vobj)
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


FreeCADGui.addCommand('Results', ResultsCommand())
