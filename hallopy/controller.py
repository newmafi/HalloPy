"""Multi class incapsulation implementation.  """
import cv2
import logging
import numpy as np
from HalloPy.hallopy.icontroller import Icontroller
from hallopy import utils

# Create loggers.
frame_logger = logging.getLogger('frame_handler')
face_processor_logger = logging.getLogger('face_processor_handler')
back_ground_remover_logger = logging.getLogger('back_ground_remover_handler')
detector_logger = logging.getLogger('detector_handler')
ch = logging.StreamHandler()
# create formatter and add it to the handlers.
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add the handlers to loggers.
frame_logger.addHandler(ch)
face_processor_logger.addHandler(ch)
back_ground_remover_logger.addHandler(ch)
detector_logger.addHandler(ch)


class FrameHandler:
    """FrameHandler handel input frame from controller,

    and perform some preprocessing.
    """
    _input_frame = ...  # type: np.ndarray

    def __init__(self):
        """Init preprocessing params.  """
        self.logger = logging.getLogger('frame_handler')
        self.logger.setLevel(logging.INFO)
        self._cap_region_x_begin = 0.6
        self._cap_region_y_end = 0.6
        self._input_frame = None

    @property
    def input_frame(self):
        return self._input_frame

    @input_frame.setter
    def input_frame(self, input_frame_from_camera):
        """Setter with preprocessing.  """

        try:
            # make sure input is np.ndarray
            assert type(input_frame_from_camera).__module__ == np.__name__
        except AssertionError as error:
            self.logger.exception(error)
            return

        self._input_frame = cv2.bilateralFilter(input_frame_from_camera, 5, 50, 100)  # smoothing filter
        self._input_frame = cv2.flip(input_frame_from_camera, 1)
        self._draw_roi()

    def _draw_roi(self):
        """Function for drawing the ROI on input frame"""

        cv2.rectangle(self._input_frame, (int(self._cap_region_x_begin * self._input_frame.shape[1]) - 20, 0),
                      (self._input_frame.shape[1], int(self._cap_region_y_end * self._input_frame.shape[0]) + 20),
                      (255, 0, 0), 2)


class FaceProcessor:
    """FaceProcessor detect & cover faces in preprocessed input_frame.  """
    _preprocessed_input_frame = ...  # type: np.ndarray

    def __init__(self):
        self.logger = logging.getLogger('face_processor_handler')
        self.logger.setLevel(logging.INFO)
        self._face_detector = cv2.CascadeClassifier(
            utils.get_full_path('hallopy/config/haarcascade_frontalface_default.xml'))
        self._face_padding_x = 20
        self._face_padding_y = 60
        self._preprocessed_input_frame = None

    @property
    def face_covered_frame(self):
        """Return a face covered frame"""
        return self._preprocessed_input_frame

    @face_covered_frame.setter
    def face_covered_frame(self, input_frame_with_faces):
        """Function to draw black recs over detected faces.

        This function remove eny 'noise' and help detector detecting palm.
        :param input_frame_with_faces (np.ndarray): a frame with faces, that needed to be covered.
        """

        try:
            # make sure input is np.ndarray
            assert type(input_frame_with_faces).__module__ == np.__name__
        except AssertionError as error:
            self.logger.exception(error)
            return

        # Preparation
        self._preprocessed_input_frame = input_frame_with_faces.copy()
        gray = cv2.cvtColor(self._preprocessed_input_frame, cv2.COLOR_BGR2GRAY)

        faces = self._face_detector.detectMultiScale(gray, 1.3, 5)

        # Black rectangle over faces to remove skin noises.
        for (x, y, w, h) in faces:
            self._preprocessed_input_frame[y - self._face_padding_y:y + h + self._face_padding_y,
            x - self._face_padding_x:x + w + self._face_padding_x, :] = 0


class BackGroundRemover:
    """BackGroundRemover removes background from inputed (preprocessed and face covered) frame.  """

    def __init__(self):
        self.logger = logging.getLogger('back_ground_remover_handler')
        self._cap_region_x_begin = 0.6
        self._cap_region_y_end = 0.6
        self._threshold = 50
        self._blur_Value = 41
        self._bg_Sub_Threshold = 50
        self._learning_Rate = 0
        self._bg_model = None
        self._input_frame_with_hand = None

    @property
    def detected_frame(self):
        """Getter for getting the interest frame, with background removed.  """
        return self._input_frame_with_hand

    @detected_frame.setter
    def detected_frame(self, preprocessed_faced_covered_input_frame):
        """Function for removing background from input frame. """
        # todo: bg_model bgModel initation to controller's input_from_keyboard_thread.
        if self._bg_model is None:
            self._bg_model = cv2.createBackgroundSubtractorMOG2(0, self._bg_Sub_Threshold)

        fgmask = self._bg_model.apply(preprocessed_faced_covered_input_frame, learningRate=self._learning_Rate)
        kernel = np.ones((3, 3), np.uint8)
        fgmask = cv2.erode(fgmask, kernel, iterations=1)
        res = cv2.bitwise_and(preprocessed_faced_covered_input_frame, preprocessed_faced_covered_input_frame,
                              mask=fgmask)
        self._input_frame_with_hand = res[
                                      0:int(self._cap_region_y_end * preprocessed_faced_covered_input_frame.shape[0]),
                                      int(self._cap_region_x_begin * preprocessed_faced_covered_input_frame.shape[1]):
                                      preprocessed_faced_covered_input_frame.shape[
                                          1]]  # clip the ROI


class Detector:
    """Detector class detect hand.

    Initiated object will recieve a preprocessed frame, with detected & covered faces.
    """

    def __init__(self):
        self.logger = logging.getLogger('detector_handler')

        self._input_frame_with_hand = None
        self.detected_gray = None
        self.detected_out_put = None

        self.detected_out_put_center = None
        self.horiz_axe_offset = 60

        self.gray = None
        self.max_area_contour = None


class Controller(Icontroller):
    """Controller class holds a detector and a extractor.

    :param icontroller.Icontroller: implemented interface
    """

    def __init__(self):
        """Init a controller object.  """
        self.move_up = 0
        self.move_left = 0
        self.move_right = 0
        self.move_down = 0
        self.move_forward = 0
        self.move_backward = 0
        self.rotate_left = 0
        self.rotate_right = 0

        # Initiate inner objects
        self.frame_handler = FrameHandler()
        self.face_processor = FaceProcessor()
        self.back_ground_remover = BackGroundRemover()

    def get_up_param(self):
        """Return up parameter (int between 0..100). """
        if self.move_up <= 0:
            return 0
        return self.move_up if self.move_up <= 100 else 100

    def get_down_param(self):
        """Return down parameter (int between 0..100). """
        if self.move_down < 0:
            return 0
        return self.move_down if self.move_down <= 100 else 100

    def get_left_param(self):
        """Return left parameter (int between 0..100). """
        if self.move_left < 0:
            return 0
        return self.move_left if self.move_left <= 100 else 100

    def get_right_param(self):
        """Return right parameter (int between 0..100). """
        if self.move_right < 0:
            return 0
        return self.move_right if self.move_right <= 100 else 100

    def get_rotate_left_param(self):
        """Return rotate left parameter (int between 0..100). """
        if self.rotate_left < 0:
            return 0
        return self.rotate_left if self.rotate_left <= 100 else 100

    def get_rotate_right_param(self):
        """Return rotate right parameter (int between 0..100). """
        if self.rotate_right < 0:
            return 0
        return self.rotate_right if self.rotate_right <= 100 else 100

    def get_forward_param(self):
        """Return move forward parameter (int between 0..100). """
        if self.move_forward < 0:
            return 0
        return self.move_forward if self.move_forward <= 100 else 100

    def get_backward_param(self):
        """Return move backward parameter (int between 0..100). """
        if self.move_backward < 0:
            return 0
        return self.move_backward if self.move_backward <= 100 else 100


if __name__ == '__main__':
    test = Controller()
    print(test.get_up_param())
