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

		msync.py -d host1,host2,host3... -p /path/to/sync

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

def runCommand(cmd):
	"""
 	Execute the given command and return the result as a tuple.

	:param	cmd:	the command to run
	:returns:		a tuple of the form (return code, stdout, stderr)
	"""
	process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	logging.debug("return code: %s" % process.returncode)
	stdout = stdout.decode()
	stderr = stderr.decode()
	logging.debug("stdout:\n%s" % stdout)
	logging.debug("stderr:\n%s" % stderr)
	return (process.returncode, stdout, stderr)

class CommandTask(object):
	"""
	A CommandTask object is used by CommandProcess objects
	to execute commands.
	"""

	def __init__(self, command):
		"""
		Create the CommandTask object with the given command.

		:param command:		the command to execute
		"""
		self.__command = command
		logging.debug("CommandTask: %s" % self.__command)

	def run(self):
		"""
		Executes the given command - should be invoked by a CommandProcess object.

		:returns:	the return code from executing the command
		"""
		rtn, stdout, stderr = runCommand(self.__command)
		return rtn

class CommandProcess(multiprocessing.Process):
	"""
	The CommandProcess class subclasses the multiprocessing.Process class to implement
	the :func:`run` method. It is intended to allow multiple commands to be executed
	in parallel.
	"""

	def __init__(self, taskQueue):
		"""
		Creates a new CommandProcess object with the given task queue.

		:param taskQueue:	the task queue to get :class:`CommandTask` objects from
		"""
		super(CommandProcess, self).__init__()
		self.__taskQueue = taskQueue
		self.__ok = True # set to False later if we need to abort cleanly

	def run(self):
		"""
		Begin processing of the :class:`CommandTask` objects in the task queue.
		"""
		while True:
			task = self.__taskQueue.get()
			if task is None:
				# poison pill, time to exit
				logging.debug("%s: exiting..." % self.name)
				self.__taskQueue.task_done()
				break
			if self.__ok:
				# only process the task if all is well
				rtn = task.run()
				if rtn != 0:
					# something went wrong
					logging.error("aborting tasks, failed to run: %s" % self.__command)
					self.__ok = False
			self.__taskQueue.task_done()

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Uses divide and conqueor method to run rsync to N servers', add_help=True)
	parser.add_argument('-d', '--destinations', help="Comma separated list of destination hosts", required=True)
	parser.add_argument('-p', '--path', help="Source path to copy via rsync", required=True)
	parser.add_argument('-v', '--verbose', help='Turn on debug messages', dest='verbose', action='store_true')
	args = parser.parse_args()

	logLevel = logging.INFO
	if args.verbose:
		logLevel = logging.DEBUG

	logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', level=logLevel)

	checkExe(RSYNC_EXE)
	checkExe(SSH_EXE)

	hostname = os.uname()[1]
	logging.debug("our hostname: %s" % hostname)

	# List of hosts that we have copied to. We must exist in the list.
	destinations = [hostname]
	for d in args.destinations.split(","):
		if d != hostname:
			destinations.append(d.strip())

	logging.debug("destinations: %s" % destinations)

	processTotal = multiprocessing.cpu_count() * 2 # number of CommandProcess objects to create
	logging.info("using %d processes" % processTotal)

	hostTotal = len(destinations)
	hostsCopiedTo = 1 # source has already been "copied" to the first host

	i = 0
	copies = 1

	# work out the source and destination path strings to use with rsync
	sourcePath = os.path.abspath(args.path.strip())
	if sourcePath.endswith("/*"):
		destPath = sourcePath[:-1]
		checkDir(destPath)
	elif sourcePath.endswith("/"):
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

	while hostsCopiedTo < hostTotal:
		# loop until all hosts have been copied to
		logging.info("iteration %d, copies required: %d" % (i + 1, copies))
		# create a new task queue
		tasks = multiprocessing.JoinableQueue()
		processes = []

		remaining = hostTotal - hostsCopiedTo
		if copies > remaining:
			copies = remaining

		for h in range(0, remaining):
			if h + copies >= hostTotal:
				# less hosts than we need to copy to on this iteration
				break
			if h < processTotal:
				# create a new CommandProcess to handle the tasks
				process = CommandProcess(tasks)
				processes.append(process)
				process.start()
			# work out the host we are going to copy to
			hostToAdd = destinations[h + copies]
			logging.debug("%s copies to %s" % (destinations[h], hostToAdd))
			hostsCopiedTo += 1
			# create the CommandTask
			tasks.put(CommandTask("%s %s %s -av %s %s:%s" % (SSH_EXE, destinations[h], RSYNC_EXE, sourcePath, hostToAdd, destPath)))
		# add a "poison pill" to each process so they will exit when there is no more work to do
		for p in processes:
			tasks.put(None)
		# wait for all processes to finish before proceeding to the next iteration
		for p in processes:
			p.join()

		i += 1
		copies = 2**i
	# finished!
	logging.info("done")
