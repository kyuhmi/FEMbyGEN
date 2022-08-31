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


def checkAnalyses():
    doc = FreeCAD.ActiveDocument
    statuses = doc.FEA.Status
    numAnalysed = doc.FEA.NumberofAnalysis

    return (statuses, numAnalysed)


def checkGenParameters():
    doc = FreeCAD.ActiveDocument
    header = doc.Generate.Parameters_Name
    parameters = doc.Generate.Generated_Parameters
    if parameters == None:
        header = [""]
        parameters = []

    return (header, parameters)


def calcAndSaveFEAMetrics():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    numGenerations = checkGenerations()
    doc = FreeCAD.ActiveDocument
    if numGenerations > 0:
        #table = [["Node Count", "Elem Count", "Max Stress", "Mean Stress", "Max Disp", "Mean Disp"]]
            table = [["Mean Stress", "Max Stress", "Max Disp"]]
        # for i in range(1, numGenerations+1):
            # filePath = workingDir + f"/Gen{i}/FEMMeshNetgen.frd"
            # if not os.path.isfile(filePath):
            #     filePath = workingDir + f"/Gen{i}/FEMMeshGmsh.frd"
            result = calculateFEAMetric()
            # result = [r["MaxStress"], r["MeanStress"],
            #           r["MaxDisp"], r["MeanDisp"]]
            # result = [f"{r:.2e}"for r in result]
            table += result
            print("Table of results: ")
            print(table) 
            doc.Results.FEAMetrics = table


def calculateFEAMetric():
    workingDir = '/'.join(FreeCAD.ActiveDocument.FileName.split('/')[0:-1])
    statuses,numgAnly = searchAnalysed()
    result=[]
    for i, j in enumerate(statuses):   #TODO only for status is anlyzed other cases it will be none
        filename = f"Gen{i+1}"
        filePath = workingDir + f"/Gen{i+1}/" + filename+".FCStd"
        doc = FreeCAD.open(filePath, hidden=True)
        mean=np.mean(doc.CCX_Results.vonMises)
        max=np.max(doc.CCX_Results.vonMises)
        maxDisp=np.max(doc.CCX_Results.DisplacementLengths)
        # Energy=np.max()    #TODO calculate the energy of the deformation
        result.append([f"{mean:.2e}",f"{max:.2e}",f"{maxDisp:.2e}"])
        print(result)
        FreeCAD.closeDocument(filename)
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
    index = item.row()+1
    old = FreeCAD.ActiveDocument.Name
    if old[:3] == "Gen":
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
        self.itemList = []
        for i in itemList:
            self.itemList.append(list(i))

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
            return str(self.itemList[index.row()][index.column()])

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
