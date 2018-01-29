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

```bash
./mysync.py -d server1,server2,server3,... -p /path/to/sync [ -v ] [ -c copiesPerHost ]
```
It issumed that:
* `rsync` has been installed on all hosts
* all hosts can `ssh` to each other passwordless

**Examples**

*Synchronise a file to 4 servers*

```bash
./msync.py -d server1,server2,server3,server4 -p /home/neil/my.iso
```

*Synchronise a directory to 4 servers*

```bash
./msync.py -d server1,server2,server3,server4 -p /home/neil/my_dir
```

*Synchronise a directory to 4 servers using 2 copy processes per host*

```bash
./msync.py -d server1,server2,server3,server4 -p /home/neil/my_dir -c 2
```
