# create_video.py: Create Compressed Videos

This program creates a video for each view present in the source images, for
each day found.  A time-aligned side-by-side video is also created that combines
two views, if both views are available for the same day.  The open-source
program ```ffmpeg``` is used to create the videos; it must be installed on your
computer.

The source images are expected to be organized in the folder structure created
by the ```autocopy.py``` program.  The folder structure is scanned and the videos are
created for each day, except in the following situations:
- If a video already exists, it is not recreated unless the ```--force``` option is used.
- Videos are not created for the final day of images for a camera.  The reason for this is the 
    assumption that more images taken on the "current" final day will be downloaded
    the next time the camera SD card is swapped.  We want to include those new images
    in the day's video, so creation of video is delayed until a future date.
    
The video files will be organized in the video directory with the following structure:
    ```<VideoDirectory>/<prefix><CameraID>/<prefix><CameraID>-<YYYY>/<prefix><CameraID>-<YYYY>-<MM>``` 
where _YYYY_ and _MM_ are the year and month the source material was acquired.  The video files
themselves will have a name of the form ```<prefix><CameraID>-<YYYYMMDD>-<view>.mp4```

## Command Line Arguments 
All arguments are optional; default values can be provided in a configuration file.

Short Form|Long Form|Value|Description
----------|---------|----|-----------
-c| --config|    path|      Configuration file.  If not provided, defaults to "create_video.config" located in the same directory as this program.
-s| --source|    path|      Image source directory.  This path must be either a folder containing sites or a day folder.
-d| --dest|      path|      Video destination directory.  
-f| --force|                | Force creation of video, even if one of the same name exists.


## Configuration File Settings
If no configuration file is provided using the ```-c``` command line option, this program will read configuration settings from a file named 
```create_video.config``` An example of how each setting is used can be found in the configuration file ```production.config```

### [General_Settings]   
This section contains configuration variables used by more than one program in the Camera Trap Tools suite.  

* _default_image_folder_: path to root of default folder where images are stored
* _default_video_folder_: path to root of default folder where compressed videos are stored
* _detection_box_folder_: path to root of the folder storing bounding boxes of animals detected
* _error_log_file_: path to error logging file
* _prefix_: string prepended to image filename

[Create_Video]
This section contains configuration variables only used by the create_video.py program.

* _compose_scale_: image scaling factor applied to each view in side-by-side composite video
* _composite_views_: full name of the two views to be composited into a side-by-side video
* _create_composite_: 1 = create a composite video; 0 = do not create a composite video
* _force_: 1 = force the creation of video files, even if one of the same name already exists; 0 = do not create a video file if one of the same name exists
* _image_extension_: file extension of source images
* _max_interval_: maximum time interval (in seconds) of leeway allowed when time-aligning composite image frames; if no image exists for a time smaller than that interval, substitue an empty, black image
* _recompress_composite_: recompress the composite videos immediately after their creation using FFMPEG for maximum compression

### [Camera_Views]
If you supply values in this section, then the left-most digit of the camera ID is taken to specify a camera view.  
The key-value pairs in this section are a mapping from digits to camera views, in the format: 

```<digit> = <full name of view>, <single-character abbreviation of view name>```
