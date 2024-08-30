"""
Convnet Digit Recognizer Training Code
Mike Hilton, Eckerd College

This is a simple convolutional neural network for recognizing digits in
trail camera images.  The architecture is based on the Keras MNIST Digits
example found on the Keras website.
"""

import os
import random

import cv2
import keras
from keras import layers
import numpy as np
from sklearn.metrics import classification_report


### Example of how to generate digits dataset from trail camera images
# from utils.ocr.ocr import TrailCamOCR
# sourceFolder = "/media/oyen/Boyd_Hill_Data/RawImages"
# destinationFolder = "/media/oyen/Boyd_Hill_Data/DigitImages"
# o = TrailCamOCR()
# o.generateTrainingDigitImages(sourceFolder, destinationFolder, maxSamples = 500)


### Example of how to test the OCR on trail camera images
# from utils.ocr.ocr import TrailCamOCR
# imageFolder = "/media/oyen/Boyd_Hill_Data/RawImages"
# o = TrailCamOCR()
# o.testFolderOfImages(imageFolder)
# exit()

# Model / data parameters
batch_size = 128
checkpoint_filepath = "/home/mike/tortoise/camera_trap_tools/code/utils/ocr/digit_model.keras"
epochs = 8
input_shape = (65, 46, 1)
image_folder = "/media/oyen/Boyd_Hill_Data/DigitImages"
num_classes = 10


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


def load_data(folder, training_fraction=0.8):
    """
    Loads the digit image dataset and returns a randomized split into
    training and test data.

    Inputs:
        folder              string; path to folder where digit image dataset lives
        training_fraction   float; fraction of the dataset allocated to training data
    Returns:
        (training_data, training_labels), (test_data, test_labels)

    """
    files = getFilePathsInSubfolders(folder, extension='.png')
    random.shuffle(files)

    images = []
    labels = []
    for file in files:
        images.append(cv2.imread(file,cv2.IMREAD_GRAYSCALE))
        labels.append(os.path.split(file)[1][0])

    split = int(len(files) * training_fraction)
    return (np.asarray(images[:split]), np.asarray(labels[:split])), (np.asarray(images[split:]), np.asarray(labels[split:]))



# Load the data and split it between train and test sets
(x_train, y_train), (x_test, y_test) = load_data(image_folder)

# Scale images to the [0, 1] range
x_train = x_train.astype("float32") / 255
x_test = x_test.astype("float32") / 255

x_train = np.expand_dims(x_train, -1)
x_test = np.expand_dims(x_test, -1)
print("x_train shape:", x_train.shape)
print(x_train.shape[0], "train samples")
print(x_test.shape[0], "test samples")

# convert class vectors to binary class matrices
classes_test = np.asarray(list((int(i) for i in y_test)))  # save classes for report generation later
y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)

# CONVNET model
model = keras.Sequential(
    [
        keras.Input(shape=input_shape),
        layers.Conv2D(32, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Flatten(),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation="softmax"),
    ]
)
model.summary()

# train the model
model_checkpoint_callback = keras.callbacks.ModelCheckpoint(
    filepath=checkpoint_filepath,
    monitor='val_accuracy',
    mode='max',
    save_best_only=True)
model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])
history = model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs, validation_split=0.1,
                    callbacks=[model_checkpoint_callback])

### evaluate the trained model
# predict the class of each example in the test set
predY = np.argmax(model.predict(x_test), axis=1)
# show a nicely formatted classification report
print(classification_report(classes_test, predY))    
 
