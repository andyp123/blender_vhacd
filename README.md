# V-HACD For Blender 2.80
Blender 2.80 conversion of Phymec's add-on that enables the use of V-HACD for quick and accurate convex decomposition of arbitrary meshes inside Blender. It uses the [V-HACD algorithm](https://github.com/kmammou/v-hacd), developed by Khaled Mammou.

![V-HACD Operation](https://raw.githubusercontent.com/andyp123/blender_vhacd/master/README_img/vhacd.gif)

## Installation
__Note:__ This add-on requires [Blender 2.80](https://builder.blender.org) and the [V-HACD](https://github.com/kmammou/v-hacd) executable to work. Before installing the add-on, make sure you have a copy of V-HACD installed somewhere on your computer. You will only need a single file (testVHACD.exe) for this add-on to work.
1. Download the add-on [here](https://github.com/andyp123/blender_vhacd/archive/master.zip).
2. In Blender, open the Preferences window (Edit>Preferences) and select the Add-ons tab.
3. Press the 'Install...' button and select the .zip file you downloaded.
4. Enable the add-on and set the VHACD Path to point to the testVHACD.exe file that you previously downloaded.
5. Save preferences so that the add-on is always enabled.

---

## Usage
Once the add-on is installed correctly, it can be used very easily by selecting meshes and running the 'Convex Hull (V-HACD)' operator, which can be found from the Blender operator search menu.

### Convex Hull (V-HACD)
Takes one or more meshes of arbitrary geometry and generates convex hulls which are suitable for use in real-time applications such as games. Generated hulls will be named based on the 'Name Template' setting in the add-on preferences.

+ __Remove Doubles__ (On) - Remove duplicate vertices from the mesh before running V-HACD on it. This may improve the resulting convex hulls. Note that this operates on a duplicate mesh, so the original data will be untouched.

+ __Apply__ (None) - Apply transformations on the mesh before running V-HACD on it. Note that this operates on a duplicate mesh, so the original data will be untouched.

For a full description of what all the V-HACD parameters do, please see the documentation on the [V-HACD Github page](https://github.com/kmammou/v-hacd#parameters).

### Rename Hulls
Renames objects in the selection based on the name of the active object and a name template. This is useful if the name of the original object changes. The name template defaults to the 'Name Template' setting in the add-on preferences, but can be changed directly in the operator redo panel.

+ __Name Template__ (?\_hull\_#) - The name template to use. '?' in the template will be replaced with the name of the active object and '#' will be replaced with the id of each hull. For example, '?\_hull\_#' becomes 'Suzanne_hull_3' for the third hull of the object named 'Suzanne'. Only the first occurence of each character will be replaced.

+ __Set Display__ (On) - Set the draw mode of selected objects to wireframe to make it easier to see that they are hulls of another object.


