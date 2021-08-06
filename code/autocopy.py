"""
Camera Trap File Copy Program
Mike Hilton, Eckerd College
2021/07/06

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

The image file names will be of the form "<prefix><CameraID><View>-<YYYYMMDD>-<HHMMSS>.<ext>", where:
    <prefix> is an optional string
    <CameraID> is the numeric ID of the camera that took the image
    <View> is the optional camera viewpoint
    <YYYYMMDD> is the date the image was acquired in year, month, day format
    <HHMMSS> is the time the image was last modified in 24-hour, minute, seconds format
    <ext> is the original source file extension, in lowercase

The file copies will be organized in the destination directory with the following structure:
    <DestinationDirectory>/<prefix><CameraID>/<Date>/<View>/<image files> 
where <Date> will have the format YYYY-MM-DD, which is the year, month, and day files were acquired.    

Command line arguments for this program are listed below.  All arguments are optional; default values 
can be provided in a configuration file.
    -c, --config    <path>      Configuration file.  If not provided, defaults to "autocopy.config" located
                                in the same directory as this program.
    -s, --source    <path>      Image source directory.  If no source path is provided on the command line
                                or the configuration file, images are copied from all SD cards found.
    -d, --dest      <path>      Image destination directory.  See description of destination directory structure
                                provided above.
    -i, --id        <string>    Camera ID.  If not provided on the command line or the configuration file, 
                                the ID will be extracted from each image's information banner.
"""

# standard Python modules
import argparse
import configparser
from datetime import datetime, timezone
import logging
import os
import pytz
import shutil

# 3rd party modules
import psutil  

# modules that are part of this package
import utils.trailcamutils as trailcamutils
                                  

class AppConfig:
    """ 
    Configuration settings for this application
    """
    def __init__(self, configFilename):
        """
        Loads settings from the app configuration file.
        """
        self.app_config = configparser.ConfigParser()         
        assert os.path.exists(configFilename), f"Confguration file not found: {configFilename}"
        self.app_config.read(configFilename)
        
        # general settings shared by multiple trail_camera_tools programs
        settings = self.app_config["General_Settings"]  
        self.images_destination = settings["default_image_folder"]          # root of destination folder 
        self.error_log_file = settings.get("error_log_file", "error.log")   # path to error log
        self.prefix = settings.get("prefix", "")                            # filename prefix string        
        self.time_zone = settings.get("time_zone", "US/Eastern")            # your time zone designator

        # settings specific to this program 
        settings = self.app_config["Autocopy"]        
        self.camera_id = settings.get("camera_id", None)                    # default camera ID
        self.camera_model = settings.get("camera_model", None)              # default camera model name
        self.copy_images = bool(int(settings.get("copy_images", 1)))        # indicates if images should be copied to destination
        self.detect_objects = bool(int(settings.get("detect_objects", 0)))  # indicates if object detector should be run on images
        self.images_source = settings.get("default_image_source", None)     # default image source folder
        self.html_report = settings.get("html_report",                      # path to HTML progress report 
            "autocopy_status.html")   
        self.sd_card_sizes = settings.get("sd_card_sizes",                  # memory sizes (in GB) of SD cards you are using
            "32, 64")
        self.skip_end = int(settings.get("skip_end", 0))                    # number of images to skip processing at the end of SD card
        self.skip_start = int(settings.get("skip_start", 0))                # number of images to skip processing at the start of SD card
        self.use_exif = bool(int(settings.get("use_exif", 0)))              # indicates if EXIF data should be used for acquisition date/time

        # camera viewpoint names
        settings = self.app_config["Camera_Views"]
        self.views = {}
        for digit in range(10):
            if str(digit) in settings:
                parts = settings[str(digit)].split(",")
                if len(parts) != 2:
                    raise Exception("Camera view is not of the form <digit> = <full name of view>, <single-character abbreviation of view name>")
                else:
                    self.views[str(digit)] = (parts[0].strip(), parts[1].strip())

        # convert the SD card sizes to numbers
        cards = self.sd_card_sizes.split(",")
        self.sd_card_sizes = []
        for card in cards:
            self.sd_card_sizes.append(float(card.strip()))



class DriveStatus:
    """
    Information about the copying progress for each SD card found on this computer.
    """
    def __init__(self, driveName, volumeName, usedSpace):
        # initialize instance variables
        self.drive_name = driveName                                         # name of drive
        self.failure_count = None                                           # number of files unsuccessfully processed
        self.file_count = None                                              # number of files on drive
        self.files = None                                                   # list of files to be processed
        self.used_space = usedSpace                                         # the percentage of space used on the drive
        self.success_count = None                                           # number of files successfully processed
        self.volume_name = volumeName                                       # name of volume             


class AutoCopy:
    def __init__(self, configFile=None, createHtml=True):
        # read the configuration file
        if configFile is None:
            configFile = self.getConfigFilename()
        self.app_config = AppConfig(configFile)

        # initialize instance variables
        self.abort = False                                                  # indicates if the autocopy process should abort
        self.arg_camera_id = None                                           # Camera ID provided on command line
        self.arg_view = None                                                # camera view provided on command line
        self.create_html = createHtml                                       # indicates if an HTML web page containing status info should be created
        self.drive_status = {}                                              # dictionary mapping drive name to status information
        self.errors = []                                                    # list of error strings
        self.object_detector = None                                         # object detection class instance
        self.ocr = None                                                     # optical character reader for image metadata        
        
        # initialization actions
        if createHtml:
            # make sure the path to HTML file exists
            p = os.path.dirname(self.app_config.html_report)
            os.makedirs(p, exist_ok=True) 
        if not self.app_config.use_exif:
            # initialize the OCR
            from utils.ocr.ocr import TrailCamOCR            
            self.ocr = TrailCamOCR() 
        if self.app_config.detect_objects:
            ### if you implement your own animal detector, you should replace these lines
            # the GenericDetector is a classification-based CNN
            from utils.genericdetector.generic_classification_detector import GenericDetector
            self.object_detector = GenericDetector(self.app_config)
            # the TortoiseDetector is an object detection-based CNN
            # from utils.tortoisedetector.tortoise_detector import TortoiseDetector
            # self.object_detector = TortoiseDetector(self.app_config)           


    def close(self):
        """
        Release any resources allocated by the program.
        """
        if self.object_detector is not None:
            self.object_detector.close()


    def currentTime(self):
        """
        Returns the current local time
        """
        utc_dt = datetime.now(timezone.utc)
        tzone = pytz.timezone(self.app_config.time_zone)
        return utc_dt.astimezone(tzone)
    

    def extractImageInfo(self, gray_img, ext):
        """
        Extract information from the text burned into the bottom of the image.
        Inputs:
            gray_img    grayscale numpy image
            ext         string; image file extension
        Outputs:
            A tuple containing (camera ID, destination path for image, filename prefix)
            Note the destination path contains the filename.
        """
        # get the information from the image
        camera, view, date, time = trailcamutils.extractImageInfo(gray_img, self.ocr, self.app_config.views)
        # create the filename and path
        view_directory = os.path.join(self.app_config.images_destination, trailcamutils.imagePathFromParts(camera, view, date))
        fname = trailcamutils.createImageFilename(camera, view, date, time, ext)
        destination_path = os.path.join(view_directory, fname)
        # create any missing folders in the path
        os.makedirs(view_directory, exist_ok=True)

        return camera, destination_path, fname


    def generate_html_report(self, noWork=False):
        """
        Generate a simple HTML web page reporting the current status of the copying process.
        Inputs:
            noWork      boolean; if True, all current drives have been processed
        """
        # boilerplate
        txt = """<!DOCTYPE html>
            <html>
            <head>
                <title>Trail Camera Autocopy Status</title>
                <meta http-equiv="refresh" content="10">
                <style>
                table, th, td {
                border: 1px solid black;
                border-collapse: collapse;
                }
                th, td {
                padding: 15px;
                }
                </style>
            </head>
            <body>"""
        txt += "<h1>Trail Camera Autocopy Status</h1>\n"
        txt +=  f"""<h3>Last update: {self.currentTime().strftime("%H:%M:%S, %m/%d/%Y")}<h3>\n"""
        if len(self.drive_status) == 0:
            txt += "<h2>No SD Cards Found</h2>"
        elif noWork:
             for _, status in self.drive_status.items():  
                txt += f"""<h3>{status.drive_name}: <progress value="1.0"></progress>100%</h3>\n"""            
        else:
            # generate table containing info on each drive 
            txt += "<table>\n<tr><th></th><th>Drive</th><th>Progress</th><th>Successful Copies</th><th>Failed Copies</th><th>SD Card Used</th><th>SD Files</th></tr>\n"
            i = 0
            for _, status in self.drive_status.items(): 
                i += 1                           
                if status.file_count is None:
                    txt += f"""<tr><td>{i}</td><td>{status.drive_name}</td><td><progress value="0"></progress>0%</td>"""
                    txt += f"""<td></td><td></td><td>{int(status.used_space)}%</td></tr>\n"""
                else:    
                    if status.file_count > 0:            
                        fraction = (status.success_count + status.failure_count) / status.file_count
                    else:
                        fraction = 0
                    pct = int(100 * fraction)
                    txt += "<tr>"
                    txt += f"<td>{i}</td>\n"
                    txt += f"<td>{status.drive_name}</td>\n"
                    txt += f"""<td><progress value="{fraction}"></progress>{pct}%</td>\n"""
                    txt += f"<td>{status.success_count:,}</td>\n"
                    txt += f"<td>{status.failure_count:,}</td>\n"
                    txt += f"<td>{int(status.used_space)}%</td>\n"
                    txt += f"<td>{status.file_count:,}</td>\n"
                    txt += "</tr>"
            txt += "</table>\n"
        # error strings, if any
        if len(self.errors) > 0:
            txt += "<h1>Recent Errors</h1>\n"
            for err in self.errors:
                txt += f"<p><pre>{err}</pre></p>\n"
        txt += "</body>"
        with open(self.app_config.html_report, "w") as f:
            f.write(txt)
 

    def getConfigFilename(self):
        """
        Creates a config filename from the main module's file name.
        """
        base, _ = os.path.splitext(__file__)
        return base + ".config"


    def getDrives(self):
        """
        Retrieves information about drives whose memory capacity is within 5% of
        the SD card capacities listed in the configuration file.

        Returns a list of tuples of the form (drive name, volume name, percent in use)
        """    
        keepers = []
        drives = psutil.disk_partitions()
        for drive in drives:
            volID = os.path.basename(drive.mountpoint)
            usage = psutil.disk_usage(drive.mountpoint)
            volSizeGB = usage.total / 1e9
            # check for any volume having a size within 5% of an SD card size
            for cardSize in self.app_config.sd_card_sizes:                    
                if (cardSize * 0.95 <= volSizeGB <= cardSize * 1.05):
                    keepers.append((drive.mountpoint, volID, usage.percent))
        return keepers


    def initializeDriveStatus(self):
        """
        Creates the drive status dictionary.
        Returns the list of drives.
        """
        # create the drive status data structure
        self.drive_status = {}
        drives = self.getDrives()
        for drive, volume_name, freeSpace in drives:
            self.drive_status[drive] = DriveStatus(drive, volume_name, freeSpace)
        return drives


    def main(self, source):
        """ 
        Process the images in the source folder.
        """
        # ensure the folder for log file exists
        os.makedirs(os.path.dirname(self.app_config.error_log_file), exist_ok=True)

        # configure the error logger
        logging.basicConfig(filename=self.app_config.error_log_file, 
            filemode="a", level=logging.DEBUG, format='%(asctime)s - %(message)s')    

        try:        
            # get the DriveStatus object associated with this source
            if source in self.drive_status:
                status = self.drive_status[source]
            else:
                status = DriveStatus(source, source, 0)

            # initialize status variables
            status.success_count = 0
            status.failure_count = 0
            status.files = trailcamutils.getFilePathsInSubfolders(source)
            status.file_count = len(status.files)

            # iterate over all the files in the input directory
            the_camera = self.processFolder(status)

            logging.info(f"Camera {the_camera}: failed copies = {status.failure_count}, successful copies = {status.success_count}")
            if self.abort:
                logging.info("Autocopy aborted")   

        except Exception as e:
            logging.error(f"Error in main: {e}")


    def processFolder(self, status):
        """
        Process all of the images in the provided status object.
        Returns the camera ID for images in the folder.
        """
        if self.create_html:
            self.generate_html_report()

        the_camera = app.app_config.camera_id

        file_count = len(status.files)
        for i in range(file_count):
            try:                
                if self.abort:
                    return the_camera

                # skip processing the first skip_start files and the last skip_end files, to avoid 
                # copying images that may have the field workers in them
                if (self.app_config.skip_start <= i < file_count - self.app_config.skip_end):
                    file = status.files[i]
                    _, ext = os.path.splitext(file)

                    if self.app_config.use_exif:
                        # get EXIF date & time for image
                        exif_data = trailcamutils.getExifData(file)
                        if exif_data is not None:
                            exif_date, exif_time = exif_data
                            # create a file name for the image
                            filename = trailcamutils.createImageFilename(self.app_config.prefix, the_camera, exif_date, exif_time, ext, self.app_config.views)

                    else: 
                        # extract the image metadata from the image using OCR                             
                        the_camera, view, ocr_date, ocr_time = self.ocr.extractImageInfo(file, self.app_config.views, self.app_config.camera_model)
                        # create a file name for the image
                        filename = trailcamutils.createImageFilename(self.app_config.prefix, the_camera, ocr_date, ocr_time, ext, self.app_config.views)

                    # create a pathname for the destination image
                    destination_path = os.path.join(
                        self.app_config.images_destination,
                        trailcamutils.imagePathFromFilename(filename, self.app_config.prefix, self.app_config.views)
                    )
                    # ensure the destination path exists
                    os.makedirs(destination_path, exist_ok=True)
                    destination_path = os.path.join(destination_path, filename)                    

                    # copy the image to the destination folder
                    if self.app_config.copy_images:
                        shutil.copyfile(file, destination_path)

                    # run the object detector
                    if self.app_config.detect_objects:
                        self.object_detector.detect(destination_path, view)

                            
            except Exception as e:
                logging.warning(f"Camera {the_camera} - Copy failed on {file}: {e}")
                self.errors.append(f"{e}")
                status.failure_count += 1
            else:
                status.success_count += 1

            if self.create_html and (status.failure_count + status.success_count) % 100 == 0:
                self.generate_html_report()                                        

        if self.create_html:
            self.generate_html_report()

        return the_camera


    def processSdCards(self):
        """
        Processes all of the SD cards found on the system
        """
        drives = self.initializeDriveStatus()

        # force an update of the web page
        self.generate_html_report()

        # process each drive
        for drive, volume_name, _ in drives:
            if self.abort:
                return
            self.main(drive)


def parseCommandLine():
    """
    Parse the command line arguments.
    Returns a dictionary containing the arguments.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", required=False, default=None, help="path to configuration file")
    ap.add_argument("-d", "--dest", required=False, default=None, help="path to destination main directory")
    ap.add_argument("-i", "--id", required=False, default=None, help="Camera ID; if not provided, an attempt will be made to read it from image using OCR")
    ap.add_argument("-s", "--source", required=False, default=None, help="path to image source directory")
    args = vars(ap.parse_args())
    return args



if __name__ == "__main__":
    args = parseCommandLine()
    app = AutoCopy(args["config"])

    # assign any command line arguments to app configuration variables
    if args["dest"] is not None:
        app.app_config.images_destination = args["dest"]
    if args["id"] is not None:
        app.app_config.camera_id = args["id"]    
    if args["source"] is not None:
        app.app_config.images_source = args["source"]

    # process the files      
    if app.app_config.images_source is not None:
        app.main(app.app_config.images_source)
    else:
        app.processSdCards()  

    # release any resources allocated
    app.close()     
