# Plotting Utility to Accompany capture_report.py
# Mike Hilton, Eckerd College
# 2021/07/06
#
# This R script generates a PNG image containing a heat map detailing the number 
# of images captured by each camera on each day, whether those images have been
# compressed into videos, and if an annotation file exists for that camera day.
#
# If a month is provided as the command line argument, in the format YYYY-MM,
# the name of the CSV file read as input will be capture_report_YYYY-MM.csv and
# the name of the image file generated is capture_report_YYYY-MM.png.  If no
# command line argument is provided, the input will be capture_report.csv and 
# the name of the image file is capture_report.png.
#
# The command line argument does not affect anything but the file names.

library(readr)
library(dplyr)
library(ggplot2)

# get the command line arguments
args = commandArgs(trailingOnly=TRUE)

# determine input data file name
if (length(args) == 0) {
  dataFile = "capture_report.csv"
  imageFile = "capture_report.png"
} else {
  dataFile = paste("capture_report_", args[1], ".csv", sep="")
  imageFile = paste("capture_report_", args[1], ".png", sep="")
}

# read in the camera report
camera_report <- read_csv(dataFile,
                          col_types = cols(Date = col_datetime(format = "%Y-%m-%d"),
                                           ImageCount = col_integer(),
                                           FrameCount = col_integer()))

camera_report <- camera_report %>%
  # convert Camera to factor in order to get geom_tile to show them in ascending order
  mutate(Camera=factor(Camera,levels=rev(sort(unique(Camera))))) %>%
  # combine the ImageCount and FrameCount columns using max
  mutate(Count = pmax(ImageCount, FrameCount)) %>%
  # create custom levels for the number of images
  mutate(countFactor=cut(Count,
                         breaks=c(0, 2000, 4000, 6000, 8000, 20000),
                         labels = c("0-2K", "2K-4K", "4K-6K", "6K-8K", ">8K")))
  
  
p <- ggplot(data = camera_report, mapping = aes(x=Date, y=Camera, fill=countFactor)) +
  # add border white colour of line thickness 0.25  
  geom_tile(colour="white", size=0.25) +
  # add dots for video + annotation
  geom_point(mapping = aes(shape = Video, color = Annotation)) +
  scale_shape_manual(values = c(1, 16)) +
  scale_color_manual(values = c("#000000", "#00FFFF")) +
  #remove x and y axis labels
  labs(x="", y="", title="Camera Trap Image Report")+
  # remove extra space
  scale_y_discrete(expand=c(0,0)) +
  # custom colors
  scale_fill_manual(values=c("#d53e4f","#f46d43","#fdae61","#fee08b","#e6f598","#abdda4","#ddf1da"),na.value = "grey90") +
  # theme
  theme_grey(base_size=10)+
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank())

ggsave(imageFile, plot = p)

