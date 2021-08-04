"""
Trail Camera Object Detector
Mike Hilton, Eckerd College

The class OD_EfficientDet0 implements an object detector based on the TensorFlow
EfficientDet0 CNN object detector that has been fine-tuned to detect tortoises.
"""

import numpy as np
from object_detection.builders import model_builder
from object_detection.utils import label_map_util, config_util, visualization_utils
import tensorflow as tf


class OD_EfficientDet0:
    def __init__(self, app_config):
        # EfficientDet0 settings
        settings = app_config.app_config["EfficientDet0"]
        self.draw_boxes = bool(int(settings["draw_boxes"]))              # indicates if boxes should be drawn around detected objects
        self.label_map = settings["label_map"]                           # label map file, mapping object labels to integer indices
        self.threshold = float(settings["threshold"])                    # object detection score threshold
        self.model_checkpoint = settings["model_ckpt"]                   # TensorFlow detection model checkpoint file
        self.model_config = settings["model_config"]                     # TensorFlow detection model pipeline config file
        # initialize the detector
        self.detection_fn = self.load_model()
        self.category_index = self.load_categories()	
 
    def get_model_detection_function(self, model):
        """Create a tf.function for detection."""
        @tf.function
        def detect_fn(image):
            """Detect objects in image."""
            image, shapes = model.preprocess(image)
            prediction_dict = model.predict(image, shapes)
            detections = model.postprocess(prediction_dict, shapes)
            return detections, prediction_dict, tf.reshape(shapes, [-1])
        return detect_fn

    def load_categories(self):
        # map labels for inference decoding
        label_map = label_map_util.load_labelmap(self.label_map)
        categories = label_map_util.convert_label_map_to_categories(
            label_map,
            max_num_classes=label_map_util.get_max_label_map_index(label_map),
            use_display_name=True)
        category_index = label_map_util.create_category_index(categories)
        return category_index    

    def load_model(self):
        # loads the TensorFlow model
        configs = config_util.get_configs_from_pipeline_file(self.model_config)
        detection_model = model_builder.build(model_config=configs['model'], is_training=False)

        # restore checkpoint
        ckpt = tf.compat.v2.train.Checkpoint(model=detection_model)
        ckpt.restore(self.model_checkpoint).expect_partial()
        detection_fn = self.get_model_detection_function(detection_model) 
        return detection_fn    

    def run_inference_on_image(self, image_np, draw_detections=None):
        """
        Runs the object detector on an image.
        Inputs:
            image_np			numpy array; image to process
            draw_detections		boolean; indicates if an output image showing object detections should be created
        Returns:
            A tuple of the form (scores, boxes, classes) where
                scores is an N x 1 array of detection confidence scores
                boxes is an N x 4 array of bounding boxes for detections
                classes is an N x 1 array of class indices
        """
        input_tensor = tf.convert_to_tensor(np.expand_dims(image_np, 0), dtype=tf.float32)
        label_id_offset = 1

        # run the detector
        detections, predictions_dict, shapes = self.detection_fn(input_tensor)
        scores = detections['detection_scores'][0].numpy()
        boxes = detections['detection_boxes'][0].numpy()
        classes = (detections['detection_classes'][0].numpy() + label_id_offset).astype(int)

        # draw object bounding boxes if appropriate
        if draw_detections is None:
            draw_detections = self.draw_boxes

        if draw_detections:
            visualization_utils.visualize_boxes_and_labels_on_image_array(
                image_np,
                boxes,
                classes,
                scores,
                self.category_index,
                use_normalized_coordinates=True,
                max_boxes_to_draw=200,
                min_score_thresh=self.threshold,
                agnostic_mode=False,
            )

        # return only the results for objects with scores above the threshold
        idxs = np.nonzero(scores >= self.threshold)     

        return scores[idxs], boxes[idxs], classes[idxs]    