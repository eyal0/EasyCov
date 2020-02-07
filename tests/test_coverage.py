#!/usr/bin/env python2
"""Test coverage.py"""

from __future__ import division
import os
import unittest

from easycov.coverage import Coverage, Hits
from .test_helpers import BaseTestCase

class CoverageTests(BaseTestCase):
  """Test Coverage class."""
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

  def test_from_lcov_with_branch(self):
    """Test Coverage.from_lcov(file, root_dir)."""
    path = os.path.dirname(os.path.realpath(__file__))
    result = Coverage.from_lcov(
        os.path.join(path, "branch-lcov.info"),
        "/home/runner/work/pcb2gcode/pcb2gcode")
    expected_file = os.path.join(path, "branch-lcov.info.json")
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

  def test_roundtrip_lcov_root_json(self):
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

  def test_coverage_bits(self):
    """Check roundtrip from Hits to bits."""
    actual = None
    expected = Coverage._bits_to_value(Coverage._value_to_bits(actual)) # pylint: disable=protected-access
    self.assertEqual(actual, expected)
    for denom in xrange(1, 10):
      for numer in xrange(denom+1):
        expected = Hits(numer, denom)
        actual = Coverage._bits_to_value(Coverage._value_to_bits(expected)) # pylint: disable=protected-access
        self.assertEqual(actual, expected)

  def test_get_ratio(self):
    """Test Coverage.get_ratio()."""
    path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(path, "coverage.xml.json"), 'r') as json_file:
      data = json_file.read()
      self.assertEqual(Coverage.from_json(data).get_ratio(), 73/86)

class HitsTests(unittest.TestCase):
  """Test Hits class."""
  def test_inequalities(self):
    """Test gt, lt, etc."""
    self.assertNotEqual(Hits(1, 2), Hits(2, 4))

    self.assertTrue(Hits(1, 2) > Hits(1, 3))
    self.assertTrue(Hits(4, 8) > Hits(1, 3))
    self.assertTrue(Hits(1, 3) < Hits(1, 2))
    self.assertTrue(Hits(1, 3) < Hits(4, 8))

    self.assertFalse(Hits(1, 2) < Hits(1, 3))
    self.assertFalse(Hits(4, 8) < Hits(1, 3))
    self.assertFalse(Hits(1, 3) > Hits(1, 2))
    self.assertFalse(Hits(1, 3) > Hits(4, 8))

    self.assertTrue(Hits(1, 2) >= Hits(1, 3))
    self.assertTrue(Hits(4, 8) >= Hits(1, 3))
    self.assertTrue(Hits(1, 3) <= Hits(1, 2))
    self.assertTrue(Hits(1, 3) <= Hits(4, 8))

    self.assertFalse(Hits(1, 2) <= Hits(1, 3))
    self.assertFalse(Hits(4, 8) <= Hits(1, 3))
    self.assertFalse(Hits(1, 3) >= Hits(1, 2))
    self.assertFalse(Hits(1, 3) >= Hits(4, 8))

    self.assertFalse(Hits(2, 4) == Hits(1, 2))
    self.assertTrue(Hits(2, 4) >= Hits(1, 2))
    self.assertTrue(Hits(2, 4) <= Hits(1, 2))
    self.assertFalse(Hits(2, 4) > Hits(1, 2))
    self.assertFalse(Hits(2, 4) < Hits(1, 2))

if __name__ == '__main__':
  unittest.main()
