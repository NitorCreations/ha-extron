import unittest

from custom_components.extron.extron import is_error_response


class ExtronTestCase(unittest.TestCase):
    def test_is_error_response(self):
        self.assertTrue(is_error_response("E01"))
        self.assertTrue(is_error_response("E74\n"))
        self.assertTrue(is_error_response("E23\r\n  "))
        self.assertFalse(is_error_response("0"))


if __name__ == "__main__":
    unittest.main()
