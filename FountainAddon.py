import bpy
import math
import operator
import re
import sys
import os
import bgl
import blf
from bpy.types import Panel, Operator, Menu, PropertyGroup
from bpy.props import *

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir )

from fountain import fountain
    

bl_info = \
    {
        "name" : "Fountain marker",
        "author" : "Philippe Lavoie <philippe.lavoie@gmail.com>",
        "version" : (1, 0, 0),
        "blender" : (2, 5, 7),
        "location" : "View 3D > Tools > Animation",
        "description" :
            "Allows you to add fountain markers to a scene with dialogue and action descriptions",
        "warning" : "",
        "wiki_url" : "",
        "tracker_url" : "",
        "category" : "Animation",
    }

# list of texts
def texts(self, context):
    return [(text.name, text.name, '') for text in bpy.data.texts]

def frameToTime(frame, context, verbose = True):
    render = context.scene.render
    framerate = render.fps / render.fps_base
    time_in_seconds = frame / framerate
    minutes = math.floor(time_in_seconds / 60.0)
    seconds = time_in_seconds - (minutes * 60)
    if verbose:
        if minutes>0:
            return "{:0d} min {:00.2f}sec".format(minutes, seconds)
        else:
            return "{:0.2f} sec".format(seconds)
    else:
        return "{:02d}:{:00.2f}".format(minutes, seconds)

def stringFits(pstr, max_width):
    font_id = 0
    text_width, text_height = blf.dimensions(font_id, pstr)
    return text_width < max_width

def draw_string(x, y, packed_strings, left_align=True, bottom_align=False, max_width=0.7):
    font_id = 0
    blf.size(font_id, 14, 72) 
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
    if not left_align:
        line_width=0
        for command in packed_strings:
            if len(command) == 2:
                pstr, pcol = command
                text_width, text_height = blf.dimensions(font_id, pstr)
                line_width += text_width
                # print("max: " + str(max_width) + "/" + str(text_width) + "/" + str(line_width) + " : " + pstr)
                # if line_width > max_width:
                #     previous_width = line_width - text_width
                #     if previous_width <= 0:
                #         previous_width = 0    
                #     split_index = int(len(pstr) * (1.0 - ((text_width - previous_width - max_width) / max_width)))
                #     print('split at ' + str(split_index))
                #     split_index = pstr.rfind(' ', 0, split_index)
                #     if split_index > 0:
                #         new_pack = packed_strings[:index]
                #         new_pack.append((pstr[:split_index], pcol))
                #         new_pack.append( '\n')
                #         if len(packed_strings) <= index:
                #             next_command = new_pack[index+1]
                #             if len(next_command) == 2:
                #                 n_pstr, pcol = next_command
                #                 new_pack.append( (pstr[split_index:] + n_pstr, pcol) )
                #                 if len(packed_strings) <= index + 2:
                #                     new_pack.append(packed_strings[index+2:])
                #         else:
                #             new_pack.append((pstr[split_index+1:], pcol))
                #         draw_string(x,y,new_pack, left_align=left_align, bottom_align=bottom_align, max_width=max_width)
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
        if not left_align:
            line_width=line_widths[index]
                        
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
    return max_size

class DrawingClass:
    def __init__(self, context):
        self.handle = bpy.types.SpaceView3D.draw_handler_add(
                   self.draw_text_callback,(context,),
                   'WINDOW', 'POST_PIXEL')
        self.scene = "Scene"
        self.action = "Action\naction"
        self.dialogue = "Dialogue\ndialogue"
        self.marker = "MarkerName"
        self.character = ""
        self.last_frame = -1
        self.last_index = 0

    def set_content(self, element):
        self.marker = element.name
        self.character = ""
        if element.fountain_type == 'Scene Heading':
            self.scene = element.content
            self.action = ""
            self.dialogue = ""
        elif element.fountain_type == 'Transition':
            self.scene = element.content
            self.action = "Transition"
        elif element.fountain_type == 'Action':
            self.action = element.content
            self.dialogue = ""
        elif element.fountain_type == 'Dialogue':
            self.dialogue = element.content
            self.character = element.target

    def updateFountainElements(self, context):
        frame = context.scene.frame_current

        if self.last_frame == frame:
            return

        fountain_collection = sorted(context.scene.fountain_markers, key  = lambda item : item.frame)

        if self.last_frame < frame:
            range = fountain_collection[self.last_index:]
            for element in [element for element in range if element.frame <= frame]:
                self.last_index += 1
                self.set_content(element)
            self.last_frame = frame
            return
        
        self.last_index = 0
        self.dialogue = ""
        self.action = ""
        self.scene = ""
        self.marker = ""
        self.character = ""
        for element in [element for element in fountain_collection if element.frame <= frame]:
            self.last_index += 1
            self.set_content(element)
        self.last_frame = frame

    def draw_text_callback(self, context):
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

        self.updateFountainElements(context)

        x = 60
        y = 60
        RED = (1, 0, 0, 1)
        GREEN = (0, 1, 0, 1)
        BLUE = (0, 0, 1, 1)
        CYAN = (0, 1, 1, 1)
        MAGENTA = (1,0,1,1)
        YELLOW = (1, 1, 0, 1)
        ORANGE = (1, 0.8, 0, 1)
        WHITE = (1,1,1,0.8)
        FULLWHITE = (1,1,1,1)
        CR = "\n"

        ps = [(self.scene, WHITE),CR, (self.marker, WHITE)]
        x = self.width-20
        y = 60
        label_size = draw_string(x, y, ps, left_align=False, max_width=0.2 * self.width) + 40

        screen_max_characters = context.scene.fountain.max_characters

        if self.action:
            ps = []
            for line in self.action.splitlines():
                while len(line) > screen_max_characters or not stringFits(line, self.width - 40):
                    screen_max_characters = context.scene.fountain.max_characters
                    while not stringFits(line[:screen_max_characters], self.width - 40):
                        split_index = line.rfind(' ', 0, screen_max_characters)
                        if split_index <= 0:
                            break
                        screen_max_characters = split_index

                    split_index = line.rfind(' ', 0, screen_max_characters)
                    if split_index > 0:
                        ps.append( (line[:split_index], CYAN))
                        ps.append( CR )
                        line = line[split_index+1:]    
                    else:
                        break
                if line == 'Transition':
                    ps.append( (line, MAGENTA))
                else:
                    ps.append( (line, CYAN))
                ps.append( CR )
            x = 20
            y = self.height-70
            draw_string(x, y, ps, left_align=True, bottom_align=False, max_width= self.width - 40)

        if self.dialogue:
            ps = []
            ps.append( (self.character + " : ", ORANGE) )
            max_characters = context.scene.fountain.max_characters - len(self.character) - 3
            for line in self.dialogue.splitlines():
                while len(line) > max_characters or not stringFits(self.character + " : " + line, self.width - label_size):
                    screen_max_characters = max_characters
                    while not stringFits(self.character + " : " + line[:screen_max_characters], self.width - label_size):
                        split_index = line.rfind(' ', 0, screen_max_characters)
                        if split_index <= 0:
                            break
                        screen_max_characters = split_index

                    split_index = line.rfind(' ', 0, screen_max_characters)
                    if split_index > 0:
                        ps.append( (line[:split_index], YELLOW))
                        ps.append( CR )
                        ps.append( (' ' * (len(self.character) + 3), YELLOW))
                        line = line[split_index+1:]    
                    else:
                        break
                ps.append( (line, YELLOW))
                ps.append( CR )

            x = 60
            y = 40
            draw_string(x, y, ps, left_align=True, bottom_align=True, max_width= self.width - label_size)            

    def remove_handle(self):
         bpy.types.SpaceView3D.draw_handler_remove(self.handle, 'WINDOW')



class FountainProps(PropertyGroup):
    def update_text_list(self, context):
        self.script = bpy.data.texts[self.scene_texts].name    
        
        return None

    def updateShow(self, context):
        bpy.ops.scene.show_fountain('EXEC_DEFAULT')
    
    name = StringProperty(default="Fountain script")
    show_fountain = BoolProperty(default=False, update = updateShow)
    script = StringProperty(default='', description='Choose your script')
    scene_texts = EnumProperty(name = 'Available Texts', items = texts, update = update_text_list,
                                         description = 'Available Texts.')
    marker_on_scene = BoolProperty(default=True)
    marker_on_action = BoolProperty(default=True)
    marker_on_transition = BoolProperty(default=True)
    marker_on_section = BoolProperty(default=True)
    marker_on_dialogue = BoolProperty(default=True)
    title = StringProperty(default="")
    max_characters = IntProperty(default=80)
       
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
    
    name = bpy.props.StringProperty(update=updateName)
    original_name = bpy.props.StringProperty()
    frame = bpy.props.IntProperty()
    duration = bpy.props.IntProperty()

    fountain_type = bpy.props.EnumProperty(
                    name='Foutain element type',
                    description='The element in the fountain script',
                    items={
                        ('Section Heading','Section Heading','A section heading'),
                        ('Comment','Comment','A comment'),
                        ('Scene Heading','Scene Heading','A scene heading'),
                        ('Transition','Transition','A transition to a different scene'),
                        ('Action','Action','An action that should be depicted'),
                        ('Dialogue','Dialogue','A dialogue from a character'),
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

#    def execute(self, context):
#        if not context.scene.fountain_markers:
#            scene.synch_markers(context)

    def draw(self, context):
        scn = context.scene
        fountain = scn.fountain
        
        row = self.layout.row()
        column = row.column(align=True)
        row = column.row(align=True)
        row.prop(fountain, 'show_fountain', text='Show Scene information')
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
        row.operator("scene.print_fountain", text="Print Markers")
        row.operator("scene.synch_markers", text="Sync markers")

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
            column.prop(item, "content")
            column.prop(item, "target")
            column.prop(item, "line_number")
            if item.duration > 0:                
                column.label("At " + frameToTime(item.frame, context) + " for " + frameToTime(item.duration, context))
            else:
                column.label("At " + frameToTime(item.frame, context))
            
#end FountainPanel

class ShowFountain(bpy.types.Operator):
    bl_idname="scene.show_fountain"
    bl_label="Show fountain markers"
    
    drawing_class = None
    
    @classmethod
    def poll(self, context):
        return True
    
    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        scn = context.scene
        fountain = scn.fountain
        
        if fountain.show_fountain:
            if ShowFountain.drawing_class is None:
                ShowFountain.drawing_class = DrawingClass(context)
        else:
            if ShowFountain.drawing_class is not None:
                ShowFountain.drawing_class.remove_handle()
                ShowFountain.drawing_class = None
        return {"FINISHED"}
    
class PrintFountain(bpy.types.Operator):
    bl_idname="scene.print_fountain"
    bl_label="Print Marker's timing"

    @classmethod
    def poll(self, context):
        return True

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        if len(context.scene.timeline_markers) == 0:
            self.report({'INFO'},"No markers found.")
            return {'CANCELLED'}
        
        sorted_markers = sorted(context.scene.fountain_markers, key=operator.attrgetter('frame'))
        fountain = context.scene.fountain

        markers_as_timecodes = ""
        for marker in sorted_markers:
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
            
            result = frameToTime(marker.frame, context, verbose=False) + " " + marker.content
            markers_as_timecodes += result + "\n"
        print(markers_as_timecodes)
        return {"FINISHED"}
#end PrintFountain

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
            clean.append(line)

        context.scene.fountain.get_script().from_string("\n".join(clean))
        if len(context.scene.fountain_markers) > 0:
            bpy.ops.scene.import_fountain('EXEC_DEFAULT')
        return {"FINISHED"}
#end CleanScript

class UpdateScript(bpy.types.Operator):
    bl_idname="scene.update_fountain_script"
    bl_label="Update fountain script"

    @classmethod
    def poll(self, context):
        return len(context.scene.fountain.script) > 0 and len(context.scene.fountain_markers) > 0

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        body = context.scene.fountain.get_body()
        lines = body.split('\n')
        fountain_collection = context.scene.fountain_markers
        offset = 0
        for f in fountain_collection:
            line = lines[f.line_number + offset]
            new_line = "[[t&d:" + str(f.frame) + " " + str(f.duration) + "]]"
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
                continue
            elif f.element_type == 'Dialogue':
                dialogue_in_scene += 1
                word_count = len(f.element_text.split())
                delta += int(word_count * framerate * 0.5)
                name += "_D" + str(dialogue_in_scene)
                target = character
            elif f.element_type == 'Action':
                action_in_scene += 1
                delta += int(1.0 * framerate * (f.element_text.count('.') + 1))
                name += "_A" + str(action_in_scene)
                target = scene_info
            elif f.element_type == 'Scene Heading':
                target = scene_number
            elif f.element_type == 'Section Heading':
                target = scene_number
            elif f.element_type == 'Transition':
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
            element.is_dual_dialogue = is_dual_dialogue
            element.fountain_type = f.element_type
            element.content = f.element_text
            element.frame = frame
            element.name = name
            element.target = target
            element.duration = delta
            element.line_number = f.original_line + 2

            print(element.name + ' : ' + str(element.frame))

            frame += delta

            if name in current_collection:
                element.frame, element.duration = current_collection[name]
                frame = element.frame
                delta = element.duration

            if is_dual_dialogue:
                element.frame = fountain_collection[-2].frame

        
        for f in fountain_collection:
            context.scene.timeline_markers.new(f.name, f.frame)

        context.scene.frame_end = frame

        print()

        return {"FINISHED"}
#end import Fountain
    
class SynchFrom(bpy.types.Operator):
    bl_idname="scene.synch_markers"
    bl_label="Synch markers to fountain"

    def __init__(self):
        self.framePattern = re.compile(r"$.*_[0-9]+$")

    @classmethod
    def poll(self, context):
        return True

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        render = context.scene.render
        
        if len(context.scene.timeline_markers) == 0:
            self.report({'INFO'},"No markers found.")
            return {'CANCELLED'}
        
        sorted_markers = sorted(context.scene.timeline_markers, key=operator.attrgetter('frame'))

        names = []

        for marker in sorted_markers:
            if marker.name in names:
                if self.framePattern.search(marker.name) is not None:
                    marker.name = re.sub("_\d+$", "_" + str(marker.frame), marker.name)
            names += [marker.name]

        markers_as_timecodes = ""
        framerate = render.fps / render.fps_base
        for marker in sorted_markers:
            time_in_seconds = marker.frame / framerate
            minutes = math.floor(time_in_seconds / 60.0)
            seconds = time_in_seconds - (minutes * 60)
            result = "{:02d}:{:00.2f}".format(minutes, seconds) + " " + marker.name
            done = False
            for fountain_marker in bpy.context.scene.fountain_markers:
                if fountain_marker.name == marker.name:
                    fountain_marker.frame = marker.frame
                    fountain_marker.duration = time_in_seconds
                    fountain_marker.marker = marker
                    fountain_marker.original_name = marker.name
                    done = True
                    break
            if not done:
                new_marker = bpy.context.scene.fountain_markers.add()
                new_marker.name = marker.name
                new_marker.original_name = marker.name
                new_marker.frame = marker.frame
                new_marker.duration = time_in_seconds
                new_marker.marker = marker
                        
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




def register():
    #for cls in classes:
    #    bpy.utils.register_class(cls)
    bpy.utils.register_module(__name__)
    bpy.types.Scene.fountain_title = bpy.props.StringProperty(
        name="Title",
        description="Fountain description"
        )
    bpy.types.Scene.fountain = bpy.props.PointerProperty(type=FountainProps)
    bpy.types.Scene.fountain_markers = bpy.props.CollectionProperty(type=FountainMarker)
    bpy.types.Scene.fountain_markers_index = bpy.props.IntProperty()
  
def unregister():
    #for cls in classes:
    #    bpy.utils.unregister_class(cls)
    bpy.utils.unregister_module(__name__)
    del bpy.types.Scene.fountain_title
    del bpy.types.Scene.fountain_markers
    del bpy.types.Scene.fountain

if __name__ == "__main__":
    register()