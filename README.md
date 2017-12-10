pymsync
=======

Author: Neil Munday

Introduction
------------

pymsync provides the `msync` utility which allows the user to synchronise a file path via `rsync` across multiple hosts. Rather than all destination hosts copying from the source host, `msync` uses an efficent algorithm that makes use of the destination hosts to copy to other hosts. This therefore dramatically decreases the time required to synchronise the files.

It is assumed that the host that `msync` is running on contains the directory/files to be synchronised.

For example, given *N* hosts named *host1, host2, host3, host4* etc. (where *host1* is the `msync` host) to copy to the copying process will take place as follows:

1. *host1* copies to *host2* (1 copy)
2. *host1* copies to *host3*, *host2* copies to *host4* (2 copies)
3. *host1* copies to *host5*, *host2* copies to *host6*, *host3* copies to *host7*, *host4* copies to *host8* (3 copies)
4. and so on

Usage
-----

```bash
./mysync.py -d server1,server2,server3,... -p /path/to/sync [-v ]
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

*Synchronise multiple files from within a directory to 4 servers*

```bash
./msync.py -d server1,server2,server3,server4 -p '/home/neil/my_dir/*'
```

**Note:** in the example above the path is encapsulated in single quotes to prevent `bash` from evaluation (and thus expanding) the asterisk character.
