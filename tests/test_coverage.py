#!/usr/bin/env python2
"""Test coverage.py"""

import difflib
import os
import unittest

from tests.context import easycov

class CoverageTests(unittest.TestCase):
  """Test Coverage class."""
  def compare_lines(self, actual_lines, expected_lines, filename):
    """Helper for comparing lines.

    Outputs a unified diff.
    """
    self.assertEqual(actual_lines,
                     expected_lines,
                     "\n\n" + "\n".join(
                         difflib.unified_diff(
                             expected_lines,
                             actual_lines,
                             os.path.relpath(filename),
                             os.path.relpath(filename),
                             lineterm="")))

  def test_from_lcov(self):
    """Test Coverage.from_lcov(file)."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.coverage.Coverage.from_lcov(os.path.join(path, "pcb2gcode-lcov.info"))
    expected_file = os.path.join(path, "pcb2gcode-lcov.info.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = result.to_json(indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_from_lcov_with_root(self):
    """Test Coverage.from_lcov(file, root_dir)."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.coverage.Coverage.from_lcov(
        os.path.join(path, "one-lcov.info"),
        "/home/runner/work/pcb2gcode/pcb2gcode")
    expected_file = os.path.join(path, "one-lcov.info.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = result.to_json(indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_from_xml(self):
    """Test Coverage.from_xml(file, root_dir)."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.coverage.Coverage.from_xml(os.path.join(path, "coverage.xml"), "/foo")
    expected_file = os.path.join(path, "coverage.xml.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = result.to_json(indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_roundtrip_lcov(self):
    """Test roundtrip with lcov and binary."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.coverage.Coverage.from_lcov(os.path.join(path, "pcb2gcode-lcov.info"))
    roundtrip = easycov.coverage.Coverage.from_binary(result.to_binary())
    self.assertEqual(roundtrip, result)

  def test_roundtrip_lcov_with_root(self):
    """Test roundtrip with lcov and root_dir and binary."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.coverage.Coverage.from_lcov(
        os.path.join(path, "one-lcov.info"),
        "/home/runner/work/pcb2gcode/pcb2gcode")
    roundtrip = easycov.coverage.Coverage.from_binary(result.to_binary())
    self.assertEqual(roundtrip, result)

  def test_roundtrip_xml(self):
    """Test roundtrip with xml and root_dir and binary."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = easycov.coverage.Coverage.from_xml(os.path.join(path, "coverage.xml"), "/foo")
    roundtrip = easycov.coverage.Coverage.from_binary(result.to_binary())
    self.assertEqual(roundtrip, result)

  def test_roundtrip_lcov_json(self):
    """Test roundtrip with lcov and json."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "pcb2gcode-lcov.info.json"), 'r') as json_file:
      data = json_file.read()
      roundtrip = easycov.coverage.Coverage.from_json(data).to_json(indent=2, sort_keys=True)
      self.compare_lines(roundtrip.splitlines(), data.splitlines(),
                         os.path.join(path, "pcb2gcode-lcov.info.json"))

  def test_roundtrip_lcov_with_root_json(self):
    """Test roundtrip with lcov and root_dir and json."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "one-lcov.info.json"), 'r') as json_file:
      data = json_file.read()
      roundtrip = easycov.coverage.Coverage.from_json(data).to_json(indent=2, sort_keys=True)
      self.compare_lines(roundtrip.splitlines(), data.splitlines(),
                         os.path.join(path, "pcb2gcode-lcov.info.json"))

  def test_roundtrip_xml_json(self):
    """Test roundtrip with xml and root_dir and json."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "coverage.xml.json"), 'r') as json_file:
      data = json_file.read()
      roundtrip = easycov.coverage.Coverage.from_json(data).to_json(indent=2, sort_keys=True)
      self.compare_lines(roundtrip.splitlines(), data.splitlines(),
                         os.path.join(path, "pcb2gcode-lcov.info.json"))


if __name__ == '__main__':
  unittest.main()
