#!/usr/bin/env python2
"""Test coverage.py"""

import difflib
import os
import unittest

from tests.context import easycov # pylint: disable=unused-import
from easycov.coverage import Coverage

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
    result = Coverage.from_lcov(os.path.join(path, "pcb2gcode-lcov.info"))
    expected_file = os.path.join(path, "pcb2gcode-lcov.info.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = result.to_json(indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_from_lcov_with_root(self):
    """Test Coverage.from_lcov(file, root_dir)."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = Coverage.from_lcov(
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
    result = Coverage.from_xml(os.path.join(path, "coverage.xml"), "/foo")
    expected_file = os.path.join(path, "coverage.xml.json")
    with open(expected_file) as expected:
      expected_lines = expected.read().splitlines() # No newlines
      actual_lines = result.to_json(indent=2, sort_keys=True).splitlines()
      self.compare_lines(actual_lines, expected_lines, expected_file)

  def test_roundtrip_lcov(self):
    """Test roundtrip with lcov and binary."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = Coverage.from_lcov(os.path.join(path, "pcb2gcode-lcov.info"))
    roundtrip = Coverage.from_binary(result.to_binary())
    self.assertEqual(roundtrip, result)

  def test_roundtrip_lcov_with_root(self):
    """Test roundtrip with lcov and root_dir and binary."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = Coverage.from_lcov(
        os.path.join(path, "one-lcov.info"),
        "/home/runner/work/pcb2gcode/pcb2gcode")
    roundtrip = Coverage.from_binary(result.to_binary())
    self.assertEqual(roundtrip, result)

  def test_roundtrip_xml(self):
    """Test roundtrip with xml and root_dir and binary."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = Coverage.from_xml(os.path.join(path, "coverage.xml"), "/foo")
    roundtrip = Coverage.from_binary(result.to_binary())
    self.assertEqual(roundtrip, result)

  def test_roundtrip_binary(self):
    """Test roundtrip with binary, from and then to."""
    path = os.path.dirname(os.path.realpath(__file__))
    binary_filename = os.path.join(path, "coverage.bin")
    result = Coverage.from_binary_filename(binary_filename)
    roundtrip = result.to_binary()
    with open(binary_filename, 'rb') as binary_file:
      self.assertEqual(roundtrip, binary_file.read())

  def test_roundtrip_lcov_json(self):
    """Test roundtrip with lcov and json."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "pcb2gcode-lcov.info.json"), 'r') as json_file:
      data = json_file.read()
      roundtrip = Coverage.from_json(data).to_json(indent=2, sort_keys=True)
      self.compare_lines(roundtrip.splitlines(), data.splitlines(),
                         os.path.join(path, "pcb2gcode-lcov.info.json"))

  def test_roundtrip_lcov_with_root_json(self):
    """Test roundtrip with lcov and root_dir and json."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "one-lcov.info.json"), 'r') as json_file:
      data = json_file.read()
      roundtrip = Coverage.from_json(data).to_json(indent=2, sort_keys=True)
      self.compare_lines(roundtrip.splitlines(), data.splitlines(),
                         os.path.join(path, "pcb2gcode-lcov.info.json"))

  def test_roundtrip_xml_json(self):
    """Test roundtrip with xml and root_dir and json."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "coverage.xml.json"), 'r') as json_file:
      data = json_file.read()
      roundtrip = Coverage.from_json(data).to_json(indent=2, sort_keys=True)
      self.compare_lines(roundtrip.splitlines(), data.splitlines(),
                         os.path.join(path, "pcb2gcode-lcov.info.json"))

  def test_coverage_iadd(self):
    """Test __iadd__ of Coverage."""
    cov1 = Coverage(version="1.0", coverage={
        "a.py": {
            0: 1
            }})
    cov2 = Coverage(version="1.0", coverage={
        "a.py": {
            1: 0.5
            }})
    cov1 += cov2
    self.assertEqual(cov1, Coverage(version="1.0", coverage={
        "a.py": {
            0: 1,
            1: 0.5
        }}))

if __name__ == '__main__':
  unittest.main()
