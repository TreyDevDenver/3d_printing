# ChangeAtHeight script - Change filament or pause at a given height
# This script was based on the PauseAtZ plugin for legacy Cura.
# It runs with the PostProcessingPlugin which is released under the terms of the AGPLv3 or higher.
# This script is licensed under the Creative Commons - Attribution - Non-Commercial - No Derivatives license

#Authors of the ChangeAtZ plugin / script:
# Written by Marcus Adams, rawlogic@gmail.com

from ..Script import Script
import re
from UM.Application import Application
class ChangeAtHeight(Script):
    version = "3.4"
    def __init__(self):
        super().__init__()
    
    def getSettingDataString(self):
        return """{
            "name":"Change filament at height """ + self.version + """",
            "key": "ChangeAtHeight",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "pause_type":
                {
                    "label": "Pause type",
                    "description": "Pause at height or at layer number.",
                    "type": "enum",
                    "options": {"height":"Height","layer":"Layer"},
                    "default_value": "layer"
                },
                "pause_method":
                {
                    "label": "Pause/Change method",
                    "description": "Choose a method that is supported by your printer. M25 Pause SD Print (Repetier, Marlin, Sprinter, RepRap). M0 Stop (Marlin, RepRap, CR-10S). M600 Filament Change (Marlin). M25 gives you the most control and uses the printer's Resume Print feature to resume. M0 resumes when you press the button on your printer's control box, which prevents you from using your control box while paused. M600 functionality relies entirely on the implementation of your firmware's Filament Change feature.",
                    "type": "enum",
                    "options": {"m25":"M25 Pause SD Print","m0":"M0 Stop","m600":"M600 Filament Change"},
                    "default_value": "m25"
                },
                "pause_height":
                {
                    "label": "Pause at height",
                    "description": "At what height should the pause occur.",
                    "unit": "mm",
                    "type": "float",
                    "minimum_value": "0.0",
                    "default_value": 5.0,
                    "enabled": "pause_type == 'height'"
                },
                "pause_layer":
                {
                    "label": "Pause at layer",
                    "description": "At what layer should the pause occur (first layer is 1).",
                    "unit": "",
                    "type": "int",
                    "minimum_value": "1",
                    "default_value": 1,
                    "enabled": "pause_type == 'layer'"
                },
                "change_filament":
                {
                    "label": "Change filament at pause",
                    "description": "Change the filament at pause, otherwise, just pause.",
                    "type": "bool",
                    "default_value": true,
                    "enabled": "pause_method != 'm600'"
                },
                "cool_down":
                {
                    "label": "Cool extruder on pause",
                    "description": "Turns extruder heat off on first pause to prevent burned filament and nozzle clogging. On first continue, heats extruder back up, beeps, and pauses again to allow for filament change.",
                    "type": "bool",
                    "default_value": true,
                    "enabled": "pause_method != 'm600'"
                },
                "beep":
                {
                    "label": "Beep",
                    "description": "Beeps at each step of the process to let you know.",
                    "type": "bool",
                    "default_value": true
                },
                "head_park_x":
                {
                    "label": "Park print head X",
                    "description": "What x location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 10,
                    "enabled": "pause_method != 'm600'"
                },
                "head_park_y":
                {
                    "label": "Park print head Y",
                    "description": "What y location does the head move to when pausing.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 10,
                    "enabled": "pause_method != 'm600'"
                },
                "head_move_z":
                {
                    "label": "Move print head Z",
                    "description": "This is the relative amount to lift the print head from the current z position before parking. A value of 0 will cause it to lift one layer. It will always move up to at least the minimum park amount to ensure you have room under the nozzle to work.",
                    "unit": "mm",
                    "type": "float",
                    "minimum_value": "0",
                    "default_value": 5,
                    "enabled": "pause_method != 'm600'"
                },
                "min_head_park_z":
                {
                    "label": "Minimum park print head Z",
                    "description": "This is the minimum Z position to park the head to ensure that you have room under the nozzle to work.",
                    "unit": "mm",
                    "type": "float",
                    "minimum_value": "0",
                    "default_value": 25,
                    "enabled": "pause_method != 'm600'"
                },
                "retraction_mm":
                {
                    "label": "Retraction distance",
                    "description": "Retracting the filament occurs immediately before the head is parked and right before the head moves to the resume position to prevent oozing while the print head travels.",
                    "unit": "mm",
                    "type": "float",
                    "minimum_value": "0",
                    "default_value": 5,
                    "enabled": "pause_method != 'm600'"
                },
                "extrusion_mm":
                {
                    "label": "Extrusion distance",
                    "description": "Extruding the filament occurs right after the head reaches the resume position and before it resumes printing. It reverses the previous retraction.",
                    "unit": "mm",
                    "type": "float",
                    "minimum_value": "0",
                    "default_value": 5,
                    "enabled": "pause_method != 'm600'"
                },
                "prime_mm":
                {
                    "label": "Prime distance",
                    "description": "Extruding the filament then immediately retracting it very quickly helps prime the nozzle after you load the new filament.",
                    "unit": "mm",
                    "type": "float",
                    "minimum_value": "0",
                    "default_value": 5,
                    "enabled": "pause_method != 'm600'"
                }
            }
        }"""
    
    #   Convenience function that finds the value in a line of g-code.
    #   When requesting key = x from line "G1 X100" the value 100 is returned.
    #   Override original function, which didn't handle values without a leading zero like ".3"
    #   Ignores keys found in comments (after ";"), but if you pass the semicolon in, you're good. eg. ";LAYER:"
    def getValue(self, line, key, default = None):
        if not key in line or (';' in line and line.find(key) > line.find(';')):
            return default
        sub_part = line[line.find(key) + len(key):]
        m = re.search('^-?[0-9]+\.?[0-9]*', sub_part)
        if m is None:
            m = re.search('^-?[0-9]*\.?[0-9]+', sub_part)
        if m is None:
            return default
        try:
            return float(m.group(0))
        except:
            return default
    
    def execute(self, data):
        # Initialize variables
        ready = False
        x = None
        y = None
        last_e = 0.
        last_e_age = 0
        last_e_temp = 0.
        current_z = None
        current_layer = 0
        currently_in_custom = False
        # Default to absolute mode because most printers do, unless we find otherwise
        extruder_absolute_mode = True
        position_absolute_mode = True
        # Get the user values into variables
        pause_type = self.getSettingValueByKey("pause_type")
        pause_method = self.getSettingValueByKey("pause_method")
        pause_z = self.getSettingValueByKey("pause_height")
        pause_layer = self.getSettingValueByKey("pause_layer")
        park_x = self.getSettingValueByKey("head_park_x")
        park_y = self.getSettingValueByKey("head_park_y")
        move_z = self.getSettingValueByKey("head_move_z")
        retraction_mm = self.getSettingValueByKey("retraction_mm")
        extrusion_mm = self.getSettingValueByKey("extrusion_mm")
        prime_mm = self.getSettingValueByKey("prime_mm")
        min_head_park_z = self.getSettingValueByKey("min_head_park_z")
        
        # Iterate through all the layers
        for layer in data:
            lines = layer.split("\n")
            # Iterate through the lines for each layer
            for line in lines:
                # Skip lines inside of CUSTOM
                if currently_in_custom:
                    if ';CUSTOM' in line:
                        currently_in_custom = False
                    continue
                elif ';TYPE:CUSTOM' in line:
                    currently_in_custom = True
                    continue
                
                # We're not inside 'CUSTOM', now start processing
                # The LAYER_COUNT always comes before the LAYER, so LAYER_COUNT resets the layer. This is to let us work for print sequence: One at a Time
                lc = self.getValue(line, ";LAYER_COUNT:")
                if lc is not None:
                    current_layer = 0
                    ready = True
                    continue
                # Get the current LAYER number
                # They start at 0, unless they're using a raft, then it starts negative
                l = self.getValue(line, ";LAYER:")
                if l is not None:
                    current_layer = current_layer + 1
                
                # Get the E (extrusion) value from the current line. Will be None if none.
                e = self.getValue(line, "E")
                # Remember the last highest E (extrusion) value so that we can resume there after a pause
                if e is not None and e > last_e:
                    last_e = e
                    last_e_age = 0
                
                # This is to handle those anomalous high E values, we'll forget the high values after three lower values
                if e is not None and e < last_e:
                    if last_e_age < 3:
                        last_e_age = last_e_age + 1
                    else:
                        last_e = e
                        last_e_age = 0
                
                # Get the current extruder temp
                # Get the M (RepRap command) value from the current line.  Will be None if none.
                m = self.getValue(line, "M")
                if m is not None:
                    if m == 104 or m == 109:
                        # Nozzle temps
                        # Get the S (command parameter) value
                        s = self.getValue(line, "S")
                        if s is not None:
                            last_e_temp = s
                    elif m == 82:
                        # Extruder absolute mode
                        extruder_absolute_mode = True
                    elif m == 83:
                        # Extruder relative mode
                        extruder_absolute_mode = False
                # Get the G value. G0 and G1 are moves. Will be None if none.
                g = self.getValue(line, "G")
                
                # Did they reset the extruder value?
                if g == 90:
                    position_absolute_mode = True
                elif g == 91:
                    position_absolute_mode = False
                elif g == 92:
                    x = self.getValue(line, "X")
                    y = self.getValue(line, "Y")
                    z = self.getValue(line, "Z")
                    if e is None and x is None and y is None and z is None: 
                        last_e = 0.
                    if e is not None:
                        last_e = e
                elif g == 1 or g == 0:
                    # It was a move, get the X and Y values from the move line
                    x = self.getValue(line, "X")
                    y = self.getValue(line, "Y")
                    
                    # Not every line will have a Z value, but at least the first move on each layer will have one when it moves to that Z height. If we record the Z value, that will always be our current Z height
                    # Get the Z value. Will be None if none
                    current_z = self.getValue(line, "Z")
                    
                    # If we have a height, and we're at least at the first layer, and we're moving, then it's time to see if we should pause
                    if ready and current_layer > 0 and current_z is not None and x is not None and y is not None:
                        # If the current height >= where they want to pause, then we want to pause before we do the next move
                        if (pause_type == 'height' and current_z >= pause_z) or (pause_type == 'layer' and current_layer >= pause_layer):
                            # We need to know where in the file we are in relation to layer and line so we can insert some stuff there
                            data_index = data.index(layer)
                            line_index = lines.index(line)
                            
                            # Build up the stuff that we're going to insert
                            # Gcode comments start with semi colon
                            # Put in a TYPE:CUSTOM header just so they know who (the script) added the following Gcode
                            prepend_gcode = ";TYPE:CUSTOM\n"
                            prepend_gcode += ";added code by post processing\n"
                            prepend_gcode += ";script: ChangeAtHeight.py\n"
                            prepend_gcode += ";current z: %f\n" % (current_z)
                            
                            # Move nozzle away from the bed so they can get their fingers under the nozzle
                            # Don't allow negative moveZ value. That would be bad. They would hit their print.
                            if move_z < 0:
                                move_z = 0
                            
                            new_z = 0
                            # Always move up to at least min z park value
                            if current_z + move_z < min_head_park_z:
                                new_z = min_head_park_z
                            else:
                                # We're getting the Max Z value from their print settings to make sure we don't go higher than their printer allows
                                # For Safety Leave a 10mm space (endstop)
                                max_z = Application.getInstance().getGlobalContainerStack().getProperty("machine_height", "value") - 10
                                new_z = current_z + move_z
                                if new_z > max_z:
                                    new_z = max_z
                            
                            # Move X and Y
                            # Don't allow negative park values
                            if park_x < 0:
                                park_x = 0
                            if park_y < 0:
                                park_y = 0
                            
                            # We're getting the Max X and Y values to make sure we don't go off the bed
                            # For Safety Leave a 10mm space (endstop)
                            max_x = Application.getInstance().getGlobalContainerStack().getProperty("machine_width", "value") - 10
                            # For Safety Leave a 10mm space (endstop)
                            max_y = Application.getInstance().getGlobalContainerStack().getProperty("machine_depth", "value") - 10
                            # Make sure x and y are within machine range
                            if park_x > max_x:
                                park_x = max_x
                            if park_y > max_y:
                                park_y = max_y
                            
                            if pause_method == 'm600':
                                if self.getSettingValueByKey("beep"):
                                    # Beep to let them know that we paused
                                    prepend_gcode += "M400  ;Wait for buffer to clear\n"
                                    prepend_gcode += "M300  ;Beep\n"
                                prepend_gcode += "M600 ; Filament Change\n"
                            else:
                                # Retraction
                                if extruder_absolute_mode:
                                    prepend_gcode += "M83  ;Set extruder to relative mode\n"
                                prepend_gcode += "G1 E-%f F2400  ;Retract\n" % (retraction_mm)
                                
                                # Move head away
                                # Z first
                                prepend_gcode += "G1 Z%f F3000   ;Move head up\n" % (new_z)
                                # Now X and Y
                                prepend_gcode += "G1 X%f Y%f F3000   ;Move head away\n" % (park_x, park_y)
                                
                                # Cool down
                                if self.getSettingValueByKey("cool_down"):
                                    # Turn off extruder temp
                                    prepend_gcode += "M104 S0  ;Turn off extruder heat\n"
                                
                                # Wait until they're ready
                                prepend_gcode += "M117 Press Continue...\n"
                                if self.getSettingValueByKey("beep"):
                                    # Beep to let them know that we paused
                                    prepend_gcode += "M400  ;Wait for buffer to clear\n"
                                    prepend_gcode += "M300  ;Beep\n"
                                # Pause
                                if pause_method == 'm25':
                                    prepend_gcode += "M25 ; Pause\n"
                                elif pause_method == 'm0':
                                    prepend_gcode += "M0 Press to Continue...\n"
                                # Do normal pause if not changing filament (wants to pause)
                                if not self.getSettingValueByKey("change_filament"):
                                    # Lock the motors and let the user do what they need to do while paused. Wait until they're ready
                                    # Engage motors
                                    if position_absolute_mode:
                                        prepend_gcode += "G91  ;Set to relative position mode\n"
                                    prepend_gcode += "G1 X-0.1 Y-0.1 Z-0.1  ; Lock motors\n"
                                    prepend_gcode += "G1 X0.1 Y0.1 Z0.1  ; Lock motors\n"
                                    if position_absolute_mode:
                                        prepend_gcode += "G90  ;Set back to absolute position mode\n"
                                    # Wait until they're ready
                                    prepend_gcode += "M117 Press Continue...\n"
                                    if self.getSettingValueByKey("beep"):
                                        # Beep to let them know that we paused
                                        prepend_gcode += "M400  ;Wait for buffer to clear\n"
                                        prepend_gcode += "M300  ;Beep\n"
                                    # Pause
                                    if pause_method == 'm25':
                                        prepend_gcode += "M25 ; Pause\n"
                                    elif pause_method == 'm0':
                                        prepend_gcode += "M0 Press to Continue...\n"
                                # Heat back up
                                if self.getSettingValueByKey("cool_down"):
                                    # Engage motors
                                    if position_absolute_mode:
                                        prepend_gcode += "G91  ;Set to relative position mode\n"
                                    prepend_gcode += "G1 X-0.1 Y-0.1 Z-0.1  ; Lock motors\n"
                                    prepend_gcode += "G1 X0.1 Y0.1 Z0.1  ; Lock motors\n"
                                    if position_absolute_mode:
                                        prepend_gcode += "G90  ;Set back to absolute position mode\n"
                                    # Heat back up
                                    prepend_gcode += "M117 Heating extruder...\n"
                                    prepend_gcode += "M109 S%f  ;Heat extruder back up\n" % (last_e_temp)
                                    prepend_gcode += "M117 Press Continue...\n"
                                    if self.getSettingValueByKey("beep"):
                                        # Beep to let them know that it is finished heating up
                                        prepend_gcode += "M400  ;Wait for buffer to clear\n"
                                        prepend_gcode += "M300  ;Beep\n"
                                    # Pause
                                    if pause_method == 'm25':
                                        prepend_gcode += "M25 ; Pause\n"
                                    elif pause_method == 'm0':
                                        prepend_gcode += "M0 Press to Continue...\n"
                                if self.getSettingValueByKey("change_filament"):
                                    # Engage motors
                                    if position_absolute_mode:
                                        prepend_gcode += "G91  ;Set to relative position mode\n"
                                    prepend_gcode += "G1 X-0.1 Y-0.1 Z-0.1  ; Lock motors\n"
                                    prepend_gcode += "G1 X0.1 Y0.1 Z0.1  ; Lock motors\n"
                                    if position_absolute_mode:
                                        prepend_gcode += "G90  ;Set back to absolute position mode\n"
                                    # Push the filament back, and retract again. This properly primes the nozzle when changing filament.
                                    if prime_mm > 0:
                                        prepend_gcode += ";Prime nozzle\n"
                                        prepend_gcode += "G1 E%f F6000\n" % (prime_mm + 1.0)
                                        prepend_gcode += "G1 E-%f F6000\n" % (prime_mm)
                                    prepend_gcode += "M117 Press Continue...\n"
                                    if self.getSettingValueByKey("beep"):
                                        # Beep to let them know to clean up
                                        prepend_gcode += "M400  ;Wait for buffer to clear\n"
                                        prepend_gcode += "M300  ;Beep\n"
                                    # Pause
                                    if pause_method == 'm25':
                                        prepend_gcode += "M25 ; Pause\n"
                                    elif pause_method == 'm0':
                                        prepend_gcode += "M0 Press to Continue...\n"
                                    # Retraction
                                    prepend_gcode += "G1 E-%f F2400 ;Retract\n" % (retraction_mm)
                                # Move the head back
                                # X and Y first
                                prepend_gcode += "G1 X%f Y%f F3000  ;Move to next layer position\n" % (x, y)
                                # Then Z
                                prepend_gcode += "G1 Z%f F3000  ;Move to next layer Z position\n" % (current_z)
                                # Extrusion
                                prepend_gcode += "G1 E%f F2400 ;Extrude\n" % (extrusion_mm)
                                if extruder_absolute_mode:
                                    prepend_gcode += "M82  ;Set extruder back to absolute mode\n"
                                    prepend_gcode += "G92  E%f  ;Set the extrude value to the previous (before last retraction)\n" % (last_e)
                                prepend_gcode += "M117 Printing...\n"
                            prepend_gcode += ";CUSTOM Pause Done\n"
                            
                            beginning = lines[:line_index]
                            ending = lines[line_index:]
                            layer = "\n".join(beginning) + "\n" + prepend_gcode + "\n".join(ending) + "\n"
                            
                            data[data_index] = layer #Override the data of this layer with the modified data
                            
                            #We're done unless we come across another LAYER_COUNT value that signals another part
                            ready = False
                            continue
                        # Continue to the next line
                        continue
        
        # Return the data
        return data
