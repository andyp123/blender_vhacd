import bpy
import re
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty, IntProperty, FloatProperty
from .utils import get_addon_prefs, get_last_generated_file_path
from os import path as os_path
from subprocess import Popen

class VHACD_OT_SelectHulls(Operator):
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
        selected_objects = [ob for ob in context.selected_objects if ob.type == 'MESH']

        if len(selected_objects) < 1:
            self.report({'ERROR'}, 'First select an object to find its matching hulls')
            return {'CANCELLED'}

        all_mesh_objects = [ob for ob in context.scene.objects if ob.type == 'MESH']

        name_template = get_addon_prefs().name_template
        name_template = name_template.replace('#', '[0-9]+', 1)
        if name_template.find('?') == -1:
            self.report({'ERROR'}, "Can only match hulls to a name template containing a '?' character.")
            return {'CANCELLED'}

        hulls = []

        for ob in selected_objects:
            regex = re.compile(name_template.replace('?', ob.name, 1))

            for ob_search in all_mesh_objects[-1::-1]: # reverse traversal
                if regex.match(ob_search.name):
                    hulls.append(ob_search)
                    all_mesh_objects.remove(ob_search)

        # deselect selected
        if self.only_hulls:
            bpy.ops.object.select_all(action='DESELECT')

        # select hulls
        for ob in hulls:
            ob.select_set(True)

        return {'FINISHED'}

class VHACD_OT_VHACD(Operator):
    bl_idname = 'object.vhacd'
    bl_label = 'Convex Hull (V-HACD)'
    bl_description = 'Create accurate convex hulls using Hierarchical Approximate Convex Decomposition'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    # VHACD parameters
    maxConvexHull : IntProperty(
        name="Maximum Convex Hull outputs",
        description="Maximum number of output convex hulls",
        default=32,
        min=1
    )

    voxelResolution: IntProperty(
        name='Voxel Resolution',
        description='Total number of voxels to use',
        default=100000,
        min=10000,
        max=64000000
    )

    volumeErrorPercent: FloatProperty(
        name="Volume error percentage",
        description="Volume error allowed as a percentage.",
        default=1,
        min=0.001,
        max=10
    )   

    maxRecursionDepth: IntProperty(
        name='Maximum recursion Depth',
        description='Maximum number of clipping stages. During each split stage, all the model parts (with a concavity higher than the user defined threshold) are clipped according the "best" clipping plane',
        default=10,
        min=1,
        max=32
    )

    shrinkwrapOutput : BoolProperty(
        name= "Shrinkwrap Output",
        description= "Whether or not to shrinkwrap output to source mesh",
        default=True
    )

    fillMode : EnumProperty(
        name='Fill Mode',
        description='Fill Mode',
        items=(('flood', 'Flood', 'Flood Fill Mode'),
               ('surface', 'Surface', 'Surface Fill Mode'),
               ('raycast', 'Raycast', 'Raycast Fill Mode')),
        default='flood'
    )

    maxHullVertCount: IntProperty(
        name='Maximum Vertices Per CH',
        description='Maximum number of vertices in the output convex hull',
        default=64,
        min=4,
        max=1024
    )

    runAsync : BoolProperty(
        name="Run Asynchronously",
        description ="Run Asynchronously",
        default=True
    )

    minEdgeLength: FloatProperty( #Maybe this is an int
        name="Minimun Edge Length",
        description="Minimum size of a voxel edge",
        default=2,
    )

    optimalSplit : BoolProperty(
        name="Split policy",
        description="If false, splits hulls in the middle. If true, tries to find optimal split plane location",
        default=False
    )

    def execute(self, context):
        prefs = get_addon_prefs()

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
            obj_filename = os_path.join(data_path, f'{filename}.obj')

            print(f'Exporting mesh for V-HACD: {obj_filename}...')
            bpy.ops.object.select_all(action='DESELECT')
            ob.select_set(True)
            bpy.ops.export_scene.obj(filepath=obj_filename, use_selection=True)

            # change cd to the data path + use integers for the bool values (Pascal case True/False is not valid)
            cmd_line = (f'cd "{data_path}" && "{vhacd_path}" "{obj_filename}" -h {self.maxConvexHull} -r {self.voxelResolution} -e {self.volumeErrorPercent} -d {self.maxRecursionDepth} -s {int(self.shrinkwrapOutput)} -f {self.fillMode} -v {self.maxHullVertCount} -a {int(self.runAsync)} -l {self.minEdgeLength} -o obj -p {int(self.optimalSplit)}')

            print(f'Running V-HACD...\n{cmd_line}\n')
            vhacd_process = Popen(cmd_line, bufsize=-1, close_fds=True, shell=True)
            vhacd_process.wait()
            # read file in specified data path
            from os import path
            bpy.ops.import_scene.obj(filepath=data_path + "\decomp.obj")

            #bpy.ops.import_scene.obj(filepath=get_last_generated_file_path())
            imported = bpy.context.selected_objects
            new_objects.extend(imported)


            name_template = prefs.name_template
            for index, hull in enumerate(imported):
                hull.select_set(False)
                name = name_template.replace('?', ob.name, 1)
                name = name.replace('#', str(index + 1), 1)
                if name == name_template:
                    name += str(index + 1)
                hull.name = name
                hull.data.name = name
                # Display
                # hull.display_type = 'WIRE'
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
        col.label(text='V-HACD Parameters:')
        col.prop(self, 'maxConvexHull')
        col.prop(self, 'voxelResolution')
        col.prop(self, 'volumeErrorPercent')
        col.prop(self, 'maxRecursionDepth')
        col.prop(self, 'shrinkwrapOutput')
        col.prop(self, 'fillMode')
        col.prop(self, 'maxHullVertCount')
        col.prop(self, 'runAsync')
        col.prop(self, 'minEdgeLength')
        col.prop(self, 'optimalSplit')
        layout.separator()
        col = layout.column()
        col.label(text='WARNING:', icon='ERROR')
        col.label(text='  Processing can take several minutes per object!')
        col.label(text='  ALL selected objects will be processed sequentially!')
        col.label(text='  See Console Window for progress..,')


## Registration
def menu_func(self, context):
    self.layout.operator(VHACD_OT_VHACD.bl_idname)
    self.layout.operator(VHACD_OT_SelectHulls.bl_idname)            

classes = (
VHACD_OT_VHACD,
VHACD_OT_SelectHulls,
)

def register():
    for cl in classes:  
        bpy.utils.register_class(cl)

    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)

