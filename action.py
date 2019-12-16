#!/usr/bin/env python2
"""Run the script to process the coverage."""

from __future__ import print_function
import json
import os
import subprocess
import shlex
from inspect import getframeinfo, stack

def maybe_print(text, level):
  """Print a string only if the verbosity is high enough."""
  verbosity = int(os.getenv('INPUT_VERBOSITY'))
  if level <= verbosity:
    print(text)

def execute(cmd, check=True):
  """Run cmd, printing the command as it is run.

  Returns the result.  If check is True, raise an exception on errors.
  """
  maybe_print("[command]" + cmd, 2)
  try:
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    maybe_print(output, 3)
  except subprocess.CalledProcessError as exc:
    maybe_print(exc.output, 3)
    if check:
      caller = getframeinfo(stack()[1][0])
      filename = caller.filename.replace("/root/EasyCov", "")
      maybe_print("::error file=%s,line=%d::%s" % (filename, caller.lineno, str(exc)), 1)
      raise
    else:
      return exc.returncode
  return output

def git_clone_sha(sha, repo_url, github_token, target_dir):
  """Clone a single commit into the target_dir."""
  clone_url = repo_url.replace('https://', 'https://x-access-token:' + github_token + "@")
  execute("git init %s" % (target_dir))
  execute("git -C %s remote add origin %s" % (target_dir, clone_url))
  execute("git -C %s fetch --depth 1 origin %s" % (target_dir, sha))
  execute("git -C %s checkout FETCH_HEAD" % (target_dir))
  execute("git -C %s log -1" % (target_dir))

def translate_docker_path(path):
  """Translate docker volumes to host path.

  A path in docker may represent a different path on the host machine.
  Translate a path inside docker to a path on the host.
  """
  with open("/proc/self/mountinfo", 'r') as mountinfo:
    for mount in mountinfo:
      host_dir, docker_dir = mount.split(" ")[3:5]
      if path.startswith(docker_dir):
        path = os.path.abspath(os.path.join(host_dir, path[len(docker_dir):]))
  return path

def do_push(github_token, github_event):
  """Process push events."""
  maybe_print("[command]Detected Push Event.", 1)
  push_dir = "/tmp/push"
  clone_url = github_event['repository']['clone_url']
  maybe_print("[command]Cloning branch.", 1)
  git_clone_sha(github_event['after'], clone_url, github_token, push_dir)
  coverage_bin = "/tmp/coverage.bin"
  xml_coverage = os.getenv('INPUT_XML-COVERAGE')
  if xml_coverage:
    xml_coverage = "--xml " + xml_coverage
  else:
    xml_coverage = ""
  lcov_coverage = os.getenv('INPUT_LCOV-COVERAGE')
  if lcov_coverage:
    lcov_coverage = "--lcov " + lcov_coverage
  else:
    lcov_coverage = ""
  maybe_print("[command]Collecting coverage.", 1)

  root_dir = os.getenv('INPUT_ROOT-DIR')
  if root_dir:
    root_dir = os.path.join(os.getenv('GITHUB_WORKSPACE'), root_dir)
    root_dir = os.path.abspath(root_dir)
    root_dir = translate_docker_path(root_dir)
    root_dir = "--root_dir " + root_dir

  with open(coverage_bin, 'wb') as coverage_file:
    coverage_file.write(execute("easycov %s"
                                % (" ".join((xml_coverage, lcov_coverage, root_dir)))))
  execute("gzip -n %s" % (coverage_bin))
  coverage_mismatch = execute("diff -q /tmp/coverage.bin.gz coverage.bin.gz", check=False)
  if coverage_mismatch:
    maybe_print("[command]Coverage is changed.", 1)
    git_cmd = "git -C %s" % (push_dir)
    execute("cp -f %s.gz %s" % (coverage_bin, os.path.join(push_dir, "coverage.bin.gz")))
    execute(git_cmd + ' config --global user.email ' +
            '"58579435+EasyCov-bot@users.noreply.github.com"')
    execute(git_cmd + ' config --global user.name "EasyCov Bot"')
    upstream_branch = github_event['ref'].replace('refs/heads/', '')
    execute(git_cmd + ' checkout -b %s' % (upstream_branch))
    execute(git_cmd + " add /tmp/push/coverage.bin.gz")
    execute(git_cmd + ' commit -m "Automated update of coverage.bin.gz"')
    execute(git_cmd + ' push origin HEAD:%s' % (upstream_branch))
  else:
    maybe_print("[command]Coverage is unchanged.", 1)

def main():
  """Run the action."""
  github_event_path = os.getenv('GITHUB_EVENT_PATH')
  github_event_name = os.getenv('GITHUB_EVENT_NAME')
  github_token = os.getenv('INPUT_GITHUB-TOKEN')
  with open(github_event_path, 'r') as event_file:
    github_event = json.loads(event_file.read())
  if github_event_name == 'push':
    do_push(github_token, github_event)

if __name__ == '__main__':
  main()
