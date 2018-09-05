bl_info = \
    {
        "name" : "Fountain Script",
        "author" : "Philippe Lavoie <philippe.lavoie@gmail.com>",
        "version" : (1, 2 , 0),
        "blender": (2, 7, 9),
        "location" : "View 3D > Tools > Animation",
        "description" :
            "Allows you to add fountain script elements as markers with dialogue and action descriptions",
        "warning" : "",
        "wiki_url" : "https://github.com/philippe-lavoie/blender-fountain-addon/wiki",
        "tracker_url" : "https://github.com/philippe-lavoie/blender-fountain-addon.git",
        "category" : "Animation",
    }
 
import os
import bpy
import math
import operator
import re
import sys
import bgl
import blf

if 'DEBUG_MODE' in sys.argv:
    import fountain    
else:
    from . import fountain

from bpy.types import Panel, Operator, Menu, PropertyGroup
from bpy.props import *



# if 'DEBUG_MODE' in sys.argv:
#     fountainModuleName = ('{}'.format('fountain'))
# else:
#     fountainModuleName = ('{}.{}'.format(__name__, 'fountain'))
 
# if fountainModuleName in sys.modules:
#     importlib.reload(sys.modules[fountainModuleName])
# else:
#     globals()[fountainModuleName] = importlib.import_module(fountainModuleName)
#     setattr(globals()[fountainModuleName], 'modulesNames', fountainModuleName)

# list of texts
def texts(self, context):
    return [(text.name, text.name, '') for text in bpy.data.texts]

def frameToTime(frame, context, format = 'long'):
    render = context.scene.render
    framerate = render.fps / render.fps_base
    time_in_seconds = frame / framerate
    hours = math.floor(time_in_seconds / 3600.0)
    minutes = math.floor(time_in_seconds / 60.0)
    seconds = time_in_seconds - (minutes * 60)
    if format == 'long':
        if minutes>0:
            return "{:0d} min {:00.2f}sec".format(minutes, seconds)
        else:
            return "{:0.2f} sec".format(seconds)
    elif format == 'srt':
        secs = math.floor(seconds)
        ms = math.floor(1000.0 * (seconds - secs))
        return "{:02d}:{:02d}:{:02d},{:03d}".format(hours, minutes, secs, ms)
    else:
        return "{:02d}:{:00.2f}".format(minutes, seconds)

def stringFits(pstr, max_width):
    font_id = 0
    text_width, text_height = blf.dimensions(font_id, pstr)
    return text_width < max_width

def draw_string(x, y, packed_strings, horizontal_align='left', bottom_align=False, max_width=0.7):
    font_id = 0
    blf.size(font_id, 14, 72)
    blf.enable(0, blf.SHADOW)
    blf.shadow_offset(0, 1, -1)
    blf.shadow(0, 5, 0.0, 0.0, 0.0, 0.8)
    x_offset = 0
    y_offset = 0
    line_height = (blf.dimensions(font_id, "M")[1] * 1.45)
    
    max_size = 0

    if not packed_strings or len(packed_strings) == 0:
        return 0

    if len(packed_strings[-1]) != 2:
        packed_strings = packed_strings[:-1]
    
    if bottom_align:
        for command in packed_strings:
            if len(command) != 2:
                y_offset += line_height

    line_widths = []
    index = 0
    if horizontal_align !='left':
        line_width=0
        for command in packed_strings:
            if len(command) == 2:
                pstr, pcol = command
                text_width, text_height = blf.dimensions(font_id, pstr)
                line_width += text_width
            else:               
                while len(line_widths) <= index:
                    line_widths.append(line_width)
                line_width = 0
            index += 1
        while len(line_widths) <= index:
            line_widths.append(line_width)
            
    index=0
    for command in packed_strings:
        line_width=0
        if horizontal_align =='right':
            line_width=line_widths[index]
        elif horizontal_align =='middle':
            line_width=line_widths[index] // 2
                        
        if len(command) == 2:
            pstr, pcol = command
            bgl.glColor4f(*pcol)
            text_width, text_height = blf.dimensions(font_id, pstr)
            blf.position(font_id, (x + x_offset - line_width), (y + y_offset), 0)
            blf.draw(font_id, pstr)
            x_offset += text_width
            if x_offset > max_size:
                max_size = x_offset
        else:
            x_offset = 0
            y_offset -= line_height
        index += 1
    blf.disable(0, blf.SHADOW)
    return max_size

class DrawingClass:

    def __init__(self, context):
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
                   self.draw_text_callback,(context,),
                   'WINDOW', 'POST_PIXEL')
        self.scene_name = "Scene"
        self.action = "Action\naction"
        self.dialogue = "Dialogue\ndialogue"
        self.dialogues = []
        self.marker = "MarkerName"
        self.character = ""
        self.characters = []
        self.last_frame = -100
        self.last_index = 0
        self.RED = (1, 0, 0, 1)
        self.GREEN = (0, 1, 0, 1)
        self.BLUE = (0, 0, 1, 1)
        self.CYAN = (0, 1, 1, 1)
        self.MAGENTA = (1,0,1,1)
        self.YELLOW = (1, 1, 0, 1)
        self.ORANGE = (1, 0.8, 0, 1)
        self.WHITE = (1,1,1,0.8)
        self.FULLWHITE = (1,1,1,1)
        self.CR = "\n"

    def start(self, context):
        if not self.handle:
            self.handle = bpy.types.SpaceView3D.draw_handler_add(
                   self.draw_text_callback,(context,),
                   'WINDOW', 'POST_PIXEL')
        self.last_frame = -100
        self.last_index = 0
        self.draw_text_callback(context)

    def stop(self):
        if self.handle:
            bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')
            self.handle = None

    def __del__(self):
        self.stop()

    def set_content(self, element):
        self.marker = element.name
        self.character = ""
        if element.fountain_type == 'Scene Heading':
            self.scene_name = element.content
            self.action = ""
            self.dialogue = ""
            self.dialogues = None
            self.characters = None
        elif element.fountain_type == 'Transition':
            self.scene_name = element.content
            self.dialogue = ''
            self.action = "Transition"
            self.dialogues = None
            self.characters = None
        elif element.fountain_type == 'Action':
            self.action = element.content
            self.dialogue = ""
            self.dialogues = None
            self.characters = None
        elif element.fountain_type == 'Dialogue':
            if element.is_dual_dialogue:
                self.dialogue = ''
                self.character = ''
                if not self.dialogues:
                    self.dialogues = [element.content]
                    self.characters = [element.target]
                else:
                    self.dialogues.append(element.content)
                    self.characters.append(element.target)
            else:
                self.dialogue = element.content
                self.character = element.target
                self.dialogues = None
                self.characters = None

    def updateFountainElements(self, context):
        frame = context.scene.frame_current

        if self.last_frame == frame:
            return

        fountain_collection = sorted(context.scene.fountain_markers, key  = lambda item : item.frame)

        # if self.last_frame < frame:
        #     range = fountain_collection[self.last_index:]
        #     for element in [element for element in range if element.frame <= frame and element.frame_end >= frame]:
        #         self.last_index += 1
        #         self.set_content(element)
        #     self.last_frame = frame
        #     return
        
        self.last_index = 0
        self.dialogue = ""
        self.action = ""
        self.scene_name = ""
        self.marker = ""
        self.character = ""
        for element in [element for element in fountain_collection if element.frame <= frame and element.frame_end > frame]:
            self.last_index += 1
            self.set_content(element)
        self.last_frame = frame

    def get_dialogue(self, character, dialogue, max_width, max_characters):
        ps = []
        ps.append( (character, self.ORANGE) )
        ps.append( self.CR )
        for line in dialogue.splitlines():
            while len(line) > max_characters or not stringFits( line, max_width):
                screen_max_characters = max_characters
                while not stringFits(line[:screen_max_characters], max_width):
                    split_index = line.rfind(' ', 0, screen_max_characters)
                    if split_index <= 0:
                        break
                    screen_max_characters = split_index

                split_index = line.rfind(' ', 0, screen_max_characters)
                if split_index > 0:
                    ps.append( (line[:split_index], self.YELLOW))
                    ps.append( self.CR )
                    line = line[split_index+1:]    
                else:
                    break
            ps.append( (line, self.YELLOW))
            ps.append( self.CR )
        return ps

    def draw_text_callback(self, context):
        try:
            if not bpy.context.scene.fountain.show_fountain:
                return
        except AttributeError:
            #self.stop()
            return

        screen_max_characters = bpy.context.scene.fountain.max_characters
        index = 0
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                self.width = area.width
                self.height = area.height
                break
            index += 1
            
        for region in bpy.context.area.regions:
            if region.type == "TOOLS":
                self.width -= region.width
                break

        if self.width<200 or self.height < 200:
            return


        self.updateFountainElements(bpy.context)

        x = 60
        y = 60

        ps = [(self.scene_name, self.WHITE),self.CR, (self.marker, self.WHITE)]
        x = self.width-20
        y = 60
        label_size = draw_string(x, y, ps, horizontal_align='right', max_width=0.2 * self.width) + 40

        if self.action:
            ps = []
            for line in self.action.splitlines():
                while len(line) > screen_max_characters or not stringFits(line, self.width - 40):
                    screen_max_characters = bpy.context.scene.fountain.max_characters
                    while not stringFits(line[:screen_max_characters], self.width - 40):
                        split_index = line.rfind(' ', 0, screen_max_characters)
                        if split_index <= 0:
                            break
                        screen_max_characters = split_index

                    split_index = line.rfind(' ', 0, screen_max_characters)
                    if split_index > 0:
                        ps.append( (line[:split_index], self.CYAN))
                        ps.append( self.CR )
                        line = line[split_index+1:]    
                    else:
                        break
                if line == 'Transition':
                    ps.append( (line, self.MAGENTA))
                else:
                    ps.append( (line, self.CYAN))
                ps.append( self.CR )
            x = self.width / 2
            y = self.height-70
            draw_string(x, y, ps, horizontal_align='middle', bottom_align=False, max_width= self.width - 40)

        if self.dialogue:
            ps = self.get_dialogue(self.character, self.dialogue, self.width - label_size * 2, bpy.context.scene.fountain.max_characters)
            x = self.width / 2
            y = 40
            draw_string(x, y, ps, horizontal_align='middle', bottom_align=True, max_width= self.width - label_size)

        if self.dialogues:
            ps = self.get_dialogue(self.characters[0], self.dialogues[0], (self.width / 2) - (label_size * 2), bpy.context.scene.fountain.max_characters)
            x = self.width / 4
            y = 40
            draw_string(x, y, ps, horizontal_align='middle', bottom_align=True, max_width= self.width - label_size)

            ps = self.get_dialogue(self.characters[1], self.dialogues[1], (self.width / 2) - (label_size * 2), bpy.context.scene.fountain.max_characters)
            x = 3 * self.width / 4
            y = 40
            draw_string(x, y, ps, horizontal_align='middle', bottom_align=True, max_width= self.width - label_size)


class FountainProps(PropertyGroup):
    def update_text_list(self, context):
        self.script = bpy.data.texts[self.scene_texts].name    
        
        return None

    # def set_show_fountain(self,value):
    #     ShowFountain.show = value
    #     self["show_fountain"] = value
    #     bpy.ops.scene.show_fountain('EXEC_DEFAULT')

    # def get_show_fountain(self):
    #     return self["show_fountain"]

    # def updateShow(self, context):
    #     if ShowFountain.show != self.get_show_fountain():
    #         ShowFountain.show = self["show_fountain"]
    #         bpy.ops.scene.show_fountain('EXEC_DEFAULT')

    def reset(self):
        self.title = ''
        self.script_line = -1
    
    name = StringProperty(default="Fountain script")
    show_fountain = BoolProperty(default=False) #, set = set_show_fountain, get=get_show_fountain)
    script = StringProperty(default='', description='Choose your script')
    scene_texts = EnumProperty(name = 'Available Texts', items = texts, update = update_text_list,
                                         description = 'Available Texts.')
    marker_on_scene = BoolProperty(default=True)
    marker_on_action = BoolProperty(default=True)
    marker_on_transition = BoolProperty(default=True)
    marker_on_section = BoolProperty(default=True)
    marker_on_dialogue = BoolProperty(default=True)
    title = StringProperty(default="")
    max_characters = IntProperty(default=80, min=10)
    script_line = IntProperty(default=-1)
    fix_duration = BoolProperty(default=True)
       
    def get_body(self):
        text = bpy.data.texts[self.scene_texts]
        full = ""
        for line in text.lines:
            full += line.body + "\n"
        return full
    
    def get_script(self):
        text = bpy.data.texts[self.scene_texts]
        return text

class FountainMarker(bpy.types.PropertyGroup):

    def get_marker(self, context):
        if not self.original_name:
            return None
        
        result = [marker for marker in context.scene.timeline_markers if marker.name == self.original_name]
        if len(result) > 0:
            return result[0]
        return None

    def updateName(self, context):
        marker = self.get_marker(context)
        if marker is not None:
            marker.name = self.name
        self.original_name = self.name
        return
    
    name = bpy.props.StringProperty()
    original_name = bpy.props.StringProperty()
    frame = bpy.props.IntProperty()
    duration = bpy.props.IntProperty(default=0, min=0)
    frame_end = bpy.props.IntProperty()
    sequence = IntProperty()

    fountain_type = bpy.props.EnumProperty(
                    name='Foutain element type',
                    description='The element in the fountain script',
                    items={
                        ('Section Heading','Section Heading','A section heading',1),
                        ('Comment','Comment','A comment',2),
                        ('Scene Heading','Scene Heading','A scene heading',3),
                        ('Transition','Transition','A transition to a different scene',4),
                        ('Action','Action','An action that should be depicted',5),
                        ('Dialogue','Dialogue','A dialogue from a character',6),
                        }
                )

    is_dual_dialogue = bpy.props.BoolProperty(default=False)
    content = bpy.props.StringProperty()
    target = bpy.props.StringProperty()  
    line_number = bpy.props.IntProperty(name="Line Number", description="Line number in the script file")  

class FountainPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type="TOOLS"
    bl_category="Animation"
    bl_label="Fountain Markers"

    last_marker = ''
    selected_index = -1

#    def execute(self, context):
#        if not context.scene.fountain_markers:
#            scene.synch_markers(context)

    def invoke(self, context):
        scn = context.scene
        fountain = scn.fountain
        fountain.updateShow(context)
        return {'FINISHED'}

    def draw(self, context):
        scn = context.scene
        fountain = scn.fountain
        
        row = self.layout.row()
        column = row.column(align=True)
        row = column.row(align=True)
        showLabel = 'Show Fountain'
        if fountain.show_fountain:
            showLabel = 'Hide Fountain'
        row.prop(fountain, 'show_fountain', text="Show Fountain")
        row.prop(fountain, 'max_characters', text='Characters per line')
        
        row = column.row(align = True) 
        row.prop(fountain, 'scene_texts', text = '', icon = 'TEXT', icon_only=True)                                                
        row.prop(fountain, 'script', text = "")

        row = self.layout.row()
        column = row.column(align=True)
        row = column.row(align=True)
        row.operator("scene.import_fountain", text="Import")
        row.operator("scene.clear_fountain", text="Clear")
        row.operator("scene.update_fountain_script", text="Update Script")
        row.operator("scene.clean_fountain_script", text="Clean Script")
        row.operator("scene.print_fountain", text="Export to SRT")

        if len(fountain.script) > 0:
            row = self.layout.row()
            column = row.column(align=True)
            row = column.row(align=True)
            row.prop(fountain, 'marker_on_scene', text='Scene')
            row.prop(fountain, 'marker_on_action', text="Action")            
            row.prop(fountain, 'marker_on_transition', text="Transition")
            row.prop(fountain, 'marker_on_section', text="Header")
            row.prop(fountain, 'marker_on_dialogue', text="Dialogue")

        row = self.layout.row()
        column = row.column(align=True)
        row = column.row(align=True)
        row.operator("scene.synch_markers", text="Sync markers")
        row.operator("scene.show_end_markers", text="Show End", icon='MARKER_HLT')
        row.operator("scene.move_markers", text="Move", icon='ALIGN')
        row = self.layout.row()
        row.prop(fountain,"fix_duration",text="Fix duration after move.")

        row = self.layout.row()
        column = row.column(align=True)
        row = column.row(align=True)
        row.enabled = False
        row.prop(fountain, "title")

        row = self.layout.row()
        rows = 2
        row.template_list("FountainMarker_UI_Item", "fountain_markers_list", context.scene, "fountain_markers", 
            context.scene, "fountain_markers_index", rows=rows)

        idx = scn.fountain_markers_index
        
        try:
            item = scn.fountain_markers[idx]
        except IndexError:
            pass
        else:
            row = self.layout.row()
            column = row.column(align=True)
            column.enabled = False
            column.prop(item, "name")
            column.prop(item, "fountain_type")
            column = row.column(align=True)
            column.prop(item, "duration")
            if item.duration > 0:                
                column.label("At " + frameToTime(item.frame, context) + " for " + frameToTime(item.duration, context))
            else:
                column.label("At " + frameToTime(item.frame, context))
            row = self.layout.row()
            column = row.column(align=True)
            column.enabled = False
            column.prop(item, "content")
            column.prop(item, "target")
            column.prop(item, "line_number")

            if FountainPanel.selected_index != idx:
                FountainPanel.selected_index = idx
                for m in context.scene.timeline_markers:
                    if m.name == item.name:
                        m.select = True
                    else:
                        m.select = False

            if fountain.script_line != item.line_number:
                bpy.context.scene.frame_set(item.frame)
                fountain.script_line = item.line_number
                bpy.ops.scene.move_fountain_cursor('EXEC_DEFAULT')
            
#end FountainPanel

class CheckMarkers(bpy.types.Operator):
    bl_idname="scene.check_markers"
    bl_label="Check fountain markers"
    bl_options = {"REGISTER"}

    @classmethod
    def poll(self, context):
        print('c')

        return bpy.context.area.type == 'TIMELINE'
        #return len(context.scene.timeline_markers) > 0
    
    def modal(self, context, evt):
        print('m')
        if evt.type == 'RIGHTMOUSE':
            if evt.value == 'PRESS':
                print('LMB Pressed')
            elif evt.value == 'RELEASE':
                print('LMB Released')
                return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def invoke(self, context, evt):
        print('invoking')
        #if evt.type == 'RIGHTMOUSE':
        bpy.context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}
        #return {'CANCELLED'}

class ShowFountain(bpy.types.Operator):
    bl_idname="scene.show_fountain"
    bl_label="Show fountain markers"
    
    drawing_class = None
    show = False
    
    @classmethod
    def poll(self, context):
        return True
    
    # def modal(self, context, event):
    #     for window in bpy.context.window_manager.windows:
    #         screen = window.screen

    #         for area in screen.areas:
    #             if area.type == 'VIEW_3D':
    #                 area.tag_redraw()
    #                 return {'PASS_THROUGH'}

    #     return {'CANCELLED'}

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        scn = context.scene
        try:
            fountain = scn.fountain
        except AttributeError:
            if ShowFountain.drawing_class is not None:
                ShowFountain.drawing_class.stop()
            return {'CANCELLED'}
        else:
            ShowFountain.show = fountain.show_fountain
            if ShowFountain.show:
                if ShowFountain.drawing_class is None:
                    ShowFountain.drawing_class = DrawingClass(context)
                ShowFountain.drawing_class.start(context)
            else:
                if ShowFountain.drawing_class is not None:
                    ShowFountain.drawing_class.stop()
            
            for window in bpy.context.window_manager.windows:
                screen = window.screen

                for area in screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
                        break

        return {'FINISHED'}
    
class PrintFountain(bpy.types.Operator):
    bl_idname="scene.print_fountain"
    bl_label="Print Marker's timing"

    filepath = bpy.props.StringProperty(default='youtube.srt',subtype="FILE_PATH")

    @classmethod
    def poll(self, context):
        return True

    def invoke(self, context, event):
        #return self.execute(context)
        #context.window_manager.invoke_props_dialog(self, width=400)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if len(context.scene.timeline_markers) == 0:
            self.report({'INFO'},"No markers found.")
            return {'CANCELLED'}
        
        sorted_markers = sorted(context.scene.fountain_markers, key=operator.attrgetter('frame'))
        fountain = context.scene.fountain

        markers_as_timecodes = ""
        sub_index=1
        marker_index = -1
        for marker in sorted_markers:
            marker_index += 1
            if marker.fountain_type == 'Scene Heading' and not fountain.marker_on_scene:
                continue
            if marker.fountain_type == 'Section Heading' and not fountain.marker_on_section:
                continue
            if marker.fountain_type == 'Action' and not fountain.marker_on_action:
                continue
            if marker.fountain_type == 'Dialogue' and not fountain.marker_on_dialogue:
                continue
            if marker.fountain_type == 'Transition' and not fountain.marker_on_transition:
                continue
            
            # The SRT format does not allow 0 durations
            if marker.duration <= 0:
                continue

            content = marker.content
            if marker.fountain_type == 'Dialogue':
                content = marker.target + ": " + marker.content
                if marker.is_dual_dialogue:
                    if sorted_markers[marker_index-1].is_dual_dialogue:
                        content = "%s: %s\n%s: %s"%(sorted_markers[marker_index-1].target, sorted_markers[marker_index-1].content, marker.target, marker.content)
                        marker.duration = max(marker.duration, sorted_markers[marker_index-1].duration)
                    else:
                        continue

            start = frameToTime(marker.frame, context, format='srt')
            end = frameToTime(marker.frame_end, context, format = 'srt')
            result = "%d\n%s --> %s\n%s\n"%(sub_index, start, end, content.replace('\\n','\n'))
            markers_as_timecodes += result + "\n"
            sub_index += 1
        file = open(self.filepath, 'w')
        file.write(markers_as_timecodes)        
        return {"FINISHED"}
#end PrintFountain

class MoveFountainCursor(bpy.types.Operator):
    bl_idname="scene.move_fountain_cursor"
    bl_label="Move cursor in fountain script"

    @classmethod
    def poll(self, context):
        return context.scene.fountain.script_line > 1

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        if context.scene.fountain.script_line < 0:
            return {"FINISHED"}

        #t = bpy.context.space_data.text
        #script = context.scene.fountain.get_script()

        for window in bpy.context.window_manager.windows:
            screen = window.screen

            for area in screen.areas:
                if area.type == 'TEXT_EDITOR':
                    for region in area.regions:
                        if region.type == "WINDOW":
                            #space_data = area.spaces.active
                            #t = space_data.text
                            override = context.copy()
                            override['window'] = window
                            override['screen'] = screen
                            override['area'] =  area
                            override['region'] = region
                            override['edit_text'] = context.scene.fountain.get_script()
                            bpy.ops.text.jump(override, line=context.scene.fountain.script_line)
                            bpy.ops.text.move(override, type='LINE_BEGIN')
                    break

        return {"FINISHED"}
#end MoveFountainScript

class CleanScript(bpy.types.Operator):
    bl_idname="scene.clean_fountain_script"
    bl_label="Clean fountain script"

    @classmethod
    def poll(self, context):
        return len(context.scene.fountain.script) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        body = context.scene.fountain.get_body()
        lines = body.split('\n')
        clean = []

        for line in lines:
            if line[:6] == "[[t&d:":
                continue
            if line[:4] == "[[t:":
                continue
            if line[:4] == "[[d:":
                continue
            clean.append(line)

        context.scene.fountain.get_script().from_string("\n".join(clean))
        if len(context.scene.fountain_markers) > 0:
            bpy.ops.scene.import_fountain('EXEC_DEFAULT')
        return {"FINISHED"}
#end CleanScript

class UpdateScript(bpy.types.Operator):
    bl_idname="scene.update_fountain_script"
    bl_label="Update fountain script"

    write_time = BoolProperty(default=True, name="Write Start Frame", description='Write start frame')
    write_duration = BoolProperty(default=True, name="Write Duration", description='Write duration')

    @classmethod
    def poll(self, context):
        return len(context.scene.fountain.script) > 0 and len(context.scene.fountain_markers) > 0

    def invoke(self, context, event):
        context.window_manager.invoke_props_dialog(self, width=500)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        body = context.scene.fountain.get_body()
        lines = body.split('\n')
        fountain_collection = context.scene.fountain_markers
        offset = 0
        if not self.write_time and not self.write_duration:
            return

        for f in fountain_collection:
            line = lines[f.line_number + offset]
            new_line = "[[t&d:" + str(f.frame) + " " + str(f.duration) + "]]"

            if self.write_time and not self.write_duration:
                new_line = "[[t:" + str(f.frame) + "]]"
            elif not self.write_time and self.write_duration:
                new_line = "[[d:" + str(f.duration) + "]]"

            if line.startswith("[["):
                lines[f.line_number + offset] = new_line
            else:
                lines.insert(f.line_number + offset, new_line)
                offset += 1

        context.scene.fountain.get_script().from_string("\n".join(lines))
        bpy.ops.scene.import_fountain('EXEC_DEFAULT')
        return {"FINISHED"}
#end UpdateScript

class ClearFountain(bpy.types.Operator):
    bl_idname="scene.clear_fountain"
    bl_label="Clear fountain markers"

    @classmethod
    def poll(self, context):
        return len(context.scene.fountain_markers) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        context.scene.fountain_markers.clear()
        context.scene.timeline_markers.clear()
        context.scene.fountain.reset()
        context.scene.fountain_markers_index = 0
        return {"FINISHED"}
#end UpdateScript

class ImportFountain(bpy.types.Operator):
    bl_idname="scene.import_fountain"
    bl_label="Import fountain script"

    @classmethod
    def poll(self, context):
        return len(context.scene.fountain.script) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        dir = os.path.dirname(bpy.data.filepath)
        if not dir in sys.path:
            sys.path.append(dir)

        fountain_script = context.scene.fountain.get_body()

        F = fountain.Fountain( fountain_script )
        
        if 'title' in F.metadata:
            context.scene.fountain.title = F.metadata['title'][0]

        context.scene.timeline_markers.clear()
        fountain_collection = context.scene.fountain_markers

        current_collection = {}
        for f in fountain_collection:
            current_collection[f.name] = (f.frame, f.duration)

        fountain_collection.clear()

        frame = 0
        act = 0
        sequence = 0
        scene = 0

        render = context.scene.render
        framerate = render.fps / render.fps_base

        scene_number = ""

        for fc, f in enumerate(F.elements):
            if f.element_type == 'Section Heading':
                if f.section_depth == 1:
                    act += 1
                elif f.section_depth == 2:
                    sequence += 1
                else: 
                    scene += 1

        use_scene_only = act == 0 and sequence == 0

        act = 0
        sequence = 0
        scene = 0
        element_in_scene = 0
        action_in_scene = 0
        dialogue_in_scene = 0
        transition_in_scene = 0
        target = ""
        scene_info = ""
        character = ""
        is_dual_dialogue = False
        was_dual_dialogue = False
        for fc, f in enumerate(F.elements):
            delta = 0
            element_in_scene += 1

            if f.element_type == 'Section Heading':
                if f.section_depth == 1:
                    act += 1
                elif f.section_depth == 2:
                    sequence += 1
                else: 
                    scene += 1
                element_in_scene = 0
                action_in_scene = 0
                dialogue_in_scene = 0
                target = ""
                transition_in_scene = 0

            if f.element_type == 'Scene Heading':
                scene += 1
                element_in_scene = 0
                action_in_scene = 0
                dialogue_in_scene = 0
                scene_info = f.element_text
                target = f.element_text
                transition_in_scene = 0

            if use_scene_only:
                scene_number = "S_" + str(scene)
            else:
                scene_number = "S_" + str(act) + "_" + str(sequence) + "_" + str(scene)

            if f.element_type == 'Scene Heading':
                if f.scene_number:
                    scene_number = "S_" + f.scene_number

            name = scene_number
            
            if f.element_type == 'Character':
                last_character = f.element_text
                is_dual_dialogue = f.is_dual_dialogue
                name += "C_" + f.element_text 
                name += "_" + str(element_in_scene)
                character = f.element_text
                continue
            elif f.element_type == 'Parenthetical':
                character += f.element_text
                continue
            elif f.element_type == 'Synopsis':
                continue
            elif f.element_type == 'Page Break':
                continue
            elif f.element_type == 'Boneyard':
                continue
            elif f.element_type == 'Comment':
                if f.element_text[0:4] == "t&d:":
                    time_and_duration = f.element_text[4:].split()
                    frame = int(time_and_duration[0])
                    delta = int(time_and_duration[1])
                    fountain_collection[-1].frame = frame
                    fountain_collection[-1].duration = delta
                elif f.element_text[0:4] == "t:":
                    time_and_duration = f.element_text[2:]
                    frame = int(time_and_duration)
                    fountain_collection[-1].frame = frame
                elif f.element_text[0:4] == "d:":
                    time_and_duration = f.element_text[2:]
                    delta = int(time_and_duration)
                    fountain_collection[-1].duration = delta
                continue
            elif f.element_type == 'Dialogue':
                dialogue_in_scene += 1
                word_count = len(f.element_text.split())
                delta += int(word_count * framerate * 0.5)
                name += "_D" + str(dialogue_in_scene)
                target = character
            elif f.element_type == 'Action':
                is_dual_dialogue = False
                action_in_scene += 1
                delta += int(1.0 * framerate * (f.element_text.count('.') + 1))
                name += "_A" + str(action_in_scene)
                target = scene_info
            elif f.element_type == 'Scene Heading':
                is_dual_dialogue = False
                target = scene_number
            elif f.element_type == 'Section Heading':
                is_dual_dialogue = False
                target = scene_number
            elif f.element_type == 'Transition':
                is_dual_dialogue = False
                target = ""
                transition_in_scene += 1
                name += "_T" + str(transition_in_scene)
                delta += int(2.0 * framerate)
            else:
                continue

            skip = False
            if f.element_type == 'Scene Heading' and not context.scene.fountain.marker_on_scene:
                skip = True
            if f.element_type == 'Section Heading' and not context.scene.fountain.marker_on_section:
                skip = True
            if f.element_type == 'Action' and not context.scene.fountain.marker_on_action:
                skip = True
            if f.element_type == 'Dialogue' and not context.scene.fountain.marker_on_dialogue:
                skip = True
            if f.element_type == 'Transition' and not context.scene.fountain.marker_on_transition:
                skip = True

            if skip:
                frame += delta
                continue

            element = fountain_collection.add()
            element.sequence = len(fountain_collection)
            element.is_dual_dialogue = is_dual_dialogue
            element.fountain_type = f.element_type
            element.content = f.element_text
            element.frame = frame
            element.name = name
            element.target = target
            element.duration = delta
            element.line_number = f.original_line + 2

            frame += delta

            if is_dual_dialogue and was_dual_dialogue:
                element.frame = fountain_collection[-2].frame
                delta_max = max(element.duration, fountain_collection[-2].duration)
                frame = element.frame + delta_max
                was_dual_dialogue = False
            else:
                was_dual_dialogue = is_dual_dialogue

            if name in current_collection:
                element.frame, element.duration = current_collection[name]
                frame = element.frame
                delta = element.duration

        f_index= -1
        for f in fountain_collection:
            f_index += 1
            context.scene.timeline_markers.new(f.name, f.frame)
            if f.duration > 0:
                f.frame_end = f.frame + f.duration
            else:
                if f.fountain_type == 'Scene Heading':
                    #Find next Scene Heading to determine the duration / end time
                    for other in fountain_collection[f_index+1:]:
                        if other.fountain_type == 'Scene Heading':
                            f.duration = other.frame - f.frame 
                            f.frame_end = other.frame 
                            break

        context.scene.frame_end = frame

        return {"FINISHED"}
#end import Fountain


class MoveElements(bpy.types.Operator):
    bl_idname="scene.move_markers"
    bl_label="Move fountain elements"

    @classmethod
    def poll(self, context):
        return True

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        n = 0
        name = ''
        for marker in context.scene.timeline_markers:
            if marker.select:
                n += 1
                name = marker.name
            if n>2:
                break
        if n == 0:
            self.report({'WARNING'},"Select 1 marker")
            return {'CANCELLED'}
        if n > 1:
            self.report({'WARNING'},"Select only 1 marker")
            return {'CANCELLED'}
        
        current_frame = -1
        current_index = -1
        for f in bpy.context.scene.fountain_markers:
            if f.name == name:
                current_frame = f.frame
                current_index = f.sequence - 1

        if current_frame < 0:
            self.report({'WARNING'},"Select a Fountain marker")
            return {'CANCELLED'}

        #let's check that the sequence is respected
        if current_index > 0:
            if bpy.context.scene.fountain_markers[current_index-1].frame > context.scene.frame_current:
                self.report({'ERROR'},"You can't reorder a sequence. Change the script for that.")
                return {'CANCELLED'}
            if bpy.context.scene.fountain.fix_duration:
                reversed = bpy.context.scene.fountain_markers[:current_index]
                fountain_type = bpy.context.scene.fountain_markers[current_index].fountain_type
                for f in reversed:
                    if f.frame_end > current_frame and (
                        f.fountain_type == fountain_type or \
                        fountain_type == 'Scene Heading' or \
                        fountain_type == "Transition" or \
                        f.fountain_type == "Transition"):
                        f.frame_end = current_frame
                        f.duration = f.frame_end - f.frame

        delta = current_frame - context.scene.frame_current

        for f in bpy.context.scene.fountain_markers:
            if f.frame >= current_frame:
                f.frame -= delta
                f.frame_end -= delta
        
        for m in context.scene.timeline_markers:
            if m.frame >= current_frame:
                m.frame -= delta
        
        set_markers(context)

        return {"FINISHED"}

class ShowEndMarkers(bpy.types.Operator):
    bl_idname="scene.show_end_markers"
    bl_label="Show end markers"

    @classmethod
    def poll(self, context):
        return True

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        
        if len(context.scene.timeline_markers) == 0:
            self.report({'INFO'},"No markers found.")
            return {'CANCELLED'}
        
        startSelected = { marker.name:marker.select for marker in context.scene.timeline_markers}

        # remove all end markers
        for marker in context.scene.timeline_markers:
            name = marker.name
            if name[:6] == 'EndOf_':
                name = name[6:]
                context.scene.timeline_markers.remove(marker)
        
        # add end markers for selected markers
        for f in bpy.context.scene.fountain_markers:
            if startSelected[f.name]:
                context.scene.timeline_markers.new('EndOf_' + f.name, f.frame_end)
                        
        return {"FINISHED"}

def set_markers(context):
    selected = []
    for marker in context.scene.timeline_markers:
        if marker.select:
            selected += [marker.name]

    context.scene.timeline_markers.clear()
    for f in context.scene.fountain_markers:
        marker = context.scene.timeline_markers.new(f.name, f.frame)
        if marker.name not in selected:
            marker.select = False

class SynchFrom(bpy.types.Operator):
    bl_idname="scene.synch_markers"
    bl_label="Synch markers to fountain"

    def __init__(self):
        self.framePattern = re.compile(r"$.*_[0-9]+$")

    @classmethod
    def poll(self, context):
        return len(context.scene.timeline_markers) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        render = context.scene.render
        
        if len(context.scene.timeline_markers) == 0:
            self.report({'INFO'},"No markers found.")
            return {'CANCELLED'}
        
        sorted_markers = sorted(context.scene.timeline_markers, key=operator.attrgetter('frame'))

        all_selected = all(marker.select for marker in sorted_markers)
        selected = 0
        selected_name = None

        for marker in sorted_markers:
            if not all_selected and not marker.select:
                continue

            selected += 1
            done = False
            name = marker.name
            set_duration = False
            if name[:6] == 'EndOf_':
                name = name[6:]
                set_duration = True

            selected_name = marker.name

            for fountain_marker in bpy.context.scene.fountain_markers:
                if fountain_marker.name == name:
                    current_index = fountain_marker.sequence - 1
                    if current_index > 0:
                        if bpy.context.scene.fountain_markers[current_index-1].frame > marker.frame:
                            set_markers(context)
                            self.report({'ERROR'},"You can't reorder a sequence. Change the script for that.")
                            return {'CANCELLED'}
                    if current_index < len(bpy.context.scene.fountain_markers) - 2:
                        if bpy.context.scene.fountain_markers[current_index+1].frame < marker.frame:
                            set_markers(context)
                            self.report({'ERROR'},"You can't reorder a sequence. Change the script for that.")
                            return {'CANCELLED'}

                    if set_duration:
                        if fountain_marker.frame < marker.frame:
                            fountain_marker.frame_end = marker.frame
                            fountain_marker.duration = fountain_marker.frame_end - fountain_marker.frame
                    else:
                        fountain_marker.frame = marker.frame
                        fountain_marker.frame_end = fountain_marker.frame + fountain_marker.duration
                        fountain_marker.marker = marker
                        fountain_marker.original_name = marker.name

                    if bpy.context.scene.fountain.fix_duration:
                        current_frame = fountain_marker.frame
                        reversed = bpy.context.scene.fountain_markers[:current_index]
                        fountain_type = bpy.context.scene.fountain_markers[current_index].fountain_type
                        for f in reversed:
                            if f.frame_end > current_frame and (
                                f.fountain_type == fountain_type or \
                                fountain_type == 'Scene Heading' or \
                                fountain_type == "Transition" or \
                                f.fountain_type == "Transition"):
                                f.frame_end = current_frame
                                f.duration = f.frame_end - f.frame

                    done = True
                    break


        if selected == 1:
            n = 0
            for f in bpy.context.scene.fountain_markers:
                if f.name == name:
                    bpy.context.scene.fountain_markers_index = n
                    break
                n += 1

        return {"FINISHED"}

def make_key(obj):
    import uuid
    return str(uuid.uuid4())

def get_uid(self):
    #if "uid" in self.keys():
    #    return self['uid']
    return make_key(self)
    #if "uid" not in self.keys():
    #    self["uid"] = make_key(self)
    #return self["uid"]

class UidProperty(property):
    def __init__(self):
        super().__init__(get_uid)
#        self = make_key(self)



class FountainMarker_UI_Item(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            split = layout.split(0.3)
            split.label(str(item.frame))
            split.label(item.name)

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.name)

    def invoke(self, context, event):
        pass

#bpy.types.TimelineMarker.uid = property(get_uid)

classes = [FountainProps, FountainPanel, PrintFountain, FountainMarker, SynchFrom, FountainMarker_UI_Item]

from bpy.app.handlers import persistent

@persistent
def monitor_markers(dummy):
    bpy.ops.scene.check_markers()


def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.fountain_title = bpy.props.StringProperty(
        name="Title",
        description="Fountain description"
        )
    bpy.types.Scene.fountain = bpy.props.PointerProperty(type=FountainProps)
    bpy.types.Scene.fountain_markers = bpy.props.CollectionProperty(type=FountainMarker)
    bpy.types.Scene.fountain_markers_index = bpy.props.IntProperty()
    #bpy.ops.scene.show_fountain('EXEC_DEFAULT')
    ShowFountain.drawing_class = DrawingClass(bpy.context)
    #bpy.app.handlers.load_post.append(monitor_markers)
  
def unregister():
    #bpy.app.handlers.load_post.remove(monitor_markers)
    ShowFountain.drawing_class = None
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.fountain_title
    del bpy.types.Scene.fountain_markers
    del bpy.types.Scene.fountain

if __name__ == "__main__":
    register()