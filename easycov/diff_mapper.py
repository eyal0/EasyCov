#!/usr/bin/env python2
"""Parse a diff and allow mapping from source to target line numbers."""

from __future__ import division
from __future__ import print_function
import bisect
from collections import defaultdict
from unidiff import PatchSet

class DiffMapper(object):
  """DiffMapper maps from target lines to source lines."""

  def __init__(self, mapping=None):
    self._mapping = mapping or defaultdict(list)

  @staticmethod
  def _add_row_to_mapping(mapping, new_row):
    """Add a row.  If the last row can be rewritten, do that instead."""
    if not mapping:
      mapping.append(new_row)
      return
    if new_row[2] is None and mapping[-1][2] is None:
      return # There is nothing to do.
    if (new_row[2] is None) != (mapping[-1][2] is None):
      mapping.append(new_row)
      return
    if new_row[0] - mapping[-1][0] == new_row[2] - mapping[-1][2]:
      return # There is nothing to do.
    mapping.append(new_row)


  @staticmethod
  def from_filename(filename):
    """Reads diff from the filename provided.

    This fills self._mapping with a mapping for each file the represents that
    map from target filename and line number to source filename and line number.
    """
    patchset = PatchSet.from_filename(filename)
    return DiffMapper.from_patchset(patchset)

  @staticmethod
  def from_string(text):
    """Reads diff from the string provided.

    This fills self._mapping with a mapping for each file the represents that
    map from target filename and line number to source filename and line number.
    """
    patchset = PatchSet.from_string(text)
    return DiffMapper.from_patchset(patchset)

  @staticmethod
  def from_patchset(patchset):
    """Reads diff from the filename provided.

    This fills self._mapping with a mapping for each file the represents that
    map from target filename and line number to source filename and line number.
    """
    mapping = defaultdict(list)
    for patched_file in patchset:
      source_path = patched_file.source_file
      target_path = patched_file.target_file
      source_current = 0
      target_current = 0
      for hunk in patched_file:
        source_start = hunk.source_start
        target_start = hunk.target_start
        if source_start - source_current != target_start - target_current:
          raise ValueError("Malformed patch is missing a hunk, source %s:%d:%d, target %s:%d:%d." %
                           (source_path, source_start, source_current,
                            target_path, target_start, target_current))
        new_row = (target_current,
                   source_path,
                   source_current)
        DiffMapper._add_row_to_mapping(mapping[target_path], new_row)
        for line in hunk:
          if line.target_line_no is not None:
            DiffMapper._add_row_to_mapping(mapping[target_path],
                                           (line.target_line_no,
                                            source_path,
                                            line.source_line_no))
        source_current = source_start + hunk.source_length
        target_current = target_start + hunk.target_length
      new_row = (target_current,
                 source_path,
                 source_current)
      DiffMapper._add_row_to_mapping(mapping[target_path], new_row)
    return DiffMapper(mapping)

  def __getitem__(self, filename):
    def _get(mapping, line_number):
      if not mapping:
        return (filename, line_number)
      index = bisect.bisect_right([x[0] for x in mapping], line_number) - 1
      index = max(index, 0)
      entry = self._mapping[filename][index]
      # entry is (line number in filename, old filename, old linenumber)
      if entry[2] is None:
        return (entry[1], None)
      offset = line_number - entry[0]
      return (entry[1], entry[2] + offset)

    return type('', (object,), {
        '__getitem__': lambda _, line_number: _get(self._mapping[filename], line_number)
    })()

  def __repr__(self):
    return "DiffMapper(mapping=%s)" % repr(self._mapping)
