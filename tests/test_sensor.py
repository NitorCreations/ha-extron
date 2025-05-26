import unittest

from custom_components.extron.sensor import parse_incoming_line_count


class TestSensors(unittest.TestCase):
    def test_parse_incoming_line_count(self):
        incoming_line_count = "2160*30.002735*67.485909*3840"

        self.assertEqual("3840 x 2160 @ 30 Hz", parse_incoming_line_count(incoming_line_count))


if __name__ == '__main__':
    unittest.main()
