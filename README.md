pymsync
=======

Author: Neil Munday

Contributors: David Murray (https://github.com/dajamu)

Repository: https://github.com/neilmunday/pymsync

Introduction
------------

pymsync provides the `msync` utility which allows the user to synchronise a file path via `rsync` across multiple hosts. Rather than all destination hosts copying from the source host, `msync` uses an efficient algorithm that makes use of the destination hosts to copy to other hosts. This therefore dramatically decreases the time required to synchronise the files.

It is assumed that the host that `msync` is running on contains the directory/files to be synchronised.

Usage
-----

```
msync [-h] -d DESTINATIONS -p PATH [-v] [-n] [-c COPIESPERHOST]

optional arguments:
  -h, --help            show this help message and exit
  -d DESTINATIONS, --destinations DESTINATIONS
                        Comma separated list of destination hosts
  -p PATH, --path PATH  Source path to copy via rsync
  -v, --verbose         Turn on debug messages
  -n, --dry-run         Perform a dry-run - do not copy anything
  -c COPIESPERHOST, --copies-per-host COPIESPERHOST
                        Number of copies to perform per host (default = 1)
```

It issumed that:
* `rsync` has been installed on all hosts
* all hosts can `ssh` to each other password-less

**Examples**

*Synchronise a file to 4 servers*

```bash
./msync -d server1,server2,server3,server4 -p /home/neil/my.iso
```

*Synchronise a directory to 4 servers*

```bash
./msync -d server1,server2,server3,server4 -p /home/neil/my_dir
```

*Synchronise a directory to 4 servers using 2 copy processes per host*

```bash
./msync -d server1,server2,server3,server4 -p /home/neil/my_dir -c 2
```

*Perform a dry-run of a directory synchronise to 4 servers using 2 copy processes per host*

```bash
./msync -d server1,server2,server3,server4 -p /home/neil/my_dir -c 2 -n
```
