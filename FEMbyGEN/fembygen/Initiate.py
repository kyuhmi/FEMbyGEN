import FreeCAD, FreeCADGui, Part, Mesh
import PySide


class InitiateCommand():
    """Analyse the generated parts"""

    def GetResources(self):
        return {'Pixmap'  : 'fembygen/Initiate.svg',  # the name of a svg file available in the resources
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
        doc=FreeCAD.ActiveDocument
        self.paramsheet=doc.addObject('Spreadsheet::Sheet','Parameters')
        # Spreadsheet editing
        for i in range(10):
            self.paramsheet.set(f'A{i+2}',f'{i+1}.Parameter')
            doc.Parameters.setStyle(f'A{i+2}:A{i+2}', 'bold', 'add')

        self.paramsheet.set('B1','Parameter Name')
        self.paramsheet.set('C1','Min Value')
        self.paramsheet.set('D1','Max Value')
        self.paramsheet.set('E1','Number of Generations')
        doc.Parameters.setStyle('B1:E1', 'bold', 'add')
        doc.Parameters.setForeground('A2:A100', (1.000000,0.000000,0.000000,1.000000))
        doc.Parameters.setForeground('B1:E1', (0.000000,0.501961,0.000000,1.000000))
        doc.Parameters.setAlignment('C2:E100', 'left|vcenter|vimplied')
        doc.recompute() 

FreeCADGui.addCommand('Initiate', InitiateCommand())
