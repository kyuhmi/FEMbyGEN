import FreeCAD
import FreeCADGui
import os.path
from fembygen import Common
import shutil
import os
import PySide


def makeFEA():
    try:
        obj=FreeCAD.ActiveDocument.FEA
        obj.isValid()
    except:
        obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "FEA")
        FreeCAD.ActiveDocument.Generative_Design.addObject(obj)
    FEA(obj)
    if FreeCAD.GuiUp:
        ViewProviderFEA(obj.ViewObject)
    return obj


class FEA:
    """ Finite Element Analysis """
    def __init__(self, obj):
        obj.Proxy = self
        self.Type = "FEA"
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

class FEACommand():
    """Perform FEA on generated parts"""

    def GetResources(self):
        return {'Pixmap': 'fembygen/FEA.svg',  # the name of a svg file available in the resources
                'Accel': "Shift+A",  # a default shortcut (optional)
                'MenuText': "FEA Generations",
                'ToolTip': "Perform FEA on generated parts"}

    def Activated(self):
        obj=makeFEA()
        # panel = ResultsPanel(obj)
        # FreeCADGui.Control.showDialog(panel)
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


class FEAPanel:
    def __init__(self, object):
        # Creating tree view object
        self.obj=object
        # this will create a Qt widget from our ui file
        guiPath = FreeCAD.getUserAppDataDir() + "Mod/FEMbyGEN/fembygen/PerformFEA.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(
            FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        self.numGenerations = Common.checkGenerations()
        (self.stats, self.numAnalysed) = Common.checkAnalyses()

        # Update status labels and table
        self.form.genCountLabel.setText(
            "There are " + str(self.numGenerations) + " generations")
        self.form.analysedCountLabel.setText(
            str(self.numAnalysed) + " successful analyses")
        self.updateAnalysisTable()

        # Link callback procedures
        self.form.startFEAButton.clicked.connect(self.FEAGenerations)
        self.form.deleteAnalyses.clicked.connect(self.deleteGenerations)
    
    def deleteGenerations(self):
        print("Deleting...")
        numGens = Common.checkGenerations()
        for i in range(1, numGens+1):
            fileName = self.workingDir + f"/Gen{i}/"
            files = os.listdir(fileName)
            for j in files:

                if j[-6:] == "backup":
                    pass
                else:
                    os.remove(self.workingDir+f"/Gen{i}/"+j)
            shutil.copyfile(
                self.workingDir+f"/Gen{i}/Gen{i}.FCStd.backup", self.workingDir+f"/Gen{i}/Gen{i}.FCStd")
        self.updateAnalysisTable()

    def FEAGenerations(self):
        print("Analysis starting")
        for i in range(self.numGenerations):
            # Open generated part
            partName = f"Gen{i+1}"
            filePath = self.workingDir + f"/Gen{i+1}/Gen{i+1}.FCStd"
            FreeCAD.open(filePath)
            FreeCAD.setActiveDocument(partName)

            # Run FEA solver on generation
            self.performFEA(i+1)

            # Close generated part
            FreeCAD.closeDocument(partName)

            # Update progress bar
            progress = ((i+1)/self.numGenerations) * 100
            self.form.progressBar.setValue(progress)

        (self.stats, self.numAnalysed) = Common.writeAnalysisStatusToFile()

        self.updateAnalysisTable()

    def updateAnalysisTable(self):
        # Make a header and table with one more column, because otherwise the table object will split each character
        # into its own cell
        header = ["Status"]
        table = []

        for i in range(len(self.stats)):
            table.append([self.stats[i]])

        colours = []
        for status in self.stats:
            white = PySide.QtGui.QColor("white")
            colour = white
            if status == "Analysed":
                # green
                colour = PySide.QtGui.QColor(114, 242, 73, 255)
            elif status == "Not analysed":
                # yellow
                colour = PySide.QtGui.QColor(207, 184, 12, 255)
            elif status == "Failed":
                # red/pink
                colour = PySide.QtGui.QColor(250, 100, 100, 255)
            colours.append([colour, white])

        tableModel = Common.GenTableModel(
            self.form, table, header, colours=colours)
        tableModel.layoutChanged.emit()
        self.form.tableView.setModel(tableModel)
        self.form.tableView.clicked.connect(Common.showGen)


    def performFEA(self, GenerationNumber):
        doc = FreeCAD.ActiveDocument
        doc.recompute()
        # run the analysis step by step
        from femtools import ccxtools
        fea = ccxtools.FemToolsCcx()
        fea.update_objects()
        fea.setup_working_dir(self.workingDir+f"/Gen{GenerationNumber}")
        fea.setup_ccx()
        message = fea.check_prerequisites()
        if not message:
            fea.purge_results()
            fea.write_inp_file()
            fea.ccx_run()
            fea.load_results()
        else:
            FreeCAD.Console.PrintError(
                "Houston, we have a problem! {}\n".format(message))  # in report view
            print("Houston, we have a problem! {}\n".format(
                message))  # in python console
    
        # save FEA results
        doc.save()
    def accept(self):
        doc = FreeCADGui.getDocument(self.obj.Document)
        doc.resetEdit()
        doc.Document.recompute()


    def reject(self):
        doc = FreeCADGui.getDocument(self.obj.Document)
        doc.resetEdit()


class ViewProviderFEA:
    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        icon_path = 'fembygen/FEA.svg'
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
        taskd =  FEAPanel(vobj)
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

FreeCADGui.addCommand('FEA', FEACommand())
