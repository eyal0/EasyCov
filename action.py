#!/usr/bin/env python2
"""Run the script to process the coverage."""

from __future__ import print_function
import json
import os
import subprocess
import shlex
import tempfile

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
      raise
    else:
      return exc.returncode
  return 0

def main():
  """Run the action."""
  github_event_path = os.getenv('GITHUB_EVENT_PATH')
  github_event_name = os.getenv('GITHUB_EVENT_NAME')
  home = os.getenv('HOME')
  try:
    os.makedirs(os.path.join(home, ".local/bin"))
  except OSError:
    pass # Ignore if the dir already exists.
  os.environ['PATH'] = os.path.join(home, '.local/bin') + ":" + os.getenv('PATH')
  tmp_dir = tempfile.mkdtemp()
  github_token = os.getenv('INPUT_GITHUB_TOKEN')
  with open(github_event_path, 'r') as event_file:
    github_event = json.loads(event_file.read())
  if github_event_name == 'push':
    push_dir = os.path.join(tmp_dir, "push")
    os.makedirs(push_dir)
    ssh_url = github_event['repository']['ssh_url']
    ssh_url = "x-access-token:" + github_token + ssh_url[4:]
    execute("git clone --depth=1 --branch=%s --no-tags %s %s" %
            (github_event.after, ssh_url, push_dir))
    execute("pip install --user coverage")
    execute("pip install --user wheel")
    execute("pip install --user .")
    execute("hash -r")
    os.chdir(push_dir)
    execute("coverage erase")
    execute("coverage run -m unittest discover")
    execute("coverage xml")
    execute("sudo apt-get install gzip")
    coverage_bin = os.path.join(tmp_dir, "coverage.bin")
    execute("easycov convert --xml coverage.xml > %s" % (coverage_bin))
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
