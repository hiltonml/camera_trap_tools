# annotation_report.py: Annotation Reporting Tool

This program combines the contents of all video annotation files and dumps
them to a single CSV file suitable for analyzing with the statistical software
of your choice.  Each record (line) of the report represents one annotation and contains the following information:
* _site_: Camera site
* _file_: The name of the annotation file this record came from
* _activity_: The name of the activity or event associated with this annotation
* _kind_: Kind of animal associated with this annotation, either 'focal' or 'commensal'
* _individual_: ID of the animal associated with this annotation
* _startTime_: Time the activity began
* _endTime_: Time the activity ended
* _user_: Name of the user who created the annotation

## Command Line Arguments

All arguments are optional; default values can be provided in a configuration file.

Short Form|Long Form|Type|Description
----------|---------|----|-----------
-c| --config|    path|      Configuration file.  If not provided, defaults to "annotation_report.config" located in the same directory as this program.
-o| --out|       path|      Path to output report file.  If not provided, the report is printed to stdout.

## Configuration File Settings
If no configuration file is provided using the ```-c``` command line option, this program will read configuration settings from a file named 
```annotation_report.config``` An example of how each setting is used can be found in the configuration file ```production.config```

### [General_Settings]   
This section contains configuration variables used by more than one program in the Camera Trap Tools suite.   

* _default_annotation_folder_: path to root of the default folder where annotations are stored
