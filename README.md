# Fountain script add-on for Blender

## About

This add-on allows Blender to use [Fountain](https://fountain.io/) to describe a storyboard or a screenplay if you prefer. 

![](https://github.com/philippe-lavoie/blender-fountain-addon/blob/master/Screenshot.png)

## Motivation

Storyboarding is hard. Inside Blender, we can use grease pencil to help draw the animation. However, a script must start
from somewhere and that's where a good fountain script can help you out. It's a simple markup language that allows
you to quickly show actions and dialogues for a screen play scene. Something like

```
EXT. BRICK'S PATIO - DAY

A gorgeous day.  The sun is shining.  But BRICK BRADDOCK, retired police detective, is sitting quietly, contemplating -- something.

The SCREEN DOOR slides open and DICK STEEL, his former partner and fellow retiree, emerges with two cold beers.

STEEL
Beer's ready!

BRICK
Are they cold?
```

In turn, this simple text can be used to generate a PDF. The later requires an application. You can browse the [Fountain apps](https://fountain.io/apps) page for a list of those. Personally, I find that [CinemaVision Fountain Editor](http://cinemavision.com/ftneditor) does a very good job, is full featured and it's free. 

In the source, there is a fountain script and the resulting PDF.

Once you're happy with the script, use this plugin and start to add the grease pencil elements to get your scene to come to life. The source contains an example blend file with a really bad storyboard in grease pencil. I'm not exaggerating, it's bad... Still, if you import the script with the add-on and do play (make sure to click on show information) you'll quickly see the value of mixing fountain scripts and Blender.

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
+ Enable the 'show scene information' to view onscreen information about the scene inside the 3D viewport.
+ Add greasepencil or other elements to complete your story board

## Disclaimer

It's my first add-on for Blender, please let me know how to improve it. 

