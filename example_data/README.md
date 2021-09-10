# Example Data 

This folder contains a small amount of data that can be used to demonstrate how the camera trap tools work:
- ```SD_Card_Images```: A set of raw camera trap images that can be used as a source folder for the ```autocopy.py``` program. 
- ```Video```: An example of the composite side-by-side time-lapse video created by the ```create_video.py``` program.  You can view this video with a media player, or you can load it into the ```annotator.py``` program.
- ```Annotations```: A video annotation file that accompanies the composite video in the ```Video``` folder.  The annotations can be viewed and edited using the ```annotation.py``` program.
- ```example.config```: A configuration file for use with all of the camera trap tool programs that sets the tools folder paths to use the example data.  When you run a tool from the ```code``` directory, you should use the command line option ```-c ../example_data/example.config```.

If you try running the ```create_video.py``` program on this example data, you should use the ```-f``` option to force the creation of videos:  ```python create_video.py -f -c ../example_data/example.config```.  See the [documentation for create_video.py](https://github.com/hiltonml/camera_trap_tools/blob/main/code/documentation/create_video.md) for an explaination of the force option.
