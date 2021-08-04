# THE DOCUMENTATION IN THIS REPOSITORY IS STILL UNDER DEVELOPMENT

# Camera Trap Time-Lapse Video Tools

This repository contains a suite of tools for managing time-lapse recordings taken by camera traps (a.k.a. trail cameras).  Tools are provided for the following tasks:
- Downloading and automatic renaming of images from SD cards. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/autocopy.md)
- Compressing images to MP4 video files. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/create_video.md)
- Automatically creating a video annotation that indicates frames where species of interest are present. (This requires training a machine learning algorithm on your images.  Examples of how to do this are provided.) [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/create_annotations.md)
- Manually annotating video to indicate user-specified events, which can be tied to specific animals, if desired. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/annotator.md)
- Generating reports for analysis using the statistical software of your choice. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/annotation_report.md)
- Generating reports on status of camera capture and processing.  [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/capture_report.md)


The distinguishing feature of this suite is that it can handle large amounts of data with a minimum of human interaction.  We use this software to manage 24 camera traps that are generating a total of 250,000 images (~380 GB of data) per day.


