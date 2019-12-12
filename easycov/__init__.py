#!/usr/bin/env python2
"""Check coverage and compare against another version."""

from __future__ import division
from __future__ import print_function
import argparse
import sys
from easycov.coverage import Coverage

def _get_args():
  parser = argparse.ArgumentParser(
      description='Process coverage.')
  subparsers = parser.add_subparsers(
      help='sub-command help',
      dest='subcommand')

  # create the parser for the "convert" command
  convert = subparsers.add_parser(
      'convert',
      help='Convert generated coverage to internal format.')
  convert.add_argument(
      '--lcov', metavar='LCOV_FILE',
      type=argparse.FileType('r'), nargs='+',
      action='append', default=[],
      help='lcov file(s)')
  convert.add_argument(
      '--xml', metavar='XML_FILE',
      type=argparse.FileType('r'), nargs='+',
      action='append', default=[],
      help='python xml file(s)')
  convert.add_argument(
      '--output,-o', nargs=1, metavar='OUTPUT_FILE',
      type=argparse.FileType('w'), default=sys.stdout,
      help='output file')
  return parser.parse_args()

if __name__ == '__main__':
  ARGS = _get_args()
  if ARGS.subcommand == 'convert':
    total_coverage = Coverage()
    for lcovs in ARGS.lcov:
      for lcov in lcovs:
        total_coverage += Coverage.from_lcov_file(lcov)
    for xmls in ARGS.xml:
      for xml in xmls:
        total_coverage += Coverage.from_xml_file(xml)
    print(total_coverage.to_binary())
