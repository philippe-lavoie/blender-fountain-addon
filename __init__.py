bl_info = \
    {
        "name" : "Fountain Script",
        "author" : "Philippe Lavoie <philippe.lavoie@gmail.com>",
        "version" : (1, 1 , 0),
        "blender" : (2, 5, 7),
        "location" : "View 3D > Tools > Animation",
        "description" :
            "Allows you to add fountain script elements as markers with dialogue and action descriptions",
        "warning" : "",
        "wiki_url" : "https://github.com/philippe-lavoie/blender-fountain-addon/wiki",
        "tracker_url" : "https://github.com/philippe-lavoie/blender-fountain-addon.git",
        "category" : "Animation",
    }
 
# I'm using the approache shown in https://b3d.interplanety.org/en/creating-multifile-add-on-for-blender/
# to structure this multifile add-on

modulesNames = ['FountainAddon', 'fountain']
 
import sys
import importlib
 
modulesFullNames = {}
for currentModuleName in modulesNames:
    if 'DEBUG_MODE' in sys.argv:
        modulesFullNames[currentModuleName] = ('{}'.format(currentModuleName))
    else:
        modulesFullNames[currentModuleName] = ('{}.{}'.format(__name__, currentModuleName))
 
for currentModuleFullName in modulesFullNames.values():
    if currentModuleFullName in sys.modules:
        importlib.reload(sys.modules[currentModuleFullName])
    else:
        globals()[currentModuleFullName] = importlib.import_module(currentModuleFullName)
        setattr(globals()[currentModuleFullName], 'modulesNames', modulesFullNames)
 
def register():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'register'):
                sys.modules[currentModuleName].register()
 
def unregister():
    for currentModuleName in modulesFullNames.values():
        if currentModuleName in sys.modules:
            if hasattr(sys.modules[currentModuleName], 'unregister'):
                sys.modules[currentModuleName].unregister()
 
if __name__ == "__main__":
    register()