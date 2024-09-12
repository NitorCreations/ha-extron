from unittest import TestCase

from custom_components.extron.media_player import make_source_bidict


class TestSourceBidict(TestCase):
    def test_make_source_bidict(self):
        # No input names specified
        bd = make_source_bidict(4, [])
        self.assertEqual(4, len(bd.values()))
        self.assertEqual("1", bd.get(1))
        self.assertEqual("4", bd.get(4))

        # First two input names specified
        bd = make_source_bidict(4, ["foo", "bar"])
        self.assertEqual(4, len(bd.values()))
        self.assertEqual("foo", bd.get(1))
        self.assertEqual("bar", bd.get(2))
        self.assertEqual("3", bd.get(3))
        self.assertEqual("4", bd.get(4))

        # Define one more input name than there are sources
        bd = make_source_bidict(2, ["foo", "bar", "baz"])
        self.assertEqual(2, len(bd.values()))
        self.assertEqual("foo", bd.get(1))
        self.assertEqual("bar", bd.get(2))
