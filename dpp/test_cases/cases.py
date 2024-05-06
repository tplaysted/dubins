from math import pi


class TestCase:
    """ Provide some test cases for a 10x10 map. """

    def __init__(self):

        self.start_pos = [4.6, 2.4, 0]
        self.end_pos = [1.6, 8, -pi/2]

        self.start_pos2 = [4, 4, 0]
        self.end_pos2 = [4, 8, 1.2*pi]

        self.obs = [
            [2, 3, 6, 0.1],
            [2, 3, 0.1, 1.5],
            [4.3, 0, 0.1, 1.8],
            [6.5, 1.5, 0.1, 1.5],
            [0, 6, 3.5, 0.1],
            [5, 6, 5, 0.1]
        ]

class MRNTestCase:
    """ Provide some test cases for the MRN 4x5 map. """

    def __init__(self):

        self.start_pos = [1, 2, 0]
        self.end_pos = [4.7, 2.5, -pi/2]

        self.start_pos2 = [0.55, 2, 0]
        self.end_pos2 = [4, 3.7, 0]

        self.obs = [
            [0.55, 0.55, 1.6, 0.04],
            [0.55, 0.55, 0.04, 1.1],
            [0.55, 2.35, 0.04, 1.1],
            [0.55, 3.45, 1.6, 0.04],
            [2.85, 0.55, 1.6, 0.04],
            [4.45, 0.55, 0.04, 1.1],
            [4.45, 2.35, 0.04, 1.1],
            [2.85, 3.45, 1.6, 0.04],

            [0.9, 0.9, 1.25, 0.75],
            [0.9, 2.35, 1.25, 0.75],
            [2.85, 0.9, 1.25, 0.75],
            [2.85, 2.35, 1.25, 0.75],
        ]