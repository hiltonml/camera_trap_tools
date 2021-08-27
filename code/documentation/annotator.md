# annotator.py: Video Annotation Program

This program lets you annotate videos or image sequences, marking segments of the video where specific activities are taking place.  You can also associate each activity with a specific animal or animals.  The annotations are stored in text files that are separate from video and image files.

The annotator can work with video files or image sequences.  An image sequence is a collection of images located in the same folder.  The images are ordered alphabetically by filename.

## Command Line Arguments
All arguments are optional; default values can be provided in a configuration file.
Short Form|Long Form|Type|Description
----------|---------|----|-----------
-c| --config|    path|      Configuration file.  If not provided, defaults to "annotator.config" located in the same directory as this program.

## Activities and Events
Activities come in two flavors: instantaneous and durational. Instantaneous activities occur at one instant in time, whereas durational activities have start and end times.  An "event" is either the time of an instantaneous activity, the start time of a durational activity, or the end time of a durational activity.

## Quick-Start Tutorial

![Annotator Application Window](Annotator.png)

The annotator application window has three main sets of controls: the video viewing and navigation controls; the annotation navigation controls; and the annotation editing controls.  
- The video controls should be familiar to most people and will not be discussed further.
- The annotation navigation controls consist of the timeline plot and the previous/next event buttons.  The timeline plot displays the activities that have been assigned to specific animals.  The colors of the activities match the colors in the activity buttons found in the annotation editor.  If you click on an activity in the timeline, the video will move to the start frame of the activity.  The previous/next event buttons move the video to the frame associated with the previous/next event.  You can also click on an activity in the Annotations table to navigate to the start of the activity.
- The annotation editing controls let you add or delete activities from the timeline.  The appearance of the editing controls will change depending on the annotation mode selected in the configuration file.  There are three annotation modes: 
  - _Focal species mode_, where only one set of editing controls is displayed. The figure above shows focal species mode.
  - _Focal and commensal animals mode_, where two sets of editing controls are displayed.  Each set can contain different events and animal IDs.
  ![Focal and Commensal mode](Focal_Commensal_Mode.png)  
  - _Counting mode_, which simplify marking video segments to indicate whether they contain a single animal or multiple animals.  You cannot specify which animal(s) are present.  The "Animals Present" buttons act as toggles, sometimes saving you the need to press the ```Begin``` or ```End``` buttons. 
  ![Counting Mode](Count_Mode.png)

To add an instantaneous activity to the timeline, navigate to the video frame where the activity occurs.  Press the appropriate activity button, select an item in the ID list, and press the ```Start``` button.  

To add a durational activity to the timeline, follow the directions for instantaneous activities, and then navigate to the video frame where the activity ends.  Press the ```End``` button. 

To delete an activity, you can click on the activity in timeline or the Annotations table, and then press the ```Delete``` button.

### Multi-Phase Annotating
If your project has complex annotating requirements, you might want to break the workflow into multiple phases that each have a limited number of actions or use different modes.  For example, in our tortoise project we are interested in the many different aspects of tortoise behavior - social interactions, thermoregulation activities, burrow migration, etc.  There are so many things we wanted to annotate, that it drove our annotators crazy!  To reduce the cognitive burden on the annotators, we split the annotation task into multiple phases.  The first phase uses counting mode to indicate how many tortoises are visible in the video at the same time.  The second phase uses focal species mode, where we identify the specific tortoises present and when a tortoise enters or exits a burrow.  And so on.  Each phase gets its own configuration file (discussed below).  All the annotations for a video are stored in a single text file, regardless of how many phases you use.

The ```Span``` button in the annotation editing controls was designed to work with multiphase projects that use a counting mode phase followed by phases using a different mode.  ```Span``` is a shortcut way to create a durational event. If you position the video cursor anywhere inside an activity on the "Count" timeline and select an activity button and ID, pressing ```Span``` will create an annotation that spans the range of the count activity.

## Configuration File Settings
If no configuration file is provided using the ```-c``` command line option, this program will read configuration settings from a file named ```annotator.config``` An example of how each setting is used can be found in the file ```annotator.config```.

### [General_Settings]   
This section contains configuration variables used by more than one program in the Camera Trap Tools suite.   
                          
* _default_annotation_folder_: path to root of the default folder where annotations are stored
* _default_image_folder_: path to root of default folder where the downloaded images are stored
* _detection_box_folder_: path to root of the folder storing bounding boxes of animals detected
* _default_video_folder_: path to root of default folder where compressed videos are stored
* _prefix_: string prepended to image filename

### [Annotator]
This section contains configuration variables used only by this program.

* _mode_: 0 = count mode; 1 = focal species mode; 2 = focal and commensal animals mode
* _show_detection_boxes_: 1 = show animal detection bounding boxes by default; 0 = do not show animal detection bounding boxes by default
* _training_folder_: path to folder where images are written when the ```Annotator > Save Frame For Training``` command is executed

### [Camera_Views]
If you supply values in this section, then the left-most digit of the camera ID is taken to specify a camera view.  
The key-value pairs in this section are a mapping from digits to camera views, in the format: 

```<digit> = <full name of view>, <single-character abbreviation of view name>```

### [Focal_ID]
This section is where you specify the names to be displayed in the ID list box for focal species.  The format is a key-value pair with no value:

```<name> =```

### [Focal_Activity]
This section contains the activities you want to appear in the focal species annotation editor controls.  The format for durational activities is:

```<activity name> = <color name>, paired```

and the format for instantaneous activities is:

```<activity name> = <color name>, single```

where ```<color name>``` is one of the [standard SVG color names](https://www.w3.org/TR/SVG11/types.html#ColorKeywords)

### [Commensal_ID]
This section is where you specify the names to be displayed in the ID list box for commensal animals.  The format is a key-value pair with no value:

```<name> =```

### [Focal_Activity]
This section contains the activities you want to appear in the commensal animal annotation editor controls.  The format for durational activities is:

```<activity name> = <color name>, paired```

and the format for instantaneous activities is:

```<activity name> = <color name>, single```

where ```<color name>``` is one of the [standard SVG color names](https://www.w3.org/TR/SVG11/types.html#ColorKeywords)
