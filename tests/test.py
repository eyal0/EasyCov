#!/usr/bin/env python2

import unittest
import os
import filecmp
import json

from context import easycov

class BasicTests(unittest.TestCase):
  def test_parse_file(self):
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.parse_file(os.path.join(path, "pcb2gcode-lcov.info"))
    with open(os.path.join(path, "pcb2gcode-lcov.info.json")) as expected:
      self.assertEqual(result, json.loads(expected.read()))

  def test_parse_file_with_root(self):
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.parse_file(
        os.path.join(path, "one-lcov.info"),
        "/home/runner/work/pcb2gcode/pcb2gcode")
    with open(os.path.join(path, "one-lcov.info.json")) as expected:
      self.assertEqual(result, json.loads(expected.read()))


if __name__ == '__main__':
  unittest.main()
