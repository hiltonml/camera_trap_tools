# Camera Trap Time-Lapse Video Tools

This repository contains a suite of tools for managing time-lapse recordings taken by camera traps (a.k.a. trail cameras) and some sample data you can use to try out the tools.  Tools are provided for the following tasks:
- Downloading and automatic renaming of images from SD cards. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/autocopy.md)
- Compressing images to MP4 video files. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/create_video.md)
- Automatically creating a video annotation that indicates frames where species of interest are present. (This requires training a machine learning algorithm on your images.  Examples of how to do this are provided.) [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/create_annotations.md)
- Manually annotating video to indicate user-specified events, which can be tied to specific animals, if desired. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/annotator.md)
- Generating reports for analysis using the statistical software of your choice. [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/annotation_report.md)
- Generating reports on status of camera capture and processing.  [Learn more.](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/capture_report.md)

The distinguishing feature of this suite is that it can handle large amounts of data with a minimum of human interaction.  We use this software to manage 24 camera traps that are generating a total of 250,000 images (~380 GB of data) per day.

A short paper describing the tool set and some results can be found [here.](https://arxiv.org/abs/2206.05159)

# Installing the Tools

1. The tools use Python 3, which must be installed on your computer.  You can find Python installers [here.](http://python.org)
2. If you are a git user, clone this repository.  If you are not familiar with git, press the green "Code" button on this page and select "Download ZIP".  After the download completes, unzip the file to the location where you want the tools installed.
3. Open a command window and change the working directory to the tool's ```code``` folder. Run the command  ```pip install -r requirements.txt```
4. If you want to create MPEG videos from your still images, you will need to install ```ffmpeg```.  You can find installers [here.](https://www.ffmpeg.org/)
5. Test if the installation was successful by running the command ```python3 autocopy.py -c ../example_data/example.config```  After running this command, there should be a file named ```autocopy_errors.log``` in the ```example_data``` folder, containing a message indicating four images have been successfully copied.
