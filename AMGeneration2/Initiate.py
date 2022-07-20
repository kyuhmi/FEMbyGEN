import FreeCAD, FreeCADGui, Part, Mesh
import PySide


class InitiateCommand():
    """Analyse the generated parts"""

    def GetResources(self):
        return {'Pixmap'  : 'Initiate.svg',  # the name of a svg file available in the resources
                'Accel' : "Shift+N",  # a default shortcut (optional)
                'MenuText': "Initiate",
                'ToolTip' : "Initialise the generation process"}

    def Activated(self): 
        return InitiatePanel()
    
    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class InitiatePanel:
    def __init__(self):   
        # Add spreatsheet
        self.paramsheet=FreeCAD.activeDocument().addObject('Spreadsheet::Sheet','Parameters')
        # Spreadsheet editing
        for i in range(10):
            self.paramsheet.set(f'A{i+2}',f'{i+1}.Parameter')
            FreeCAD.ActiveDocument.Parameters.setStyle(f'A{i+2}:A{i+2}', 'bold', 'add')

        self.paramsheet.set('B1','Parameter Name')
        FreeCAD.ActiveDocument.Parameters.setStyle('B1:B1', 'bold', 'add')
        self.paramsheet.set('C1','Min Value')
        FreeCAD.ActiveDocument.Parameters.setStyle('C1:C1', 'bold', 'add')
        self.paramsheet.set('D1','Max Value')
        FreeCAD.ActiveDocument.Parameters.setStyle('D1:D1', 'bold', 'add')
        self.paramsheet.set('E1','Number of Generations')
        FreeCAD.ActiveDocument.Parameters.setStyle('E1:E1', 'bold', 'add')
        FreeCAD.ActiveDocument.recompute() 

FreeCADGui.addCommand('Initiate', InitiateCommand())
