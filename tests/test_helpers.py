#!/usr/bin/env python2
"""Helpers for tests"""

from __future__ import division
import difflib
import os
import unittest

class BaseTestCase(unittest.TestCase):
  """Base class for tests that need compare_lines."""
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
