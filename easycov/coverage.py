#!/usr/bin/env python2
"""All the utilities needed for parsing coverage."""

from __future__ import division
from __future__ import print_function
import os
import xml.etree.ElementTree as ET
import re
from collections import defaultdict
from fractions import (Fraction, gcd)
import json
import math
import itertools
import lcovparse
import pkg_resources

def _relative_filename(filename, root_dir):
  if not root_dir:
    return filename
  new_path = os.path.relpath(filename, root_dir)
  if not new_path.startswith('..'):
    return new_path
  return filename

class Coverage(object):
  """Coverage represents a coverage report of many files."""

  def __init__(self, coverage=None, version=None):
    self._coverage = coverage or defaultdict(lambda: defaultdict(Fraction))
    self._version = version or pkg_resources.require("EasyCov")[0].version

  @staticmethod
  def from_lcov(filename, root_dir=None):
    """Reads coverage from the filename provided.

    If root_dir is provided, all paths that are below that directory have the
    root_dir prefix removed from them
    """
    with open(filename, 'r') as current_file:
      json_cov = lcovparse.lcovparse(current_file.read())
    coverage = defaultdict(lambda: defaultdict(Fraction))
    for current_file in json_cov:
      for line in current_file['lines']:
        filename = _relative_filename(current_file['file'], root_dir)
        coverage[filename][int(line['line'])] = max(
            coverage[filename][int(line['line'])],
            min(int(line['hit']), 0))
    return Coverage(coverage)

  @staticmethod
  def from_xml(filename, root_dir=None):
    tree = ET.parse(filename)
    root = tree.getroot()
    source_dir = ''
    for source in root.iterfind('./sources/source'):
      source_dir = source.text

    result = Coverage()
    for c in root.iterfind('./packages/package/classes/class'):
      filename = os.path.join(source_dir, c.get('filename'))
      filename = _relative_filename(filename, root_dir)
      for line in c.iterfind('./lines/line'):
        if line.get('branch', 'false') == 'true':
          # This is a branch line
          condition_coverage = line.get('condition-coverage')
          m = re.match(r'\d+%\s+\((\d+)/(\d+)\)', condition_coverage)
          result._coverage[filename][int(line.get('number'))] = max(
              result._coverage[filename][int(line.get('number'))],
              Fraction(int(m.group(1)), int(m.group(2))))
        else:
          result._coverage[filename][int(line.get('number'))] = max(
              result._coverage[filename][int(line.get('number'))],
              int(line.get('hits', 0)))
    return result

  def to_json(self, *args, **kwargs):
    """Returns the coverage as a json string."""
    result = {"version": self._version,
              "coverage": self._coverage}
    return json.dumps(result, default=lambda x: float(x), *args, **kwargs)

  @staticmethod
  def from_json(json_string):
    json_in = json.loads(json_string)
    result = Coverage()
    result._version = json_in['version']
    result._coverage = defaultdict(lambda: defaultdict(Fraction), json_in['coverage'])
    for filename in result._coverage:
      # Don't use iterkeys because we are modifying the dictionary.
      for line_number in result._coverage[filename].keys():
        result._coverage[filename][int(line_number)] = result._coverage[filename].pop(line_number)
    return result

  @staticmethod
  def _value_to_bits(v):
    """Convert a value to a byte that represents that value between 0 and 1.

    Return value 0 means that v was None.  1 is 0, 2 is 1, 3 is 1/2, 4 is 1/3, 5
    is 2/3, etc.
    """
    if v == None:
      return 0
    bits = 1
    best_bits = 0
    best_value = 0
    for d in xrange(256):
      for n in xrange(d+1):
        if gcd(n, d) != 1:
          continue
        current = Fraction(n, d)
        if float(v) == float(current):
          return bits
        if abs(v - current) < abs(v - best_value):
          best_bits = bits
          best_value = current
        bits += 1
        if bits >= 256:
          # This is already too big to fit in a byte so return the best so far.
          return best_bits

  @staticmethod
  def _bits_to_value(v):
    """Convert a byte to a value between 0 and 1.

    v should be between 0 and 255 inclusive.  0 means None.  Input 1 is 0, 2 is
    1, 3 is 1/2, 4 is 1/3, 5 is 2/3, etc.
    """
    if v == 0:
      return None
    current = 1
    for d in itertools.count():
      for n in xrange(d+1):
        if gcd(n, d) != 1:
          continue
        if current == v:
          return Fraction(n, d)
        current += 1

  def to_binary(self):
    """Returns the coverage in a much-compressed string format.

    First the version as a string followed by a 0 byte.
    Then for each file:
      filename in ascii followed by a null
      number_of_lines in the filename as a string followed by a null
      bits_per_line as a single byte, never more than 255
      Then for each line from 0 to number_of_lines-1:
        The hit value from 0 to 1 encoded into the right number of bits.
    """
    result = ""
    result += self._version + "\0"
    max_hit = 0
    for filename in sorted(self._coverage.keys()):
      result += filename + "\0"
      number_of_lines = max(self._coverage[filename].iterkeys())+1
      result += str(number_of_lines) + "\0"
      #hits is the bit-encoded value of the fraction.
      hits = [self._value_to_bits(self._coverage[filename].get(line_number, None))
              for line_number in xrange(number_of_lines)]
      bits_per_line = int(math.ceil(math.log(max(hits)+1, 2)))
      result += chr(bits_per_line)
      hit_bits = ""
      for hit in hits:
        new_val = bin(hit)[2:]
        new_val = ('0' * (bits_per_line - len(new_val))) + new_val
        hit_bits += new_val
      if len(hit_bits) % 8 != 0:
        hit_bits += '0' * (8 - len(hit_bits) % 8)
      for i in xrange(0, len(hit_bits), 8):
        result += unichr(int(hit_bits[i:i+8], 2))
    return result

  @staticmethod
  def from_binary(bin_coverage):
    """Reads the coverage from the binary format described in to_binary."""
    pos = 0
    result = Coverage()
    result._version = ""
    while bin_coverage[pos] != '\0':
      result._version += bin_coverage[pos]
      pos += 1
    pos += 1
    while pos < len(bin_coverage):
      filename = ""
      while bin_coverage[pos] != '\0':
        filename += bin_coverage[pos]
        pos += 1
      pos += 1
      number_of_lines = ""
      while bin_coverage[pos] != '\0':
        number_of_lines += bin_coverage[pos]
        pos += 1
      pos += 1
      number_of_lines = int(number_of_lines)
      bits_per_line = ord(bin_coverage[pos])
      pos += 1
      total_bits = number_of_lines * bits_per_line
      total_bytes = (total_bits + 7) // 8
      hit_bytes = bin_coverage[pos:pos+total_bytes]
      pos += total_bytes
      hit_bits = (bin(ord(b))[2:] for b in hit_bytes)
      hit_bits = "".join('0'*(8-len(b)) + b for b in hit_bits)
      hits = {}
      for line_number, hit in enumerate(re.findall(("."*bits_per_line), hit_bits)):
        hit_fraction = Coverage._bits_to_value(int(hit, 2))
        if hit_fraction != None:
          hits[line_number] = hit_fraction
      result._coverage[filename] = hits
    return result

  def __eq__(self, other):
    if not isinstance(other, Coverage):
      return False
    if self._version != other._version:
      return False
    if sorted(self._coverage.keys()) != sorted(other._coverage.keys()):
      return False
    for filename in self._coverage.iterkeys():
      if sorted(self._coverage[filename].keys()) != sorted(other._coverage[filename].keys()):
        return False
      for line_number in self._coverage[filename].iterkeys():
        if self._coverage[filename][line_number] != other._coverage[filename][line_number]:
          return False
    return True

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    return self.to_json(indent=2, sort_keys=True)
