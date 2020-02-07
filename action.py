#!/usr/bin/env python2
"""Run the script to process the coverage."""

from __future__ import print_function
import json
import os
import re
import shlex
import sys
from collections import defaultdict
from inspect import getframeinfo, stack
from subprocess import Popen, PIPE, STDOUT, check_output, CalledProcessError
from HTMLParser import HTMLParser
import urlparse

import colorama
from easycov.coverage import Coverage
from easycov.diff_mapper import DiffMapper

def maybe_print(text, level, prefix=""):
  """Print a string only if the verbosity is high enough."""
  verbosity = int(os.getenv('INPUT_VERBOSITY'))
  if level > verbosity:
    return
  if prefix:
    text = "\n".join(prefix + x for x in text.splitlines())
  print(text)

def maybe_debug(text, level):
  """Like maybe_print but with the debug coloring."""
  maybe_print(text, level, "[debug]")

def execute(cmd, check=True):
  """Run cmd, printing the command as it is run.

  Returns the result.  If check is True, raise an exception on errors.
  """
  maybe_print(cmd, 2, "[command]")
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
  maybe_print("Cloning branch.", 1, "[command]")
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
  maybe_print("Collecting coverage.", 1, "[command]")
  xml_coverage = os.getenv('INPUT_XML-COVERAGE')
  if xml_coverage:
    for xml_filename in xml_coverage.split(" "):
      total_coverage += Coverage.from_xml(xml_filename, root_dir)
  lcov_coverage = os.getenv('INPUT_LCOV-COVERAGE')
  if lcov_coverage:
    for lcov_filename in lcov_coverage.split(" "):
      total_coverage += Coverage.from_lcov(lcov_filename, root_dir)
  return total_coverage

def write_coverage_bin_gz(coverage):
  """Write covearge coverage.bin.gz to github workspace"""
  coverage_bin = "/tmp/coverage.bin"
  with open(coverage_bin, 'wb') as coverage_file:
    coverage_file.write(coverage.to_binary())
  execute("gzip -n %s" % (coverage_bin))
  execute("cp -f /tmp/coverage.bin.gz " + os.getenv('GITHUB_WORKSPACE'))

def do_push():
  """Process push events."""
  maybe_print("Detected Push Event.", 1, "[command]")
  write_coverage_bin_gz(collect_coverage())
  return True

def color_diff(path, base_sha, change_sha):
  """git giff the base_sha to change_sha in the path, colorizing the output."""
  diff = execute("git -C %s diff --color %s %s" %
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
    print("::error file=%s,line=%d::%s" % (filename, caller.lineno, stderr))
    raise CalledProcessError(diff_so_fancy.returncode, "diff-so-fancy", output)
  return output

def highlight_coverage_line(fancy_line):
  """Highlight the start of a line if it starts with a ratio like 1/2.

  Whatever ANSI style codes are present at the start of the string are saved and
  used after the ratio is printed.  The ratio is printed in red background for 0
  and green background for 1.  The rest have yellow backgrounds.
  """
  ansi_code = r"(?:\x1B\[[0-9;]*m)"
  regex = r"""(?x)                                # Verbose
            ^(?P<style>{ansi_code}*)              # The leading style
             (?P<numer>\d(?:{ansi_code}|\d)*)     # Numerator
             /                                    # Fraction slash
             (?P<denom>\d(?:{ansi_code}|\d)*)     # Denominator
             (?P<end>\ .*)$                       # Rest of string
           """.format(
               ansi_code=ansi_code
           )
  match_object = re.match(regex, fancy_line)
  if not match_object:
    return fancy_line
  # The numerator and denominator might have ansi codes in them.
  numer_int = int(re.sub(ansi_code, "", match_object.group('numer')))
  denom_int = int(re.sub(ansi_code, "", match_object.group('denom')))
  if numer_int == denom_int:
    background = colorama.Back.GREEN
  elif numer_int == 0:
    background = colorama.Back.RED
  else:
    background = colorama.Back.YELLOW
  return (match_object.group('style') + # Original style.
          colorama.Fore.BLACK + background + colorama.Style.BRIGHT + # Highlight coverage.
          match_object.group('numer') + # Numerator, which might have ansi codes in it.
          colorama.Style.RESET_ALL + match_object.group('style') + # back to original
          colorama.Fore.BLACK + background + colorama.Style.BRIGHT + # Highlight coverage.
          "/" + match_object.group('denom') + # coverage ratio
          colorama.Style.RESET_ALL + match_object.group('style') + # back to original
          match_object.group('end')) # all the rest.

def get_diff_stats(pr_dir, base_sha, base_coverage, merge_sha, merge_coverage):
  """Get stats on change in coverage."""
  stats = defaultdict(lambda: defaultdict(int))
  diff_map = DiffMapper.from_string(execute("git -C %s diff --color=never --no-prefix %s %s" %
                                            (pr_dir, base_sha, merge_sha)))
  for filename, file_coverage in merge_coverage.get_coverage().iteritems():
    for line_number, hits in file_coverage.iteritems():
      base_filename, base_line_number = diff_map[filename][line_number]
      if base_filename is None or base_line_number is None:
        old_hits = None
      else:
        old_hits = base_coverage.get_coverage(base_filename, base_line_number)
      stats[hits][old_hits] += 1
  return stats

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
          self._maybe_href = attr[1]

  def handle_endtag(self, tag):
    self._maybe_href = None

  def handle_data(self, data):
    if self._maybe_href and data == 'coverage.bin.gz':
      self._href = self._maybe_href

  def href(self):
    """Get the href of the coverage.bin.gz file."""
    return self._href

def get_coverage_artifact(base_sha, github_token):
  """Search the artifacts of previous CI runs to find coverage.bin.gz.

  This returns the Coverage that was found.
  """
  checks_url = 'https://github.com/%s/commit/%s/checks' % (os.getenv('GITHUB_REPOSITORY'), base_sha)
  checks_html = execute(
      "wget --header 'Authorization: token %s' -H -O - '%s'" %
      (github_token, checks_url))
  parser = ChecksHTMLParser()
  parser.feed(checks_html)
  if not parser.href():
    return None
  coverage_bin_gz_url = urlparse.urljoin(checks_url, parser.href())
  execute("wget --header 'Authorization: token %s' -H -O /tmp/base_coverage.bin.gz.zip '%s'" %
          (github_token, coverage_bin_gz_url))
  execute("mkdir -p /tmp/base_coverage")
  execute("unzip -d /tmp/base_coverage /tmp/base_coverage.bin.gz.zip")
  execute("gunzip /tmp/base_coverage/coverage.bin.gz/coverage.bin.gz")
  return Coverage.from_binary_filename("/tmp/base_coverage/coverage.bin.gz/coverage.bin")

def check_coverage(diff_stats):
  """Sums the coverage in the diff_stats.

  Returns true if coverage is maintained or improved.  Returns false if coverage
  is worse.
  """
  newly_covered = 0
  newly_uncovered = 0
  coverage_increased = 0
  coverage_decreased = 0
  for target_hit, source_hits in diff_stats.iteritems():
    for source_hit, count in source_hits.iteritems():
      if target_hit is None:
        # Ignore lines that are removed.
        continue
      elif source_hit is None:
        # New lines.
        if float(target_hit) == 1:
          newly_covered += count
        else:
          newly_uncovered += count
      else:
        if target_hit > source_hit:
          coverage_increased += count
        elif target_hit < source_hit:
          coverage_decreased += count
  maybe_print("Lines with coverage increased: %d" % coverage_increased, 1)
  maybe_print("Lines with coverage decreased: %d" % coverage_decreased, 1)
  maybe_print("New lines with coverage: %d" % newly_covered, 1)
  maybe_print("New lines without coverage: %d" % newly_uncovered, 1)
  return coverage_decreased == 0 and newly_uncovered == 0

def remove_unmodified_files(git_cmd):
  """git rm files that are not modified."""
  tracked_files = execute(git_cmd + "ls-tree -r HEAD --name-only").splitlines()
  modified_files = execute(git_cmd + "ls-files -m").splitlines()
  for tracked_file in tracked_files:
    if tracked_file not in modified_files:
      execute(git_cmd + "rm '" + tracked_file + "'")

def do_pull_request(github_token, github_event):
  """Process pull request events.

  Returns True if it all works and coverage didn't go down."""
  maybe_print("Detected Pull Request Event.", 1, "[command]")
  merge_coverage = collect_coverage()
  write_coverage_bin_gz(merge_coverage)
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

  base_coverage = get_coverage_artifact(base_sha, github_token)
  if not base_coverage:
    # Can't find the base coverage, maybe it expired or there was no push request?
    print("::error::Can't find the coverage for base sha %s" % (base_sha))
    return False
  execute(git_cmd + 'checkout %s' % (base_sha))

  root_dir = os.getenv('INPUT_ROOT-DIR')
  if root_dir:
    root_dir = os.path.join(pr_dir, root_dir)
    root_dir = os.path.abspath(root_dir)

  # Make an annotated version of the base.
  base_coverage.annotate(root_dir)
  remove_unmodified_files(git_cmd)
  execute(git_cmd + "commit -a --allow-empty -m annotated")
  annotated_base_sha = execute(git_cmd + "rev-parse HEAD").strip()

  # Make an annotated version of the merge.
  execute(git_cmd + 'checkout %s' % (merge_sha))
  merge_coverage.annotate(root_dir)
  remove_unmodified_files(git_cmd)
  execute(git_cmd + "commit -a --allow-empty -m annotated")
  annotated_merge_sha = execute(git_cmd + "rev-parse HEAD")
  maybe_print(
      "\n".join(highlight_coverage_line(line)
                for line in
                color_diff(
                    pr_dir, annotated_base_sha, annotated_merge_sha).split("\n")),
      1)
  diff_stats = get_diff_stats(pr_dir, base_sha, base_coverage, merge_sha, merge_coverage)
  maybe_debug(str(diff_stats), 2)
  if not check_coverage(diff_stats):
    print("::error::Coverage is decreased")
    return False
  return True

def main():
  """Run the action.  Return success value.

  Success means that nothing was done, or it was a push and everything worked,
  or it was a PR and everything worked and coverage did not decrease.
  """
  try:
    github_event_path = os.getenv('GITHUB_EVENT_PATH')
    github_event_name = os.getenv('GITHUB_EVENT_NAME')
    github_token = os.getenv('INPUT_GITHUB-TOKEN')
    with open(github_event_path, 'r') as event_file:
      github_event = json.loads(event_file.read())
    if github_event_name == 'push':
      return do_push()
    if github_event_name == 'pull_request':
      return do_pull_request(github_token, github_event)
    return 0
  except Exception as exc:# pylint: disable=broad-except
    caller = getframeinfo(stack()[1][0])
    filename = caller.filename.replace("/root/EasyCov", "")
    maybe_print("::error file=%s,line=%d::%s" % (filename, caller.lineno, str(exc)), 1)
    raise

if __name__ == '__main__':
  print("::set-output name=success::%s" % ("true" if main() else "false"))
  sys.exit(0)
