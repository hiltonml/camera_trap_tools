# autocopy.py: SD Card Automatic Download, Rename, and Optionally Run Animal Detector

This program copies files from a source location (typically SD cards used in a trail camera)
to a destination directory, renaming the files so they include image metadata in the 
new file names.  Metadata includes:
- Image Capture Time, which can be extracted from image EXIF data or from an information banner
  burned into each image by the camera.
- Camera ID, extracted from the image's information banner or provided on the command line.  
  The first digit of the Camera ID can optionally be translated into a string specifying the 
  camera's view by providing a substitution table in the application configuration file.

An HTML file displaying the download progress is generated every after every 100 images processed.
The path to this file is set in the configuration file.  You can open this file in a browser
to monitor the program's progress.

The image file names will be of the form ```<prefix><CameraID><View>-<YYYYMMDD>-<HHMMSS>.<ext>``` where:
 -   ```<prefix>``` is an optional string
 -   ```<CameraID>``` is the numeric ID of the camera that took the image
 -   ```<View>``` is the optional camera viewpoint
 -   ```<YYYYMMDD>``` is the date the image was acquired in year, month, day format
 -   ```<HHMMSS>``` is the time the image was last modified in 24-hour, minute, seconds format
 -   ```<ext>``` is the original source file extension, in lowercase

The file copies will be organized in the destination directory with the following structure:
    ```<DestinationDirectory>/<prefix><CameraID>/<Date>/<View>/<image files>``` 
where ```<Date>``` will have the format YYYY-MM-DD, which is the year, month, and day files were acquired.    

## Command Line Arguments
All arguments are optional; default values can be provided in a configuration file.
Short Form|Long Form|Type|Description
----------|---------|----|-----------
-c| --config|    path|      Configuration file.  If not provided, defaults to "autocopy.config" located in the same directory as this program.
-s| --source|    path|      Image source directory.  If no source path is provided on the command line or the configuration file, images are copied from all SD cards found.
-d| --dest|      path|      Image destination directory.  See description of destination directory structure provided above.
-i| --id|        string|    Camera ID.  If not provided on the command line or the configuration file, the ID will be extracted from each image's information banner.

## Configuration File Settings
If no configuration file is provided using the ```-c``` command line option, this program will read configuration settings from a file named ```autocopy.config``` An example of how each setting is used can be found in the configuration file ```production.config```

### [General_Settings]   
This section contains configuration variables used by more than one program in the Camera Trap Tools suite.   
                          
* _default_annotation_folder_: path to root of the default folder where annotations are stored
* _default_image_folder_: path to root of default folder where the downloaded images are stored
* _detection_box_folder_: path to root of the folder storing bounding boxes of animals detected
* _detection_log_file_: path to file indicating the number of animals detected in each image file
* _error_log_file_: path to error logging file
* _prefix_: string prepended to image filename
* _time_zone_: your time zone designator

### [Autocopy]
This section contains configuration variables used only by the Autocopy program.

* _camera_id_: Unique four digit number assigned to camera.  The default behavior of this program is to extract the camera ID from the serial number embedded in the information banner by many cameras. If your camera does not create an information banner, or you have not created an OCR module for your camera, you should override the default value by setting the camera_id configuration (or use the ```--id``` command line option).
* _camera_model_: name of the camera camera_model
* _copy_images_: 1 = copy images to destination, 0 = do not copy images
* _default_image_source_: If you are copying images from a folder instead of an SD card, this is the path to folder containing images to copy
* _detect_objects_: 1 = run animal detector on images, 0 = do not run detector
* _html_report_: path to HTML report indicating copy status
* _sd_card_sizes_: comma-separated values indicating memory sizes (in GB) of SD cards you are using
* _skip_end_: Number of images to skip processing at the end of SD card.  The purpose of this capability is to avoid including images of field workers who are swapping SD cards.
* _skip_start_: Number of images to skip processing at the start of SD card. The purpose of this capability is to avoid including images of field workers who are swapping SD cards.
* _use_exif_: 1 means use EXIF data for acquisition date/time; 0 means use OCR

### [Camera_Views]
If you supply values in this section, then the left-most digit of the camera ID is taken to specify a camera view.  
The key-value pairs in this section are a mapping from digits to camera views, in the format: 

```<digit> = <full name of view>, <single-character abbreviation of view name>```

### [Animal_Detector]
If you enable animal detection by setting the configuration variable ```detect_objects=1```, the configuration variables in this section are used.

* _max_nms_overlap_: maximum fraction of bounding box overlap allowed before non-maxima suppression routine prunes smaller box 
* _supported_views_: comma separated list of abbreviated names for views the detector should be run on


## OCR Capability
Many trail cameras include the ability to burn an information banner into the images they capture. This banner typically contains metadata such as image aquisition date and time, camera serial number, and temperature.  This program includes the ability to extract some image metadata from the information banner using optical character recognition (OCR).  The OCR module used by this program is based on the k-Nearest Neighbors algorithm, which is a machine learning technique that must be trained for each specific camera + image resolution combination.  For more information on how to train the OCR, see [this document](https://github.com/hiltonml/camera_trap_tools/edit/main/code/utils/ocr/README.md).

If you do not wish to train the OCR for your images, you can tell the program to get the acquisition date/time from EXIF metadata by setting the configuration variable ```use_exif=1``` and providing the camera serial number using either the ```--id``` command line option or by setting the configuration variable ```camera_ID```.
