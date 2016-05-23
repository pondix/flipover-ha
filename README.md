# Flipover HA Manaager 

Flipover HA Manager is a utility to perform

- Cloning of replicas: Using Xtrbackup to stream a backup and start replication
- Master / Slave Promotion: Rechaining all slaves to a new master
- Master replacement: In case no master is available

No SSH access is required and the tools is designed for simplicity.

## Configuration

#### Open ports required:

- 3306 (or mysql port if different)
- 837 (xtrabackup port used)
- 836 (flipover agent port)

#### Packages required:

- yum install openssh-server
- yum install mariadb-server   (becomes install percona repo)
- yum install MySQL-python
- yum install gcc
- yum install nc
- easy_install twisted

#### Required vars /etc/my.cnf

```
[mysqld]
log-bin # mandatory for replication
server-id=19216811 # mandatory for replication - must be unique for each host
log-slave-updates # mandatory for promote-slave
report-host=<ip-address of server> # mandatory for promote-slave
binlog-format=ROW # optional however recommended in general
```

## Command line usage:

#### flipover-cmd
```
usage: flipover-cmd [-h] [-N HOST] [-P PORT] [-U USER] [-S PASSWD]
                    [-n SLAVEHOST] [-p SLAVEPORT] [-u SLAVEUSER]
                    [-s SLAVEPASSWD] [-r REPL_USER] [-c REPL_PASS]
                    [-m {show-status,clone-slave,promote-slave,replace-master}]

Flipover MySQL HA Manager

optional arguments:
  -h, --help            show this help message and exit
  -N HOST, --node HOST  Hostname for master / source ~ defaults to localhost
                         
  -P PORT, --port PORT  Port for master / source ~ defaults to 3306
                         
  -U USER, --user USER  Username to connect to master / source ~ defaults to ''
                         
  -S PASSWD, --secret PASSWD
                        Password to connect to master / source ~ defaults to ''
                         
  -n SLAVEHOST, --slavenode SLAVEHOST
                        Hostname for slave ~ defaults to localhost
                         
  -p SLAVEPORT, --slaveport SLAVEPORT
                        Port for slave ~ defaults to 3306
                         
  -u SLAVEUSER, --slaveuser SLAVEUSER
                        Username to connect to slave ~ defaults to 'root'
                         
  -s SLAVEPASSWD, --slavesecret SLAVEPASSWD
                        Password to connect to slave ~ defaults to ''
                         
  -r REPL_USER, --repluser REPL_USER
                        Username to connect to slave ~ defaults to 'repl'
                         
  -c REPL_PASS, --replpass REPL_PASS
                        Password to connect replication stream to master ~ defaults to ''
                         
  -m {show-status,clone-slave,promote-slave,replace-master}, --mode {show-status,clone-slave,promote-slave,replace-master}
                        
                        Choose one of the three '-m' options ~ defaults to 'show-status':
                         
                          show-status:   Prints master & slave binlog filename and positions
                        
                          clone-slave:   Clones a slave using Xtrabackup using the local serer as source
                                         e.g. 'flipover -m clone-slave -N 10.10.10.1 -n 10.10.10.2' will 
                                         stream a fresh Xtrabackup from 10.10.10.1 to 10.10.10.2 and 
                                         start replication between the current master and 10.10.10.2.
                                         >> You must run 'flipover -m ...' from 10.10.10.1 in this scenario.
                                         NOTE: The source can be a master, this is not advisable.
                         
                          promote-slave: Promotes the specified slave to master
  ```
  
#### flipover-agent

```
usage: flipover-agent [-h] [-c CONF] [-s SERVICE]

Flipover MySQL HA Agent

optional arguments:
  -h, --help            show this help message and exit
  -c CONF, --conf CONF  Location of my.cnf configuration file - defaults to
                        /etc/my.cnf. For Ubuntu or Debian you may need to set
                        to /etc/mysql/my.cnf
  -s SERVICE, --service SERVICE
                        Name of MySQL service e.g. 'mysql' for default
                        'service mysql start'. For MariaDB you may need to set
                        to 'mariadb'
```
