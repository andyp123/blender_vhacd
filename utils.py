import os
import bpy

def get_addon_prefs():
    '''
    function to read current addon preferences properties
    access a prop like this :
    prefs = get_addon_prefs()
    option_state = prefs.super_special_option
    oneliner : get_addon_prefs().super_special_option
    '''
    addon_name = os.path.splitext(__name__)[0]
    preferences = bpy.context.preferences
    addon_prefs = preferences.addons[addon_name].preferences
    return (addon_prefs)

def get_last_generated_file_path(filename="decomp.obj"):
    script_file = os.path.realpath(__file__)
    directory = os.path.dirname(script_file)
    return os.path.join(directory, filename)