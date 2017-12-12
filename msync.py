#!/usr/bin/env python3

#
#    This file is part of pymsync.
#
#    pymsync is a tool to synchronise files between many hosts using rsync.
#    It uses a divide and conqueor method to efficiently copy files
#    between hosts on a network.
#
#    Copyright (C) 2017 Neil Munday (neil@mundayweb.com)
#
#    pymsync is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    pymsync is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with pymsync.  If not, see <http://www.gnu.org/licenses/>.
#

"""
	:author: Neil Munday

	Usage:

		msync.py -d host1,host2,host3... -p /path/to/sync [ -v ] [ -c copiesPerHost ]

		Notes:
			- it is assumed that each host can SSH passwordless to all other hosts
			- it is assumed that all hosts have the rsync command installed
"""

import argparse
import logging
import multiprocessing
import shlex
import os
import subprocess
import sys

RSYNC_EXE = "/usr/bin/rsync"
SSH_EXE = "/usr/bin/ssh"
STDBUF_EXE = "/usr/bin/stdbuf"

def checkDir(d):
	"""
	Tests if the given file path is a directory.
	The program will exit if it is not via the :func:`die` function.

	:param	d: the file path to check
	"""
	if not os.path.isdir(d):
		die("%d is not a directory")

def checkExe(e):
	"""
	Tests if the given file path is exists.
	The program will exit if it does not via the :func:`die` function.

	:param	e: the file path to check
	"""
	if not os.path.exists(e):
		die("%s does not exist")

def die(msg):
	"""
	Exit the program with the given error message.

	:param	msg: the file path to check
	"""
	logging.error(msg)
	sys.exit(1)

class CommandProcess(multiprocessing.Process):
	"""
	The CommandProcess class subclasses the multiprocessing.Process class to implement
	the :func:`run` method. It is intended to allow multiple commands to be executed
	in parallel.
	"""

	def __init__(self, command):
		"""
		Creates a new CommandProcess object to run the given command.

		:param command:	the command to run by this process
		"""
		super(CommandProcess, self).__init__()
		# prevent stdout from being buffered
		self.__command = "%s -o0 %s" % (STDBUF_EXE, command)

	def run(self):
		"""
		Run the command assigned to this process.
		"""
		logging.debug("%s: running: %s" % (self.name, self.__command))
		process = subprocess.Popen(shlex.split(self.__command), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		stdout, stderr = process.communicate()
		logging.debug("return code: %s" % process.returncode)
		if process.returncode != 0 or logging.getLogger().getEffectiveLevel() == logging.DEBUG:
			stdout = stdout.decode()
			stderr = stderr.decode()
			if process.returncode != 0:
				die("%s: failed to run: %s\nstdout:\n%s\nstderr:\n%s\n" % (self.name, self.__command, stdout, stderr))
			logging.debug("%s: stdout:\n%s" % (self.name, stdout))
			logging.debug("%s: complete" % self.name)

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Uses divide and conqueor method to run rsync to N servers', add_help=True)
	parser.add_argument('-d', '--destinations', help="Comma separated list of destination hosts", required=True)
	parser.add_argument('-p', '--path', help="Source path to copy via rsync", required=True)
	parser.add_argument('-v', '--verbose', help="Turn on debug messages", action='store_true')
	parser.add_argument('-c', '--copies-per-host', help="Number of copies to perform per host (default = 1)", dest="copiesPerHost", type=int, default=1)
	args = parser.parse_args()

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)

	checkExe(RSYNC_EXE)
	checkExe(SSH_EXE)
	checkExe(STDBUF_EXE)

	hostname = os.uname()[1]
	logging.debug("our hostname: %s" % hostname)

	inList = [hostname]
	outList = []
	for d in args.destinations.split(","):
		if d != hostname and d not in inList:
			outList.append(d)

	logging.debug("hosts to copy to: %s" % ",".join(outList))
	logging.debug("copies per host: %s" % args.copiesPerHost)

	# work out the source and destination path strings to use with rsync
	sourcePath = os.path.abspath(args.path.strip())
	if sourcePath.endswith("/"):
		destPath = sourcePath
		sourcePath = sourcePath[:-1]
		checkDir(sourcePath)
	else:
		if os.path.isdir(sourcePath):
			destPath = os.path.split(sourcePath)[0]
		elif os.path.isfile(sourcePath):
			destPath = "%s" % sourcePath
		else:
			die("source path is not a file or directory")

	logging.debug("source path: %s" % sourcePath)
	logging.debug("destination path: %s" % destPath)

	logging.info("syncing...")
	exitOk = True

	while len(outList) > 0:
		# loop until all hosts have been copied to
		logging.info("hosts left to copy to: %d" % len(outList))
		# list of CommandProcess objects
		processes = []

		# loop over each host in a copy inList,
		# and start N copies to hosts in outList
		for sourceHost in list(inList):
			for i in range(args.copiesPerHost):
				if len(outList) == 0:
					break
				destHost = outList.pop()
				inList.append(destHost)
				logging.info("%s copying to %s" % (sourceHost, destHost))
				if sourceHost == hostname:
					process = CommandProcess("%s -av %s %s:%s" % (RSYNC_EXE, sourcePath, destHost, destPath))
				else:
					process = CommandProcess("%s %s %s -av %s %s:%s" % (SSH_EXE, sourceHost, RSYNC_EXE, sourcePath, destHost, destPath))
				processes.append(process)
				process.start()

		for p in processes:
			p.join()
			if exitOk and p.exitcode != 0:
				exitOk = False
		logging.debug("all processes joined main thread")
		if not exitOk:
			die("one or more hosts failed to copy %s" % sourcePath)

	# finished!
	logging.info("done")
	sys.exit(0)
