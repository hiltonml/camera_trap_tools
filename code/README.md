# Camera Trap Tools 

This folder contains the source code for the camera trap tools.  The ```documentation``` folder contains information about each of the tools.

To install the Python dependencies for this project, use the command  ```pip install -r requirements.txt```.

## Recommended Workflow

Most of the input parameters for the tools are provided in configuration files (see the documentation for each tool for more details).  I recommend creating a single configuration file containing the parameters for all the tools and to use the ```-c configuration_file_path``` command line option with each tool.  An example of such a configuration file is provided in ```production.config```.

The tools are typically run in the following order:
1. ```autocopy.py``` is used to download the images from SD cards and (optionally) run the animal detector on the image.
2. If the animal detector is used, run ```create_annotations.py``` to create draft video segmentations indicating when the focal species is present.  After running, manually delete the detection log file.
3. Assemble the downloaded images into video files by running ```create_video.py```
4. Use the ```annotator.py``` tool to review and edit the video segmentations. Depending on the needs of your project, you may need to run the annotator multiple times for each video, using a different configuration file each time.  See the annotator documentation for an explanation.

The report generation tools, ```capture_report.py``` and ```annotation_report.py``` are run on an as-needed basis.
