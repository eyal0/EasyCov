#!/usr/bin/env python2
"""Run the script to process the coverage."""

from __future__ import print_function
import json
import os
import re
import shlex
from inspect import getframeinfo, stack
from subprocess import Popen, PIPE, STDOUT, check_output, CalledProcessError
from HTMLParser import HTMLParser
import urlparse
import colorama
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
    output = check_output(shlex.split(cmd), stderr=STDOUT)
    if output:
      maybe_print(output, 3)
  except CalledProcessError as exc:
    maybe_print(exc.output, 3)
    if check:
      raise
    else:
      return exc.returncode
  return output

def git_clone(repo_url, github_token, target_dir):
  """Clone a repo into the target_dir."""
  maybe_print("[command]Cloning branch.", 1)
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
  return total_coverage

def do_push(github_token, github_event):
  """Process push events."""
  maybe_print("[command]Detected Push Event.", 1)
  push_dir = "/tmp/push"
  clone_url = github_event['repository']['clone_url']
  git_clone(clone_url, github_token, push_dir)
  push_sha = github_event['after']
  git_fetch(push_sha, push_dir)
  coverage_bin = "/tmp/coverage.bin"
  with open(coverage_bin, 'wb') as coverage_file:
    coverage_file.write(collect_coverage().to_binary())
  execute("gzip -n %s" % (coverage_bin))
  execute("cp -f /tmp/coverage.bin.gz " + os.getenv('GITHUB_WORKSPACE'))

def color_diff(path, base_sha, change_sha):
  """git giff the base_sha to change_sha in the path, colorizing the output."""
  diff = execute("git -C %s diff --color=never %s %s" %
                 (path, base_sha, change_sha))
  diff_so_fancy = Popen(['diff-so-fancy'], stdout=PIPE, stdin=PIPE, stderr=PIPE)
  output, stderr = diff_so_fancy.communicate(input=diff)
  if output:
    maybe_print(output, 3)
  if stderr:
    maybe_print(stderr, 3)
  if diff_so_fancy.returncode:
    caller = getframeinfo(stack()[1][0])
    filename = caller.filename.replace("/root/EasyCov", "")
    maybe_print("::error file=%s,line=%d::%s" % (filename, caller.lineno, stderr), 1)
    raise CalledProcessError(diff_so_fancy.returncode, "diff-so-fancy", output)
  return output

def highlight_coverage_line(fancy_line):
  """Highlight the start of a line if it starts with a ratio like 1/2.

  Whatever ANSI style codes are present at the start of the string are saved and
  used after the ratio is printed.  The ratio is printed in red background for 0
  and green background for 1.  The rest have yellow backgrounds.
  """
  match_object = re.match(
      r"^(?P<style>(\x1B\[[0-9;]*m)*)(?P<numer>\d+)/(?P<denom>\d+)(?P<end> .*)$", fancy_line)
  if not match_object:
    return fancy_line
  if int(match_object.group('numer')) == int(match_object.group('denom')):
    background = colorama.Back.GREEN
  elif int(match_object.group('numer')) == 0:
    background = colorama.Back.RED
  else:
    background = colorama.Back.YELLOW
  return (colorama.Fore.BLACK + background + colorama.Style.BRIGHT + # Colorize
          match_object.group('numer') + "/" + match_object.group('denom') + # coverage ratio
          colorama.Style.RESET_ALL + match_object.group('style') + # back to original
          match_object.group('end')) # all the rest.

class ChecksHTMLParser(HTMLParser, object):
  """Finds coverage.bin.gz artifact in the checks HTML page."""

  def __init__(self):
    self._maybe_href = None
    self._href = None
    super(ChecksHTMLParser, self).__init__()

  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      for attr in attrs:
        if attr[0] == 'href' and 'artifacts' in attr[1]:
          print(attr)
          self._maybe_href = attr[1]

  def handle_endtag(self, tag):
    self._maybe_href = None

  def handle_data(self, data):
    if self._maybe_href and data == 'coverage.bin.gz':
      self._href = self._maybe_href

  def href(self):
    """Get the href of the coverage.bin.gz file."""
    return self._href

def get_coverage_artifact(base_sha):
  """Search the artifacts of previous CI runs to find coverage.bin.gz.

  This returns the Coverage that was found.
  """
  checks_url = 'https://github.com/%s/commit/%s/checks' % (os.getenv('GITHUB_REPOSITORY'), base_sha)
  checks_html = execute("wget -H -O - '%s'" % (checks_url))
  parser = ChecksHTMLParser()
  parser.feed(checks_html)
  coverage_bin_gz_url = urlparse.urljoin(checks_url, parser.href())
  execute("wget -H -O /tmp/base_coverage.bin.gz.zip '%s'" % (coverage_bin_gz_url))
  execute("unzip -d /tmp/base_coverage /tmp/base_coverage.bin.gz.zip")
  execute("gunzip /tmp/base_coverage/coverage.bin.gz/coverage.bin.gz")
  return Coverage.from_binary_filename("/tmp/base_coverage/coverage.bin.gz/coverage.bin")

def do_pull_request(github_token, github_event):
  """Process pull request events."""
  maybe_print("[command]Detected Pull Request Event.", 1)
  pr_dir = "/tmp/pr"
  clone_url = github_event['pull_request']['base']['repo']['clone_url']
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
  base_sha = execute(git_cmd + ('rev-parse %s^' % (merge_sha))).strip()

  base_coverage = get_coverage_artifact(base_sha)
  execute(git_cmd + 'checkout %s' % (base_sha))

  root_dir = os.getenv('INPUT_ROOT-DIR')
  if root_dir:
    root_dir = os.path.join(pr_dir, root_dir)
    root_dir = os.path.abspath(root_dir)

  # Make an annotated version of the base.
  base_coverage.annotate(root_dir)
  execute(git_cmd + "commit -a --allow-empty -m annotated")
  annotated_base_sha = execute(git_cmd + "rev-parse HEAD").strip()

  # Make an annotated version of the merge.
  execute(git_cmd + 'checkout %s' % (merge_sha))
  collect_coverage().annotate(root_dir)
  execute(git_cmd + "commit -a --allow-empty -m annotated")
  annotated_merge_sha = execute(git_cmd + "rev-parse HEAD")
  maybe_print(
      "\n".join(highlight_coverage_line(line)
                for line in
                color_diff(
                    pr_dir, annotated_base_sha, annotated_merge_sha).split("\n")),
      1)
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
  try:
    github_event_path = os.getenv('GITHUB_EVENT_PATH')
    github_event_name = os.getenv('GITHUB_EVENT_NAME')
    github_token = os.getenv('INPUT_GITHUB-TOKEN')
    with open(github_event_path, 'r') as event_file:
      github_event = json.loads(event_file.read())
    if github_event_name == 'push':
      do_push(github_token, github_event)
    if github_event_name == 'pull_request':
      do_pull_request(github_token, github_event)
  except Exception as exc:# pylint: disable=broad-except
    caller = getframeinfo(stack()[1][0])
    filename = caller.filename.replace("/root/EasyCov", "")
    maybe_print("::error file=%s,line=%d::%s" % (filename, caller.lineno, str(exc)), 1)
    raise

if __name__ == '__main__':
  main()
