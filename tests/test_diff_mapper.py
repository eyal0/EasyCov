#!/usr/bin/env python2
"""Test diff_mapper.py"""

from __future__ import division
import os
import unittest
import json

from easycov.diff_mapper import DiffMapper
from .test_helpers import BaseTestCase

class DiffMapperTests(BaseTestCase):
  """Test DiffMapper class."""
  def test_simple(self):
    """Test DiffMapper with a simple input diff."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = DiffMapper.from_filename(os.path.join(path, "simple.diff"))
    expected_file = os.path.join(path, "simple.diff.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = json.dumps(result.get_mapping(), indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)
    self.assertEqual(result["action.py"][300], ("action.py", 293))
    self.assertEqual(result["action.py"][302], ("action.py", None))
    self.assertEqual(result["fake_file"][302], ("fake_file", 302))

  def test_simple_from_string(self):
    """Test DiffMapper with a simple input diff as a string."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "simple.diff")) as diff_string:
      result = DiffMapper.from_string(diff_string.read())
    expected_file = os.path.join(path, "simple.diff.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = json.dumps(result.get_mapping(), indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)
    self.assertEqual(result["action.py"][300], ("action.py", 293))
    self.assertEqual(result["action.py"][302], ("action.py", None))
    self.assertEqual(result["fake_file"][302], ("fake_file", 302))

  def test_new_file(self):
    """Test DiffMapper with a simple input diff."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = DiffMapper.from_filename(os.path.join(path, "new_file.diff"))
    expected_file = os.path.join(path, "new_file.diff.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = json.dumps(result.get_mapping(), indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_broken(self):
    """Test DiffMapper with a malformed patch."""
    path = os.path.dirname(os.path.realpath(__file__))
    with self.assertRaises(ValueError):
      DiffMapper.from_filename(os.path.join(path, "broken.diff"))


if __name__ == '__main__':
  unittest.main()
