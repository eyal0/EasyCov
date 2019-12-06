#!/usr/bin/env python2

import unittest
import os
import filecmp
import json
import difflib

from context import easycov

class BasicTests(unittest.TestCase):
  def compare_lines(self, actual_lines, expected_lines, filename):
    self.assertEqual(actual_lines,
                     expected_lines,
                     "\n\n" + "\n".join(
                         difflib.unified_diff(
                             expected_lines,
                             actual_lines,
                             os.path.relpath(filename),
                             os.path.relpath(filename),
                             lineterm="")))

  def test_lcov_to_json(self):
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.lcov_to_json(os.path.join(path, "pcb2gcode-lcov.info"))
    expected_file = os.path.join(path, "pcb2gcode-lcov.info.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = json.dumps(result, indent=2).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_lcov_to_json_with_root(self):
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.lcov_to_json(
        os.path.join(path, "one-lcov.info"),
        "/home/runner/work/pcb2gcode/pcb2gcode")
    expected_file = os.path.join(path, "one-lcov.info.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = json.dumps(result, indent=2).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_xml_to_json(self):
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.xml_to_json(os.path.join(path, "coverage.xml"))
    expected_file = os.path.join(path, "coverage.xml.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = json.dumps(result, indent=2).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

if __name__ == '__main__':
  unittest.main()
