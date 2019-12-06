#!/usr/bin/env python2

import lcovparse
import os

def parse_file(filename, root_dir=None):
  with open(filename, 'r') as f:
    json_cov = lcovparse.lcovparse(f.read())
    if root_dir:
      for f in json_cov:
        if 'file' in f:
          try:
            new_path = os.path.relpath(f['file'], root_dir)
            if not new_path.startswith('..'):
              f['file'] = new_path
          except ValueError:
            pass
    return json_cov
