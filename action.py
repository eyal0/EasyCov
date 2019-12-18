#!/usr/bin/env python2
"""Run the script to process the coverage."""

from __future__ import print_function
import json
import os
import subprocess
import shlex
from inspect import getframeinfo, stack
from easycov.coverage import Coverage

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
    if output:
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

def git_clone(repo_url, github_token, target_dir):
  """Clone a repo into the target_dir."""
  clone_url = repo_url.replace('https://', 'https://x-access-token:' + github_token + "@")
  execute("git init %s" % (target_dir))
  execute("git -C %s remote add origin %s" % (target_dir, clone_url))

def git_fetch(sha, target_dir, depth=1):
  """Checkout a single commit into the target_dir."""
  execute("git -C %s fetch --depth %d origin %s" % (target_dir, depth, sha))
  execute("git -C %s log -1 %s" % (target_dir, sha))

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

def collect_coverage():
  """Get all the coverage specified in the environment variables."""
  total_coverage = Coverage()
  root_dir = os.getenv('INPUT_ROOT-DIR')
  if root_dir:
    root_dir = os.path.join(os.getenv('GITHUB_WORKSPACE'), root_dir)
    root_dir = os.path.abspath(root_dir)
    root_dir = translate_docker_path(root_dir)
  maybe_print("[command]Collecting coverage.", 1)
  xml_coverage = os.getenv('INPUT_XML-COVERAGE')
  if xml_coverage:
    for xml_filename in xml_coverage.split(" "):
      total_coverage += Coverage.from_xml(xml_filename, root_dir)
  lcov_coverage = os.getenv('INPUT_LCOV-COVERAGE')
  if lcov_coverage:
    for lcov_filename in lcov_coverage.split(" "):
      total_coverage += Coverage.from_lcov(lcov_filename, root_dir)
  maybe_print(total_coverage.to_json(indent=2), 3)
  return total_coverage

def do_push(github_token, github_event):
  """Process push events."""
  maybe_print("[command]Detected Push Event.", 1)
  push_dir = "/tmp/push"
  clone_url = github_event['repository']['clone_url']
  maybe_print("[command]Cloning branch.", 1)
  git_clone(clone_url, github_token, push_dir)
  push_sha = github_event['after']
  git_fetch(push_sha, push_dir)
  coverage_bin = "/tmp/coverage.bin"
  with open(coverage_bin, 'wb') as coverage_file:
    coverage_file.write(collect_coverage().to_binary())
  execute("gzip -n %s" % (coverage_bin))
  coverage_mismatch = execute("diff -q /tmp/coverage.bin.gz coverage.bin.gz", check=False)
  if coverage_mismatch:
    maybe_print("[command]Coverage is changed.", 1)
    git_cmd = "git -C %s " % (push_dir)
    execute(git_cmd + 'config --global user.email ' +
            '"58579435+EasyCov-bot@users.noreply.github.com"')
    execute(git_cmd + 'config --global user.name "EasyCov Bot"')
    upstream_branch = github_event['ref'].replace('refs/heads/', '')
    execute(git_cmd + 'checkout %s' % (push_sha))
    execute("cp -f %s.gz %s" % (coverage_bin, os.path.join(push_dir, "coverage.bin.gz")))
    execute(git_cmd + "add " + os.path.join(push_dir, "coverage.bin.gz"))
    execute(git_cmd + 'commit -m "Automated update of coverage.bin.gz"')
    execute(git_cmd + 'push origin HEAD:%s' % (upstream_branch))
  else:
    maybe_print("[command]Coverage is unchanged.", 1)

def do_pull_request(github_token, github_event):
  """Process pull request events."""
  maybe_print("[command]Detected Pull Request Event.", 1)
  pr_dir = "/tmp/pr"
  clone_url = github_event['pull_request']['base']['repo']['clone_url']
  maybe_print("[command]Cloning branch.", 1)
  # merge_sha is the one that would be potentially merged.
  merge_sha = os.getenv('GITHUB_SHA')
  # pr_sha is the head of the pull request.
  #pr_sha = github_event['pull_request']['head']['sha']

  git_cmd = "git -C %s " % (pr_dir)
  git_clone(clone_url, github_token, pr_dir)

  # We can't fetch the base_sha because it isn't advertised so fetch the
  # merge_sha and trust that at depth 2, the base_sha will be there.
  git_fetch(merge_sha, pr_dir, depth=2)
  # base_sha is the commit that we want to merge onto.
  base_sha = execute(git_cmd + ('rev-parse %s' % (merge_sha)))

  execute(git_cmd + 'checkout %s' % (base_sha))
  execute("cp -f %s /tmp/coverage.bin.gz" % (os.path.join(pr_dir, 'coverage.bin.gz')))
  execute("gunzip /tmp/coverage.bin.gz")
  coverage_bin = "/tmp/coverage.bin"
  base_coverage = Coverage.from_binary_filename(coverage_bin)

  # Make an annotated version of the base.
  root_dir = os.getenv('INPUT_ROOT-DIR')
  if root_dir:
    root_dir = os.path.join(pr_dir, root_dir)
    root_dir = os.path.abspath(root_dir)
  base_coverage.annotate(root_dir)
  execute(git_cmd + 'config --global user.email ' +
          '"58579435+EasyCov-bot@users.noreply.github.com"')
  execute(git_cmd + 'config --global user.name "EasyCov Bot"')
  execute(git_cmd + "commit -a --allow-empty --allow-empty-message")
  annotated_base_sha = execute(git_cmd + "rev-parse HEAD")

  # Get the coverage from the new sha.
  merge_coverage = collect_coverage()

  # Make an annotated version of the merge.
  execute(git_cmd + 'checkout %s' % (merge_sha))
  merge_coverage.annotate(root_dir)
  execute(git_cmd + "commit -a --allow-empty --allow-empty-message")
  annotated_merge_sha = execute(git_cmd + "rev-parse HEAD")

  execute(git_cmd + ("diff %s %s" % (annotated_base_sha, annotated_merge_sha)))

  #coverage_mismatch = execute("diff -q /tmp/coverage.bin.gz coverage.bin.gz", check=False)
  #if coverage_mismatch:
  #  maybe_print("[command]Coverage is changed.", 1)
  #  git_cmd = "git -C %s" % (push_dir)
  #  execute("cp -f %s.gz %s" % (coverage_bin, os.path.join(push_dir, "coverage.bin.gz")))
  #  upstream_branch = github_event['ref'].replace('refs/heads/', '')
  #  execute(git_cmd + ' checkout -b %s' % (upstream_branch))
  #  execute(git_cmd + " add /tmp/push/coverage.bin.gz")
  #  execute(git_cmd + ' commit -m "Automated update of coverage.bin.gz"')
  #  execute(git_cmd + ' push origin HEAD:%s' % (upstream_branch))
  #else:
  #  maybe_print("[command]Coverage is unchanged.", 1)

def main():
  """Run the action."""
  github_event_path = os.getenv('GITHUB_EVENT_PATH')
  github_event_name = os.getenv('GITHUB_EVENT_NAME')
  github_token = os.getenv('INPUT_GITHUB-TOKEN')
  with open(github_event_path, 'r') as event_file:
    github_event = json.loads(event_file.read())
  if github_event_name == 'push':
    do_push(github_token, github_event)
  if github_event_name == 'pull_request':
    do_pull_request(github_token, github_event)

if __name__ == '__main__':
  main()
