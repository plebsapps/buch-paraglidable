# coding: utf-8
# Tests for the PHP-faithful helpers of the D2 web port (web/php_compat.py).
# Pure stdlib, runs inside the frozen Python 3.6 container:
#   python -m unittest discover -s pipeline/tests -v

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from web.php_compat import (php_filter_int, php_filter_float, ctype_xdigit,
							php_round4, php_float_str, php_substr_byte,
							php_substr2_be, php_loose_eq_int,
							latlon_to_tile_coords, clean_search_q)


class TestPhpCompat(unittest.TestCase):

	def test_filter_int(self):
		self.assertEqual(php_filter_int("128"), 128)
		self.assertEqual(php_filter_int("-7"), -7)
		self.assertIsNone(php_filter_int("12.5"))
		self.assertIsNone(php_filter_int(""))
		self.assertIsNone(php_filter_int(None))

	def test_filter_float(self):
		self.assertEqual(php_filter_float("45.9"), 45.9)
		self.assertEqual(php_filter_float("1e2"), 100.0)
		self.assertIsNone(php_filter_float("abc"))
		self.assertIsNone(php_filter_float("nan"))
		self.assertIsNone(php_filter_float(None))

	def test_ctype_xdigit(self):
		self.assertTrue(ctype_xdigit("abc123"))
		self.assertTrue(ctype_xdigit("DEADBEEF"))
		self.assertFalse(ctype_xdigit("zzz"))
		self.assertFalse(ctype_xdigit(""))

	def test_round_and_str(self):
		# ord/255 quantization like get.php: round(.., 4), precision-14 echo
		self.assertEqual(php_float_str(php_round4(241 / 255.0)), "0.9451")
		self.assertEqual(php_float_str(php_round4(0 / 255.0)), "0")
		self.assertEqual(php_float_str(php_round4(255 / 255.0)), "1")
		self.assertEqual(php_float_str(0.9727881), "0.9727881")

	def test_substr_semantics(self):
		data = bytes([10, 20, 30])
		self.assertEqual(php_substr_byte(data, 1), 20)
		self.assertEqual(php_substr_byte(data, 99), 0)    # past end -> ord('')
		self.assertEqual(php_substr_byte(data, -1), 30)   # from the end
		self.assertEqual(php_substr_byte(data, -99), 10)  # clamped to 0
		self.assertEqual(php_substr2_be(bytes([1, 2]), 0), (1 << 8) + 2)
		self.assertEqual(php_substr2_be(bytes([1]), 0), 1 << 8)  # short slice
		self.assertEqual(php_substr2_be(bytes([1, 2]), 5), 0)

	def test_loose_eq(self):
		self.assertTrue(php_loose_eq_int("3323", 3323))
		self.assertTrue(php_loose_eq_int(3323, 3323))
		self.assertFalse(php_loose_eq_int("3323", 42))
		self.assertTrue(php_loose_eq_int("junk", 0))  # PHP 7: 'junk' == 0

	def test_latlon_to_tile_coords(self):
		# The frozen snapshot pair: lat=45.9, lon=6.6 resolves to the same
		# pixel the PHP resolved (snapshot get_latlon vs. tile 66/45).
		c = latlon_to_tile_coords(45.9, 6.6)
		self.assertEqual(c["zoom"], 7)
		self.assertEqual((c["tx"], c["ty"]), (66, 45))
		self.assertTrue(0 <= c["x"] <= 255 and 0 <= c["y"] <= 255)

	def test_clean_search_q(self):
		self.assertEqual(clean_search_q("q/anne.js"), "anne")
		self.assertEqual(clean_search_q("a/b\\c,d;e'f\"g.h"), "abcdefgh")


if __name__ == "__main__":
	unittest.main()
