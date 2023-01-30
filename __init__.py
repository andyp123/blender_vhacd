# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "V-HACD for Blender",
    "author": "Alain Ducharme, Andrew Palmer, Terence Dickson, Henri Hebeisen",
    "version": (0, 5),
    "blender": (3, 4, 1),
    "location": "3D View > Object Menu",
    "description": "Link Between V-HACD and Blender",
    'wiki_url': 'https://github.com/kmammou/v-hacd',
    "tracker_url": "https://github.com/maxiriton/blender_vhacd/issues",
    "category": "3D View",
    }

import bpy
from bpy.types import AddonPreferences
from bpy.props import StringProperty
from tempfile import gettempdir
from . import OP_VHCAD_main


class VHACD_blender_prefs(AddonPreferences):
    bl_idname = __package__

    executable_path: StringProperty(
        name='VHACD Path',
        description='Path to VHACD executable',
        default='',
        maxlen=1024,
        subtype='FILE_PATH'
    )

    data_path: StringProperty(
        name='Data Path',
        description='Data path to store V-HACD meshes and logs',
        default=gettempdir(),
        maxlen=1024,
        subtype='DIR_PATH'
    )

    name_template: StringProperty(
        name='Name Template',
        description='Name template used for generated hulls.\n? = original mesh name\n# = hull id',
        default='?_hull_#',
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, 'executable_path')
        col.prop(self, 'data_path')
        col.prop(self, 'name_template')

classes = (
    VHACD_blender_prefs,
)

addon_modules = (
    OP_VHCAD_main,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    for mod in addon_modules:
        mod.register()

def unregister():
    for mod in reversed(addon_modules):
        mod.unregister()

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
