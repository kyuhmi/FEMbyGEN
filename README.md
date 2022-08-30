# FEMbyGEN
A FreeCAD module that uses Generative Design to calculate and show structural analysis results

This project was devoloped based on Rahul Jhuree Master's thesis. For more information, click [here](https://mightybucket.github.io/projects/2021/05/31/masters-dissertation.html) [Rahul] (https://github.com/MightyBucket) and [Ogeday Yavuz](https://github.com/OgedaYY/) Graduation Thesis.

## Installation instructions
This folder contains the code for a workbench plug-in for FreeCAD. Therefore you must have FreeCAD installed to use it.

FreeCAD 0.20 can be downloaded for free from https://www.freecadweb.org/

Once installed, you must manually copy the 'AMGeneration2' folder to the user 'Mod' directory for FreeCAD. On Windows, this is normally found in the following directory:
in Windows:
`C:\Users\*UserName*\AppData\Roaming\FreeCAD\Mod
in Linux
/home/*UserName*/.local/FreeCAD/Mod

Where `UserName` is replaced with the name of your user profile.

Once copied, start up FreeCAD. From the workbench selection drop down menu in the top middle of the window, you should see the option for "FEMbyGEN". Selecting this will activate the workbench.

Not all of the functions will work out of the box. Some dependencies need to be installed first, which is detailed in the section below.
