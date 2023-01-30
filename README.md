# V-HACD For Blender 3.5
Blender 3.5 conversion of Phymec's add-on that enables the use of V-HACD for quick and accurate convex decomposition of arbitrary meshes inside Blender. It uses the [V-HACD algorithm](https://github.com/kmammou/v-hacd), developed by Khaled Mammou.

## Installation
__Note:__ This add-on requires [Blender 3.5](https://builder.blender.org) and the [V-HACD](https://github.com/kmammou/v-hacd) executable to work. Before installing the add-on, make sure you have a copy of V-HACD installed somewhere on your computer. You will only need a single file (testVHACD.exe) for this add-on to work.

1. Download the add-on [here](https://github.com/maxiriton/blender_vhacd/releases).
2. In Blender, open the Preferences window (Edit>Preferences) and select the Add-ons tab.
3. Press the 'Install...' button and select the .zip file you downloaded.
4. Enable the add-on and set the VHACD Path to point to the testVHACD.exe file that you previously downloaded.
5. Save preferences so that the add-on is always enabled.

### Add-on Preferences
This addon stores some general settings inside its entry under the Add-ons tab of the Blender Preferences window.

![V-HACD Preferences](https://raw.githubusercontent.com/maxiriton/blender_vhacd/master/README_img/addon_prefs.png)

+ __VHACD Path__
The path to the V-HACD Executable. This is required for the add-on to be able to generate convex hulls for objects. See the above installation notes for a download link.

+ __Temp Path__
A Path for temporary files created by the add-on and V-HACD executable while in operation. By default, Blender's temp directory is used, so you shouldn't need to change anything in most cases.

+ __Name Template__
A name template used when creating, renaming and selecting convex hulls. Change this to align with any external application (such as a game engine) you may be generating colliders for. For more details on the format of the name template, see explanation in the Rename Hulls operator below.

---

## Usage
Once the add-on is installed correctly, it can be used very easily by selecting meshes and running the 'Convex Hull (V-HACD)' operator, which can be found from the Blender operator search menu.

![V-HACD Operation](https://raw.githubusercontent.com/maxiriton/blender_vhacd/master/README_img/vhacd.gif)

### Convex Hull (V-HACD)
Takes one or more meshes of arbitrary geometry and generates convex hulls which are suitable for use in real-time applications such as games. Generated hulls will be named based on the 'Name Template' setting in the add-on preferences.

For a full description of what all the V-HACD parameters do, please see the documentation on the [V-HACD Github page](https://github.com/kmammou/v-hacd#parameters). Note that you can save the parameters to a preset using the dropdown menu at the top of the operator panel if you find particular settings that work well for your use.


### Select Hulls
Selects existing convex hulls in the scene based on the name template set in the add-on preferences. This will only work if the name template contains a '?' character, which represents the name of the selected object. For example, if the name template is '?\_hull\_#' and the selected object is named 'wall_1', then it would match hulls named 'wall_1_hull_2', 'wall_1_hull_63', etc. and select them all.

+ __Only Hulls__ (Off) - Select only the hulls of the selected object(s), and deselect everything else.

