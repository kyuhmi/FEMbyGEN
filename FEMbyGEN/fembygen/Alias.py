#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 16:35:28 2022

@author: trial
"""

import FreeCAD, FreeCADGui, Part, Mesh
import PySide

class AliasCommand():
    """Analyse the generated parts"""

    def GetResources(self):
        return {'Pixmap'  : 'fembygen/Alias.png',  # the name of a svg file available in the resources
                'Accel' : "Shift+A",  # a default shortcut (optional)
                'MenuText': "Alias",
                'ToolTip' : "Alias in spreadsheet"}

    def Activated(self): 
        return AliasPanel()
    
    def IsActive(self):
        """Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional."""
        return True

class AliasPanel:
    def __init__(self):
        for i in range(10):
            try:
                FreeCAD.ActiveDocument.Parameters.setAlias(f'C{i+2}', FreeCAD.ActiveDocument.Parameters.get(f'B{i+2}'))
                FreeCAD.ActiveDocument.Parameters.recompute()
            except:
                pass
FreeCADGui.addCommand('Alias', AliasCommand())
