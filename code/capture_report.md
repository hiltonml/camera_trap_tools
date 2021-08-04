# capture_report.py: Camera Capture Report

This program generates a CSV file detailing the number of images captured by
each camera on each day, whether those images have been compressed into videos,
and if an annotation file exists for that camera day.  The companion R script 
capture_report.R can be used to create a graphic from the CSV file.

Each record (line) of the report represents one camera day and contains the following information:
* _Camera_: Camera site and view
* _Date_
* _ImageCount_: Number of images in the default_image_folder that are associated with this camera day
* _FrameCount_: Number of frames in the video associated with this camera day
* _Video_: Boolean value indicating if a compressed video exists for this camera day
* _Annotation_: Boolean value indicating if an annotation file exists for this camera day


## Command Line Arguments
All arguments are optional; default values can be provided in a configuration file.
Short Form|Long Form|Type|Description
----------|---------|----|-----------
-c| --config|    path|      Configuration file.  If not provided, defaults to "capture_report.config" located in the same directory as this program.
-m| --month| string|   Month for which to create a report, in YYYY-MM format.  If not provided, the report is created for the entire period of time data has been recorded.

The name of the report file generated depends on whether the **--month** argument is provided. If no argument is provided, the file is named 'capture_report.csv'; 
if an argument is provided, the file is named 'capture_report_*YYYY-MM*.csv' where *YYYY-MM* is the year and month for the report.

## Configuration File Settings
If no configuration file is provided using the ```-c``` command line option, this program will read configuration settings from a file named ```capture_report.config``` An example of how each setting is used can be found in the configuration file ```production.config```

### [General_Settings]   
This section contains configuration variables used by more than one program in the Camera Trap Tools suite.   

* _default_annotation_folder_: path to root of the default folder where annotations are stored
* _default_image_folder_: path to root of default folder where images are stored
* _default_video_folder_: path to root of default folder where compressed videos are stored
* _prefix_: string prepended to image filename

### [Camera_Views]
If you supply values in this section, then the left-most digit of the camera ID is taken to specify a camera view.  
The key-value pairs in this section are a mapping from digits to camera views, in the format: 

```<digit> = <full name of view>, <single-character abbreviation of view name>```

# Companion R Script
The file 'capture_report.R' reads a CSV file produced by 'capture_report.py' and generates a visualization of the 
data in the CSV file.  The script takes an optional command line argument for the year and month of the report file in *YYYY-MM* format.  The visualization is
written to a file named either 'capture_report.png' or 'capture_report_*YYYY-MM*.png', depending on whether the optional command argument was provided.
