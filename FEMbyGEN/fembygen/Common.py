import FreeCAD
import PySide
import os.path
from fembygen import FRDParser
import numpy as np
import copy
import operator


def checkGenerations():
    numGens = 1
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    while os.path.isdir(workingDir + "/Gen" + str(numGens)):
        numGens += 1

    return numGens-1


def searchAnalysed():
    numAnalysed = 0
    statuses = []
    doc = FreeCAD.ActiveDocument
    numGenerations = checkGenerations()
    workingDir = '/'.join(doc.FileName.split('/')[0:-1])
    for i in range(1, numGenerations+1):
        if doc.Analysis.Content.find("Netgen") > 0:
            FRDPath = workingDir + f"/Gen{i}/FEMMeshNetgen.frd"
        elif doc.Analysis.Content.find("Gmsh") > 0:
            FRDPath = workingDir + f"/Gen{i}/FEMMeshGmsh.frd"
        if os.path.isfile(FRDPath):
            try:
                # This returns an exception if analysis failed for this .frd file, because there is no results data
                FRDParser.FRDParser(FRDPath)
            except:
                status = "Failed"
            else:
                status = "Analysed"
                numAnalysed += 1

        else:
            status = "Not analysed"
        statuses.append(status)

    return (statuses, numAnalysed)


def writeAnalysisStatusToFile():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])

    (statuses, numAnalysed) = searchAnalysed()
    filePath = workingDir + "/AnalysisStatus.txt"
    f = open(filePath, "w")
    f.write(str(numAnalysed) + "\n")
    [f.write(status+"\n") for status in statuses]
    print(statuses)
    f.close()

    return (statuses, numAnalysed)


def checkAnalyses():    # Reads AnalysisStatus.txt for results of analysis
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    filePath = workingDir + "/AnalysisStatus.txt"
    try:
        f = open(filePath)
        text = f.read().split("\n")
        numAnalysed = int(text[0])
        statuses = text[1:]
    except FileNotFoundError:
        print("ERROR: AnalysisStatus.txt does not exist")
        statuses = []
        numAnalysed = 0
    except:
        print("An error occured while trying to read analysis results")
        statuses = []
        numAnalysed = 0

    return (statuses, numAnalysed)


def checkGenParameters():
    try:
        workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        filePath = workingDir + "/GeneratedParameters.txt"
    except:
        print("Please open a master file before creating generation")
    header = []
    parameters = []

    try:
        f = open(filePath)
        text = f.read().split("\n")
        header = text[0].split(",")
        for line in text[1:-1]:
            result = line.split(",")
            parameters.append(result)
    except FileNotFoundError:
        print("ERROR: GeneratedParameters.txt does not exist")
        header = [""]
        parameters = []
    except:
        print("An error occured while trying to read generation parameters")
        header = [""]
        parameters = []

    return (header, parameters)


def calcAndSaveFEAMetrics():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    numGenerations = checkGenerations()

    if numGenerations > 0:
        #table = [["Node Count", "Elem Count", "Max Stress", "Mean Stress", "Max Disp", "Mean Disp"]]
        table = [["Max Stress", "Mean Stress", "Max Disp", "Mean Disp"]]
        for i in range(1, numGenerations+1):
            filePath = workingDir + f"/Gen{i}/FEMMeshNetgen.frd"
            if not os.path.isfile(filePath):
                filePath = workingDir + f"/Gen{i}/FEMMeshGmsh.frd"
            r = calculateFEAMetric(filePath)
            result = [r["MaxStress"], r["MeanStress"],
                      r["MaxDisp"], r["MeanDisp"]]
            result = [str(r) for r in result]
            table.append(result)

        print("Table of results: ")
        print(table)

        # Save FEA metrics to .npy file
        np.save(workingDir + "/FEAMetrics.npy", np.array(table))


def calculateFEAMetric(FRDFilePath):
    result = None
    try:
        parser = FRDParser.FRDParser(FRDFilePath)

        nodeCount = parser.frd.node_block.numnod
        elemCount = parser.frd.elem_block.numelem

        stresses = np.zeros((nodeCount, 4), dtype=np.float32)
        disp = np.zeros((nodeCount, 4), dtype=np.float32)
        error = np.zeros((nodeCount, 1), dtype=np.float32)
        for i in range(nodeCount):
            stresses[i, 0:3] = parser.get_results_node(
                i + 1, names="STRESS")[0][0:3]
            disp[i, 0:3] = parser.get_results_node(i + 1, names="DISP")[0][0:3]
            error[i] = parser.get_results_node(i + 1, names="ERROR")[0]

        # Calculate resultant stresses and displacements
        stresses[:, 3] = np.sqrt(np.square(
            stresses[:, 0]) + np.square(stresses[:, 1]) + np.square(stresses[:, 2]))
        disp[:, 3] = np.sqrt(np.square(disp[:, 0]) +
                             np.square(disp[:, 1]) + np.square(disp[:, 2]))

        # Find max and mean for stress, displacement, and error
        resultantStress = stresses[:, 3]
        maxStress = round(max(resultantStress), 3)
        meanStress = round(np.mean(resultantStress), 3)

        resultantDisp = disp[:, 3]
        maxDisp = round(max(resultantDisp), 3)
        meanDisp = round(np.mean(resultantDisp), 3)

        maxError = round(max(error)[0], 1)
        meanError = round((np.mean(error)), 1)

        # Store results in dictionary to be returned by function
        result = {
            "NodeCount": nodeCount,
            "ElemCount": elemCount,
            "MaxStress": maxStress,
            "MeanStress": meanStress,
            "MaxDisp": maxDisp,
            "MeanDisp": meanDisp,
            "MaxError": maxError,
            "MeanError": meanError
        }
    except:
        print("Analysis failed on generation")
        result = {
            "NodeCount": None,
            "ElemCount": None,
            "MaxStress": None,
            "MeanStress": None,
            "MaxDisp":    None,
            "MeanDisp":   None,
            "MaxError":   None,
            "MeanError":  None
        }
    finally:
        return result


def hsvToRgb(h, s, v):
    if s == 0.0:
        return v, v, v
    i = int(h * 6.0)  # XXX assume int() truncates!
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


def showGen(item):
        global old
        index=item.row()+1
        old=FreeCAD.ActiveDocument.Name
        if old[:3]=="Gen":
            FreeCAD.closeDocument(old)

        # Open the generation
        workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
        docPath = workingDir + \
            f"/Gen{index}/Gen{index}.FCStd"
        docName = f"Gen{index}"
        FreeCAD.open(docPath)
        FreeCAD.setActiveDocument(docName)


class GenTableModel(PySide.QtCore.QAbstractTableModel):
    def __init__(self, parent, itemList, header, colours=None, *args):

        PySide.QtCore.QAbstractTableModel.__init__(self, parent, *args)
        self.itemList = copy.deepcopy(itemList)
        self.header = header[:]
        height = len(itemList)
        width = len(header)
        defaultColour = PySide.QtGui.QColor("white")

        if colours == None:
            self.colours = [
                [defaultColour for x in range(width)] for y in range(height)]
        else:
            self.colours = colours[:]

        # Insert generation number column into table
        self.header.insert(0, "Gen")
        for i in range(1, height+1):
            self.itemList[i-1].insert(0, i)
            self.colours[i-1].insert(0, defaultColour)

    def updateColours(self, colours):
        for i, row in enumerate(colours):
            self.colours[i][1:] = row
        # self.dataChanged.emit()

    def updateData(self, table):
        for i, row in enumerate(table):
            self.itemList[i][1:] = row

    def updateHeader(self, header):
        self.header[1:] = header

    def rowCount(self, parent):
        return len(self.itemList)

    def columnCount(self, parent):
        return len(self.header)

    def data(self, index, role):
        if not index.isValid():
            return None
        elif role == PySide.QtCore.Qt.BackgroundRole:
            # Return colour
            return self.colours[index.row()][index.column()]
        elif role == PySide.QtCore.Qt.DisplayRole:
            return self.itemList[index.row()][index.column()]

    def headerData(self, col, orientation, role):
        if orientation == PySide.QtCore.Qt.Horizontal and role == PySide.QtCore.Qt.DisplayRole:
            return self.header[col]
        return None

    def sort(self, col, order):
        """sort table by given column number col"""
        self.emit(PySide.QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.itemList = sorted(self.itemList, key=operator.itemgetter(col))
        if order == PySide.QtCore.Qt.DescendingOrder:
            self.itemList.reverse()
        self.emit(PySide.QtCore.Qt.SIGNAL("layoutChanged()"))
        pass
