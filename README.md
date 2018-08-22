# Fountain script add-on

## About

This add-on allows Blender to use [Fountain](https://fountain.io/) to describe the storyboard or screenplay if you prefer.

## Installation

Do the usual install from disk by specifying that you want to install from disk. You can grab the release from [GitHub](https://github.com/philippe-lavoie/blender-fountain-addon/releases).

- In File / User Preferences, select add-ons
- Click on "Install Add-on from file"
- Save user settings
- The addon is inside the Animation tab of the toolbar


## Features

This animation add-on allows you to:
- Import a fountain script
    - This adds markers to elements inside the script like
        - Section headers
        - Scene headers
        - Transitions
        - Dialogue
        - Actions
- View the fountain elements on the View3D
    - Click on 'Show Scene Information' to enable this
- Click on a fountain marker to 
    - quickly jump in the timeline
    - move the cursor to the appropriate line in the script
- Clear all markers
- Update the fountain script
    - This adds notes that identify the frame and duration of each element.
- Clean Script
    - This removes the notes to have a cleaner version of the script. Useful when exporting the text.
- Print markers
    - prints the time and the marker's content. Useful for youtube (I guess)
- Sync markers
    - after you move the markers around make sure that
    fountain is aware of the changes.

## Usage

+ In the text editor, open or write a fountain script.
+ In the fountain add-on under the animation tab, select the script
+ Click import
+ Notice that markers are added to the timeline
    - Default duration is 0.5 seconds per word and 1 second per action phrase.
+ Click on a scene element
    - Notice the timeline moves
    - Notice the text cursor is moved
+ Enable the 'show scene information' to view onscreen information about the scene.
+ Add greasepencil or other elements to complete your story board



