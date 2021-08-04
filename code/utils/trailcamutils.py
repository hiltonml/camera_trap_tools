"""
Utility functions used by the various trail camera applications.
Mike Hilton, Eckerd College
"""

from datetime import datetime
import glob
import os
import shutil



def copyImages(sourceFolder, destFolder, burrowList, dayList):
    """
    Copies the raw image files for the specified burrows and days.
    Input:
        sourceFolder        string; base folder for raw images
        destFolder          string; base folder to copy images to
        burrowList          list of strings; list of burrow IDs for images to copy
        dayList             list of strings; list of days to copy, in YYYY-MM-DD format
    """
    for burrow in burrowList:
        for day in dayList:
            source = os.path.join(sourceFolder, burrow, day)
            if os.path.exists(source):
                dest = os.path.join(destFolder, burrow)
                os.makedirs(dest, exist_ok=True)                
                shutil.copytree(source, os.path.join(dest, day))


def copyVideos(sourceFolder, destFolder, burrowList, dayList):
    """
    Copies the video files for the specified burrows and days.
    Input:
        sourceFolder        string; base folder for source videos
        destFolder          string; base folder to copy videos to
        burrowList          list of strings; list of burrow IDs for videos to copy
        dayList             list of strings; list of days to copy, in YYYY-MM-DD format
    """
    for burrow in burrowList:
        for day in dayList:
            parts = day.split('-')
            midPath = os.path.join(burrow, f"{burrow}-{parts[0]}", f"{burrow}-{parts[0]}-{parts[1]}")
            files = glob.glob(f"{sourceFolder}/{midPath}/{burrow}-{day.replace('-', '')}-*")
            for f in files:
                destPath = os.path.join(destFolder, midPath)
                os.makedirs(destPath, exist_ok=True)  
                destFile = os.path.join(destPath, os.path.basename(f))
                shutil.copyfile(f, destFile)


def createAnnotationFilename(site_ID, date):
    """
    Returns the filename for the specified annotation file.
    """
    return site_ID + "-" + date + ".annotations"


def createDatetime(date, time):
    """
    Returns a datetime specifier built from the date and time.
    """
    return date.replace("-", "") + "-" + time.replace(":", "")  


def createImageFilename(prefix, camera_ID, date, time, extension, views=None):
    """
    Returns an image filename built from the supplied parts.
    """
    # If views are provided, map the first digit of camera_ID to its abbreviated view name
    if (views is not None) and (len(views) > 0) and (camera_ID[0] in views):
        camera = camera_ID[1:] + views[camera_ID[0]][1]
    else:
        camera = camera_ID
    # make sure the extension starts with a period
    if extension[0] == '.':
        ext = extension
    else:
        ext = "." + extension  
    # build the filename         
    return prefix + camera + "-" + createDatetime(date, time) + ext   


def createVideoFilename(site_ID, view, date, extension="mp4"):
    """
    Returns a video filename built from the supplied parts.
    """
    return videoFilenameFromParts(site_ID, date, view, extension)
        

def datetimeFromImageFilename(filename, prefix, views):
    """
    Extracts the datetime field from a trail camera image filename.
    """
    _, _, _, date, time = splitImageFilename(filename, prefix, views)
    return createDatetime(date, time)


def dumpAnnotations(annotationFolder, dumpFilename):
    """
    Appends all annotation files in the annotationFolder into a single file
    with the name dumpFilename.
    """
    files = getFilenamesInFolder(annotationFolder, ".annotations")
    with open(dumpFilename, "w") as dumpFile:
        for filename in files:
            burrow_id, date = splitAnnotationFilename(filename)
            with open(os.path.join(annotationFolder, filename), "r") as f:
                for line in f:
                    dumpFile.write(f"{burrow_id},{date},{line}")



def getExifData(filename):
    """
    If the specified image file has exif data, return the date and time the image was
    taken.
    Input:
        filename        string; name of image file
    Returns:
        If the image has exif data, this function returns a tuple of the form (date, time);
        otherwise, it returns None
    """
    from exif import Image    
    with open(filename, 'rb') as image_file:
        exif_image = Image(image_file)   
        if exif_image.has_exif:
            parts = exif_image.datetime.split(' ')
            exif_date = parts[0].replace(":", "-")
            exif_time = parts[1].replace(":", "")
            return exif_date, exif_time
        else:
            return None
            

def getFilenamesInFolder(folder, extension='.jpg'):
    """
    Returns a sorted list of the names of files in the specified folder.
    """
    answer = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_file():
                # make sure the file has the proper extension
                _, ext = os.path.splitext(entry.name) 
                ext = ext.lower()                        
                if ext == extension:                        
                    answer.append(entry.name) 
    answer.sort()
    return answer


def getFilePathsInSubfolders(folder, extension='.jpg'):
    """
    Returns a sorted list of the absolute paths of files in all children of the specified folder.
    """
    extension = extension.lower()
    answer = []
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.is_file():
                # make sure the file has the proper extension
                _, ext = os.path.splitext(entry.name) 
                ext = ext.lower()                        
                if ext == extension:                        
                    answer.append(entry.path) 
            else:
                # process subfolder recursively
                answer.extend(getFilePathsInSubfolders(entry.path, extension))
    answer.sort()
    return answer


def getSubfolders(parent, leaves=False, includePath=True):
    """
    Returns a sorted list of the folders in the specified folder.
    Inputs:
        parent          string; parent folder
        leaves          boolean; indicates if leaves of the entire subfolder tree should be returned
    """
    def helper(p, lyst):
        with os.scandir(p) as entries:
            for entry in entries:
                if entry.is_dir():  
                    if includePath:                    
                        lyst.append(entry.path) 
                    else:
                        lyst.append(entry.name)
                    if leaves:
                        helper(entry.path, lyst)

    answer = []
    helper(parent, answer)
    answer.sort()
    return answer    


def imagePathFromFilename(filename, prefix, views):
    """
    Returns the path to the folder where the specified image should be stored.
    This path is relative to the raw image folder.
    """
    _, camera_ID, abbrev, date, _ = splitImageFilename(filename, prefix, views)
    if abbrev is None:
        # no view matched the first digit in the camera serial number
        return os.path.join(prefix + camera_ID, date)
    else:
        # find the full view name associated with the abbreviated view
        fullView = None
        for key, val in views.items():
            if val[1] == abbrev:
                fullView = val[0]
                break
        return os.path.join(prefix + camera_ID, date, fullView)


def imagePathFromParts(site_ID, abbrevView, date, views):
    """
    Returns the path to the folder where the specified images should be stored.
    This path is relative to the raw image folder.
    """
    # find the full view name associated with the abbreviated view
    fullView = None
    for key, val in views.items():
        if val[1] == abbrevView:
            fullView = val[0]
            break    
    return os.path.join(site_ID, date, fullView)


def parseDateTime(tc_date, tc_time):
    """
    Returns a Python datetime object from a trail camera file date and time.
    """
    year = int(tc_date[0:4])
    month = int(tc_date[5:7])
    day = int(tc_date[8:10])
    hour = int(tc_time[0:2])
    minute = int(tc_time[3:5])
    second = int(tc_time[6:8])
    return datetime(year, month, day, hour, minute, second)


def parseSerialNumber(serial_number, views={}):
    """
    Parse the camera serial number, to extract the cameraID and view information.
    Inputs:
        serial_number    string; serial number from a trail camera image
        views            dictionary mapping digits to (full view name, abbreviated view name)
    Returns:
        A tuple of the form (camera ID, abbreviated view, full view name)
    """
    cameraID = serial_number
    digit = serial_number[0]

    if digit in views:
        full = views[digit][0]
        abbrev = views[digit][1]
    else:
        full = None
        abbrev = None
    
    return cameraID, abbrev, full


def splitAnnotationFilename(filename):
    """
    Splits a trail cam annotation filename into its constituent parts.
    Input:
        filename        string; filename in the format "<siteID>-<YYYY>-<MM>-<DD>.annotations"
    Returns:
        A tuple of the form (site ID, date)
    """
    filename = os.path.basename(filename)
    parts = os.path.splitext(filename)[0].split("-")
    site_ID = parts[0] 
    date = parts[1] + "-" + parts[2] + "-" + parts[3]
    return (site_ID, date)


def splitImageFilename(filename, prefix, views):
    """
    Splits a trail cam image filename into its constituent parts.
    Input:
        filename        string; filename in the format "<BurrowID><'T' or 'F'>-<YYYYMMDD>-<HHMMSS>.<ext>"
        prefix          string; prefix string at front of filename
        views           {char: (string, char)}; dictionary mapping digits to views
    Returns:
        A tuple of the form (camera, camera ID, view abbreviation, date, time)
    """
    parts = os.path.basename(filename).split("-")
    camera = parts[0][len(prefix):]

    # determine if the last character of the camera name is a view abbreviation
    abrevs = [abbrev for name, abbrev in views.values()]
    if camera[-1] in abrevs:
        view = camera[-1]
        camera_ID = camera[:-1]
        camera = parts[0][len(prefix):-1]
    else:
        view = None
        camera_ID = camera
        camera = parts[0]

    date = parts[1][:4] + "-" + parts[1][4:6] + "-" + parts[1][6:]
    time = parts[2][:2] + ":" + parts[2][2:4] + ":" + parts[2][4:6]

    return (camera, camera_ID, view, date, time)


def splitVideoFilename(filename, prefix, views):
    """
    Splits a trail cam video filename into its constituent parts.
    Input:
        filename        string; filename in the format "<prefix><siteID>-<date>-<view>.<ext>"
        prefix          string; prefix string at front of filename
        views           {char: (string, char)}; dictionary mapping digits to views        
    Returns:
        A tuple of the form (site_ID, view_abbreviation, date)
    """
    # split the filename into pieces
    filename = os.path.basename(filename)
    parts = os.path.splitext(filename)[0].split("-")
    site_ID = parts[0][len(prefix):]
    date = parts[1][0:4] + "-" + parts[1][4:6] + "-" + parts[1][6:]
    viewName = parts[2]

    # get the view abbreviation associated with viewName
    view = None
    for full, abbrev in views.values():
        if full.lower() == viewName.lower():
            view = abbrev
            break

    return (site_ID, view, date)


def videoFilenameFromParts(site_ID, date, view, extension):
    """
    Returns the filename of the specified video file.
    """
    return site_ID + "-" + date.replace("-","") + "-" + view + "." + extension


def videoPathFromParts(site_ID, date):
    """
    Returns the path to the folder where the specified videos should be stored.
    This path is relative to the video folder.
    """
    year = date[0:4]
    year_month = date[0:7]
    return os.path.join(site_ID, f"{site_ID}-{year}", f"{site_ID}-{year_month}")


def copy_videos_in_file(filenames, sourceDir, destDir):
    """
    Copies videos from one folder to another.
    Inputs:
        filenames       string; path to a text file containing prefix names videos to copy, in the format <siteID>-<date>
        sourceDir       string; root folder of the source folder tree
        destDir         string; root folder of the destination folder tree
    """
    # read in the file prefixes
    files = set()
    with open(filenames, "r") as f:
        for line in f:
            files.add(line.strip())
    files = list(files)
    files.sort()

    # process files
    for file in files:
        siteID, _, date = splitVideoFilename(file + "top.mp4", "", {})
        p = videoPathFromParts(siteID, date)
        f = os.path.join(sourceDir, p, (file + "*"))
        for name in glob.glob(f):
            print(name)
            fname = os.path.basename(name)
            destPath = os.path.join(destDir, p)
            os.makedirs(destPath, exist_ok=True)
            destName = os.path.join(destPath, fname)
            shutil.copyfile(name, destName)
        