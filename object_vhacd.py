# ----------------
# V-HACD Blender add-on
# Copyright (c) 2014, Alain Ducharme
# ----------------
# This software is provided 'as-is', without any express or implied warranty.
# In no event will the authors be held liable for any damages arising from the use of this software.
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it freely,
# subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not claim that you wrote the original software. If you use this software in a product, an acknowledgment in the product documentation would be appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

#
# NOTE: requires/calls Khaled Mamou's VHACD executable found here: https://github.com/kmammou/v-hacd/
#

# This add-on has been converted to work with Blender 2.80 (conversion by Andrew Palmer)

bl_info = {
    'name': 'V-HACD',
    'description': 'Hierarchical Approximate Convex Decomposition',
    'author': 'Alain Ducharme (original author), Andrew Palmer (Blender 2.80), Terence Dickson (2.90)',
    'version': (0, 36),
    'blender': (2, 90, 0),
    'location': 'Object Mode | View3D > V-HACD',
    'warning': "Requires Khaled Mamou's V-HACD v2.0 executable (see Documentation)",
    'wiki_url': 'https://github.com/kmammou/v-hacd',
    "tracker_url": "https://github.com/andyp123/blender_vhacd/issues",
    'category': 'Object',
}


import bpy
import bmesh
import re # for matching object names
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from mathutils import Matrix, Vector
from bl_operators.presets import AddPresetBase

from subprocess import Popen
from os import path as os_path
from tempfile import gettempdir


def off_export(mesh, fullpath):
    '''Export triangulated mesh to Object File Format'''
    with open(fullpath, 'wb') as off:
        off.write(b'OFF\n')
        off.write(str.encode('{} {} 0\n'.format(len(mesh.vertices), len(mesh.polygons))))
        for vert in mesh.vertices:
            off.write(str.encode('{:g} {:g} {:g}\n'.format(*vert.co)))
        for face in mesh.polygons:
            off.write(str.encode('3 {} {} {}\n'.format(*face.vertices)))


class VHACD_OT_RenameHulls(bpy.types.Operator):
    bl_idname = 'object.vhacd_rename_hulls'
    bl_label = 'Rename Hulls'
    bl_description = 'Rename selected objects with name of active object using a template'
    bl_options = {'REGISTER', 'UNDO'}

    name_template: StringProperty(
        name='Name Template',
        description='Name template used for generated hulls.\n? = original mesh name\n# = hull id',
        default=''
    )

    set_display: BoolProperty(
        name='Set Display',
        description='Set the display properties of selected objects to wireframe',
        default=True
    )

    def execute(self, context):
        if self.name_template == '':
            self.name_template = context.preferences.addons[__name__].preferences.name_template
        name_template = self.name_template

        active_object = context.active_object
        selected_objects = [ob for ob in context.selected_objects if ob != active_object and ob.type == 'MESH']

        for index, ob in enumerate(selected_objects):
            name = name_template.replace('?', active_object.name, 1)
            name = name.replace('#', str(index + 1), 1)
            if name == name_template:
                name += str(index + 1)
            ob.name = name
            ob.data.name = name

            if self.set_display:
                ob.display_type = 'WIRE'
                # ob.display.show_shadows = False
                # ob.show_all_edges = True

        return {'FINISHED'}


class VHACD_OT_SelectHulls(bpy.types.Operator):
    bl_idname = 'object.vhacd_select_hulls'
    bl_label = 'Select Hulls'
    bl_description = 'Select any convex hulls in the scene for the current object based on object name'
    bl_options = {'REGISTER', 'UNDO'}

    only_hulls: bpy.props.BoolProperty(
        name="Only Hulls",
        default=False,
        description="Select only hulls and deselect everything else"
    )

    def execute(self, context):
        selected_objects = [ob for ob in bpy.context.selected_objects if ob.type == 'MESH']

        if len(selected_objects) < 1:
            self.report({'ERROR'}, 'First select an object to find its matching hulls')
            return {'CANCELLED'}

        all_objects = [ob for ob in context.scene.objects if ob.type == 'MESH']

        name_template = context.preferences.addons[__name__].preferences.name_template
        name_template = name_template.replace('#', '[0-9]+', 1)
        if name_template.find('?') == -1:
            self.report({'ERROR'}, "Can only match hulls to a name template containing a '?' character.")
            return {'CANCELLED'}

        hulls = []

        for ob in selected_objects:
            regex = re.compile(name_template.replace('?', ob.name, 1))

            for ob_search in all_objects[-1::-1]: # reverse traversal
                if regex.match(ob_search.name):
                    hulls.append(ob_search)
                    all_objects.remove(ob_search)

        # deselect selected
        if self.only_hulls:
            bpy.ops.object.select_all(action='DESELECT')

        # select hulls
        for ob in hulls:
            ob.select_set(True)

        return {'FINISHED'}


class VHACD_OT_VHACD(bpy.types.Operator):
    bl_idname = 'object.vhacd'
    bl_label = 'Convex Hull (V-HACD)'
    bl_description = 'Create accurate convex hulls using Hierarchical Approximate Convex Decomposition'
    bl_options = {'REGISTER', 'PRESET', 'UNDO'} # PRESET doesn't seem to require AdPresetBase operator to work anymore...

    # pre-process options
    remove_doubles: BoolProperty(
        name='Remove Doubles',
        description='Collapse overlapping vertices in generated mesh',
        default=True
    )

    # pre-process options
    apply_modifiers: BoolProperty(
        name='Apply Modifiers',
        description='Apply all modifiers before computing hull',
        default=True
    )

    apply_transforms: EnumProperty(
        name='Apply',
        description='Apply Transformations to generated mesh',
        items=(
            ('LRS', 'Location + Rotation + Scale', 'Apply location, rotation and scale'),
            ('RS', 'Rotation + Scale', 'Apply rotation and scale'),
            ('S', 'Scale', 'Apply scale only'),
            ('NONE', 'None', 'Do not apply transformations'),
            ),
        default='NONE'
    )

    # VHACD parameters
    resolution: IntProperty(
        name='Voxel Resolution',
        description='Maximum number of voxels generated during the voxelization stage',
        default=100000,
        min=10000,
        max=64000000
    )

    depth: IntProperty(
        name='Clipping Depth',
        description='Maximum number of clipping stages. During each split stage, all the model parts (with a concavity higher than the user defined threshold) are clipped according the "best" clipping plane',
        default=20,
        min=1,
        max=32
    )

    concavity: FloatProperty(
        name='Maximum Concavity',
        description='Maximum concavity',
        default=0.0025,
        min=0.0,
        max=1.0,
        precision=4
    )

    planeDownsampling: IntProperty(
        name='Plane Downsampling',
        description='Granularity of the search for the "best" clipping plane',
        default=4,
        min=1,
        max=16
    )

    convexhullDownsampling: IntProperty(
        name='Convex Hull Downsampling',
        description='Precision of the convex-hull generation process during the clipping plane selection stage',
        default=4,
        min=1,
        max=16
    )

    alpha: FloatProperty(
        name='Alpha',
        description='Bias toward clipping along symmetry planes',
        default=0.05,
        min=0.0,
        max=1.0,
        precision=4
    )

    beta: FloatProperty(
        name='Beta',
        description='Bias toward clipping along revolution axes',
        default=0.05,
        min=0.0,
        max=1.0,
        precision=4
    )

    gamma: FloatProperty(
        name='Gamma',
        description='Maximum allowed concavity during the merge stage',
        default=0.00125,
        min=0.0,
        max=1.0,
        precision=5
    )

    pca: BoolProperty(
        name='PCA',
        description='Enable/disable normalizing the mesh before applying the convex decomposition',
        default=False
    )

    mode: EnumProperty(
        name='ACD Mode',
        description='Approximate convex decomposition mode',
        items=(('VOXEL', 'Voxel', 'Voxel ACD Mode'),
               ('TETRAHEDRON', 'Tetrahedron', 'Tetrahedron ACD Mode')),
        default='VOXEL'
    )

    maxNumVerticesPerCH: IntProperty(
        name='Maximum Vertices Per CH',
        description='Maximum number of vertices per convex-hull',
        default=32,
        min=4,
        max=1024
    )

    minVolumePerCH: FloatProperty(
        name='Minimum Volume Per CH',
        description='Minimum volume to add vertices to convex-hulls',
        default=0.0001,
        min=0.0,
        max=0.01,
        precision=5
    )


    def execute(self, context):
        prefs = context.preferences.addons[__name__].preferences

        # Check executable path
        vhacd_path = bpy.path.abspath(prefs.executable_path)
        if os_path.isdir(vhacd_path):
            vhacd_path = os_path.join(vhacd_path, 'testVHACD')
        elif not os_path.isfile(vhacd_path):
            self.report({'ERROR'}, 'Path to V-HACD executable required')
            return {'CANCELLED'}
        if not os_path.exists(vhacd_path):
            self.report({'ERROR'}, 'Cannot find V-HACD executable at specified path')
            return {'CANCELLED'}

        # Check data path
        data_path = bpy.path.abspath(prefs.data_path)
        if data_path.endswith('/') or data_path.endswith('\\'):
            data_path = os_path.dirname(data_path)
        if not os_path.exists(data_path):
            self.report({'ERROR'}, 'Invalid data directory')
            return {'CANCELLED'}

        selected = bpy.context.selected_objects

        if not selected:
            self.report({'ERROR'}, 'Object(s) must be selected first')
            return {'CANCELLED'}
        for ob in selected:
            ob.select_set(False)

        new_objects = []

        for ob in selected:
            if ob.type != 'MESH':
                continue

            # Base filename is object name with invalid characters removed
            filename = ''.join(c for c in ob.name if c.isalnum() or c in (' ','.','_')).rstrip()

            off_filename = os_path.join(data_path, '{}.off'.format(filename))
            outFileName = os_path.join(data_path, '{}.wrl'.format(filename))
            logFileName = os_path.join(data_path, '{}_log.txt'.format(filename))

            if self.apply_modifiers:
                depsgraph = context.evaluated_depsgraph_get()
                mesh = ob.evaluated_get(depsgraph).data.copy()
            else:
                mesh = ob.data.copy()

            translation, quaternion, scale = ob.matrix_world.decompose()
            scale_matrix = Matrix(((scale.x,0,0,0), (0,scale.y,0,0), (0,0,scale.z,0), (0,0,0,1)))
            if self.apply_transforms in ['S', 'RS', 'LRS']:
                pre_matrix = scale_matrix
                post_matrix = Matrix()
            else:
                pre_matrix = Matrix()
                post_matrix = scale_matrix
            if self.apply_transforms in ['RS', 'LRS']:
                pre_matrix = quaternion.to_matrix().to_4x4() @ pre_matrix
            else:
                post_matrix = quaternion.to_matrix().to_4x4() @ post_matrix
            if self.apply_transforms == 'LRS':
                pre_matrix = Matrix.Translation(translation) @ pre_matrix
            else:
                post_matrix = Matrix.Translation(translation) @ post_matrix

            mesh.transform(pre_matrix)

            bm = bmesh.new()
            bm.from_mesh(mesh)
            if self.remove_doubles:
                bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            bm.to_mesh(mesh)
            bm.free()

            print('\nExporting mesh for V-HACD: {}...'.format(off_filename))
            off_export(mesh, off_filename)
            cmd_line = ( '"{}" --input "{}" --resolution {} --depth {} '
                '--concavity {:g} --planeDownsampling {} --convexhullDownsampling {} '
                '--alpha {:g} --beta {:g} --gamma {:g} --pca {:b} --mode {:b} '
                '--maxNumVerticesPerCH {} --minVolumePerCH {:g} --output "{}" --log "{}"').format(
                    vhacd_path, off_filename, self.resolution, self.depth,
                    self.concavity, self.planeDownsampling, self.convexhullDownsampling,
                    self.alpha, self.beta, self.gamma, self.pca, self.mode == 'TETRAHEDRON',
                    self.maxNumVerticesPerCH, self.minVolumePerCH, outFileName, logFileName)

            print('Running V-HACD...\n{}\n'.format(cmd_line))
            vhacd_process = Popen(cmd_line, bufsize=-1, close_fds=True, shell=True)

            bpy.data.meshes.remove(mesh)

            vhacd_process.wait()
            if not os_path.exists(outFileName):
                continue

            bpy.ops.import_scene.x3d(filepath=outFileName, axis_forward='Y', axis_up='Z')
            imported = bpy.context.selected_objects
            new_objects.extend(imported)

            name_template = prefs.name_template
            for index, hull in enumerate(imported):
                hull.select_set(False)
                hull.matrix_basis = post_matrix
                name = name_template.replace('?', ob.name, 1)
                name = name.replace('#', str(index + 1), 1)
                if name == name_template:
                    name += str(index + 1)
                hull.name = name
                hull.data.name = name
                # Display
                hull.display_type = 'WIRE'
                # hull.display.show_shadows = False
                # hull.show_all_edges = True

        if len(new_objects) < 1:
            for ob in selected:
                ob.select_set(True)
            self.report({'WARNING'}, 'No meshes to process!')
            return {'CANCELLED'}

        for ob in new_objects:
            ob.select_set(True)

        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.label(text='Pre-Processing Options:')
        col.prop(self, 'remove_doubles')
        col.prop(self, 'apply_modifiers')
        col.prop(self, 'apply_transforms')

        layout.separator()
        col = layout.column()
        col.label(text='V-HACD Parameters:')
        col.prop(self, 'resolution')
        col.prop(self, 'depth')
        col.prop(self, 'concavity')
        col.prop(self, 'planeDownsampling')
        col.prop(self, 'convexhullDownsampling')
        row = col.row()
        row.prop(self, 'alpha')
        row.prop(self, 'beta')
        row.prop(self, 'gamma')
        col.prop(self, 'pca')
        col.prop(self, 'mode')
        col.prop(self, 'maxNumVerticesPerCH')
        col.prop(self, 'minVolumePerCH')

        layout.separator()
        col = layout.column()
        col.label(text='WARNING:', icon='ERROR')
        col.label(text='  Processing can take several minutes per object!')
        col.label(text='  ALL selected objects will be processed sequentially!')
        col.label(text='  See Console Window for progress..,')


class VIEW3D_MT_vhacd_menu(bpy.types.Menu):
    bl_label = "V-HACD"
    bl_idname = "VIEW3D_MT_vhacd_menu"

    def draw(self, context):
        layout = self.layout
        layout.label(text="V-HACD")
        layout.operator(
                VHACD_OT_VHACD.bl_idname,
                text=VHACD_OT_VHACD.bl_label,
                icon="MOD_MESHDEFORM")
        layout.separator()
        layout.operator(
                VHACD_OT_SelectHulls.bl_idname,
                text=VHACD_OT_SelectHulls.bl_label)
        layout.operator(
                VHACD_OT_RenameHulls.bl_idname,
                text=VHACD_OT_RenameHulls.bl_label)


class VHACD_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

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
    VHACD_AddonPreferences,
    VHACD_OT_RenameHulls,
    VHACD_OT_SelectHulls,
    VHACD_OT_VHACD,
    VIEW3D_MT_vhacd_menu,
)

def menu_func(self, context):
    self.layout.menu(VIEW3D_MT_vhacd_menu.bl_idname)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

# allows running addon from text editor
if __name__ == '__main__':
    register()
