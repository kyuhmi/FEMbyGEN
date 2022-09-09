import FreeCAD
import PySide
import os.path
from fembygen import FRDParser
import numpy as np
import copy
import operator
import glob

def checkGenerations(workingDir):
    numGens = 1
    loadCase =1
    # workingDir = '/'.join(master.FileName.split('/')[0:-1])
    while os.path.isdir(workingDir + "/Gen" + str(numGens)):
        numGens += 1
    return numGens-1


def searchAnalysed(master):
    numAnalysed = 0
    statuses = []
    workingDir = '/'.join(master.FileName.split('/')[0:-1])
    numGenerations = checkGenerations(workingDir)
    for i in range(1, numGenerations+1):
        # Checking the loadcases in generated file
        lc=0
        lcStatus=[]
        for obj in master.Objects:
            if obj.TypeId=="Fem::FemAnalysis":   #to choose analysis objects
                lc+=1
                analysisfolder=os.path.join(workingDir + f"/Gen{i}/loadCase{lc}/")
                try:
                    # This returns an exception if analysis failed for this .frd file, because there is no results data
                    FRDPath = glob.glob(analysisfolder + "*.frd")[0]
                    try:
                          FRDParser.FRDParser(FRDPath)
                    except:
                        status = "Failed"
                except:
                    status = "Not analysed"
                else:
                    status = "Analysed"
                    numAnalysed += 1
                try:
                    lcStatus.append(status)
                except:
                    FreeCAD.Console.PrintError("Analysis not found.")
        statuses.append(lcStatus)
    return (statuses, numAnalysed, lc)


def checkAnalyses(master):
    statuses = master.FEA.Status
    numAnalysed = master.FEA.NumberofAnalysis

    return (statuses, numAnalysed)


def checkGenParameters(master):
    header = master.Generate.Parameters_Name
    parameters = master.Generate.Generated_Parameters
    if parameters == None:
        header = [""]
        parameters = []

    return (header, parameters)



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
    old = FreeCAD.ActiveDocument.Name
    if old[:3] == "Gen":
        FreeCAD.closeDocument(old)
    if item=="close":
        return
    index = item.row()+1
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
        # print(self.itemList)

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
