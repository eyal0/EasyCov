#!/usr/bin/env python2
"""Run the script to process the coverage."""

from __future__ import print_function
import json
import os
import subprocess
import shlex
from inspect import currentframe, getframeinfo

def execute(cmd, check=True):
  """Run cmd, printing the command as it is run.

  Returns the result.  If check is True, raise an exception on errors.
  """
  print("[command]" + cmd)
  try:
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    print(output)
  except subprocess.CalledProcessError as exc:
    print(exc.output)
    if check:
      frameinfo = getframeinfo(currentframe())
      print("::error file=%s,line=%d::Didn't work" % (frameinfo.filename, frameinfo.lineno))
      raise
    else:
      return exc.returncode
  return 0

def main():
  """Run the action."""
  github_event_path = os.getenv('GITHUB_EVENT_PATH')
  github_event_name = os.getenv('GITHUB_EVENT_NAME')
  github_token = os.getenv('INPUT_GITHUB-TOKEN')
  with open(github_event_path, 'r') as event_file:
    github_event = json.loads(event_file.read())
  if github_event_name == 'push':
    push_dir = "/tmp/push"
    ssh_url = github_event['repository']['ssh_url']
    ssh_url = "http://x-access-token:" + github_token + ssh_url[3:]
    execute("git clone --depth=1 --branch=%s %s %s" %
            (github_event['after'], ssh_url, push_dir))
    coverage_bin = "/tmp/coverage.bin"
    xml_coverage = os.getenv('INPUT_XML_COVERAGE')
    if xml_coverage:
      xml_coverage = "--xml " + xml_coverage
    execute("easycov convert %s > %s" % (xml_coverage, coverage_bin))
    execute("gzip -n %s" % (coverage_bin))
    coverage_mismatch = execute("diff -q /tmp/coverage.bin.gz coverage.bin.gz", check=False)
    if coverage_mismatch:
      execute("cp -f /tmp/coverage.bin.gz coverage.bin.gz")
      execute("git add coverage.bin.gz")
      execute('git config --global user.email "58579435+EasyCov-bot@users.noreply.github.com"')
      execute('git config --global user.name "EasyCov Bot"')
      execute('git commit -a -m "Automated update of coverage.bin.gz"')
      execute('git push')

if __name__ == '__main__':
  main()
