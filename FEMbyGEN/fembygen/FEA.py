import FreeCAD, FreeCADGui, Part, Fem
import os.path
from fembygen import FRDParser
import PySide, operator
import time
from fembygen import Common
import shutil
import os

class FEACommand():
    """Perform FEA on generated parts"""

    def GetResources(self):
        return {'Pixmap'  : 'fembygen/FEA.svg',  # the name of a svg file available in the resources
                'Accel' : "Shift+A",  # a default shortcut (optional)
                'MenuText': "FEA Generations",
                'ToolTip' : "Perform FEA on generated parts"}

    def Activated(self):
        panel = FEAPanel()
        FreeCADGui.Control.showDialog(panel)
        return

    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class FEAPanel:
    def __init__(self):
        # this will create a Qt widget from our ui file

        guiPath = FreeCAD.getUserAppDataDir() + "Mod/FEMbyGEN/fembygen/PerformFEA.ui"
        self.form = FreeCADGui.PySideUic.loadUi(guiPath)
        self.workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        self.numGenerations = self.checkGenerations()
        (self.stats, self.numAnalysed) = Common.checkAnalyses()

        # Update status labels and table
        self.form.genCountLabel.setText("There are " + str(self.numGenerations) + " generations")
        self.form.analysedCountLabel.setText(str(self.numAnalysed) + " successful analyses")
        self.updateAnalysisTable()

        # Link callback procedures
        self.form.startFEAButton.clicked.connect(self.FEAGenerations)
        self.form.deleteAnalyses.clicked.connect(self.deleteGenerations)

    def accept(self):
        pass

    def checkGenerations(self):
        numGens = 1
        print(self.workingDir)
        while os.path.isdir(self.workingDir + "/Gen" + str(numGens) ):
            numGens += 1
        return numGens-1


    def deleteGenerations(self):
        print("Deleting...")
        numGens = self.checkGenerations()
        for i in range(1,numGens+1):
            fileName = self.workingDir + f"/Gen{i}/"
            files=os.listdir(fileName)
            for j in files:

                if  j[-6:]=="backup":
                    pass
                else:
                    os.remove(self.workingDir+f"/Gen{i}/"+j)
            shutil.copyfile(self.workingDir+f"/Gen{i}/Gen{i}.FCStd.backup",self.workingDir+f"/Gen{i}/Gen{i}.FCStd")
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
            performFEA(i+1)

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
        header = ["Status", ""]
        table = []
        for i in range(len(self.stats)):
            table.append([self.stats[i], ""])

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

        tableModel = Common.GenTableModel(self.form, table, header, colours=colours)
        tableModel.layoutChanged.emit()
        self.form.tableView.setModel(tableModel)


def performFEA(GenerationNumber):
    doc = FreeCAD.ActiveDocument
    doc.recompute()
    workingDir = '/'.join(doc.FileName.split('/')[0:-1])
    # run the analysis step by step
    from femtools import ccxtools
    fea = ccxtools.FemToolsCcx()
    fea.update_objects()
    fea.setup_working_dir(workingDir)
    fea.setup_ccx()
    message = fea.check_prerequisites()
    if not message:
        fea.purge_results()
        fea.write_inp_file()
        fea.ccx_run()
        fea.load_results()
    else:
        FreeCAD.Console.PrintError("Houston, we have a problem! {}\n".format(message))  # in report view
        print("Houston, we have a problem! {}\n".format(message))  # in python console

    # save FEA results
    doc.save()

def hsvToRgb(h, s, v):
    if s == 0.0:
        return v, v, v
    i =int(h * 6.0)  # XXX assume int() truncates!
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return v, t, p
    if i == 1:
        return q, v, p
    if i == 2:
        return p, v, t
    if i == 3:
        return p, q, v
    if i == 4:
        return t, p, v
    if i == 5:
        return v, p, q

FreeCADGui.addCommand('FEA', FEACommand())
