#!/usr/bin/env python

import os.path
import subprocess
import time
import sys
import argparse
import MySQLdb
import socket
import system
from twisted.internet import reactor, protocol

class node():
    def __init__(self,user,passwd,host='localhost',port=3306,db='mysql'):
        self.user=user
        self.passwd=passwd
        self.host=host
        self.port=port
        self.db=db

    def connect_db(node):
        # Connect to MySQL
        try:
            if os.path.exists(os.path.expanduser("~/.my.cnf")):
                print "[INFO] Using ~/.my.cnf for user / passwd on host %s:%s" % (node.host, node.port)
                db = MySQLdb.connect(read_default_file='~/.my.cnf',
                                     host=node.host,
                                     port=node.port,
                                     db=node.db)
            else:
                db = MySQLdb.connect(host=node.host,
                                     port=node.port,
                                     user=node.user,
                                     passwd=node.passwd,
                                     db=node.db)
        except MySQLdb.Error as e:
            if e[0] == 2003:
                print "[ERROR] Cannot connect to MySQL on host %s:%s" % (node.host, node.port)
                print
                sys.exit(2003)
            else:
                try:
                    db = MySQLdb.connect(host=node.host,
                                     port=node.port,
                                     user=node.user,
                                     passwd=node.passwd,
                                     db=node.db)
                except MySQLdb.Error as e:
                    print "[ERROR] %s on host %s:%s" % (e,node.host,node.port)
                    sys.exit(e[0])
        return db

def get_master_status(db):
    # Get master status
    try:
        cur = db.cursor()
        cur.execute("SHOW MASTER STATUS;")
        master_status = cur.fetchall()
        if len(master_status) == 0:
            print "[ERROR] You have not enabled binary logging, enabling 'log-bin' is mandatory"
        else:
            master_log_file = master_status[0][0]
            master_log_pos = master_status[0][1]
        cur.close()
    except MySQLdb.Error as e:
        print e
    return master_log_file, master_log_pos

def run_single_command(db, sql):
    try:
        cur = db.cursor()
        cur.execute(sql)
        ret = cur.fetchall()
        cur.close()
    except MySQLdb.Error as e:
        print e
    return ret

def get_slave_status(db):
    # Get slave status
    try:
        db.ping(True)
        cur = db.cursor()
        cur.execute("SHOW SLAVE STATUS;")
        slave_status = cur.fetchall()
        cur.close()
    except MySQLdb.Error as e:
        print e
    return slave_status

def change_master(db, master_cstring, master_log_file, master_log_pos, repl_user, repl_pass):
    # Change master
    try:
        cur = db.cursor()
        print "[INFO] Running STOP SLAVE as a safeguard before CHANGE MASTER"
        cur.execute("STOP SLAVE;")
        chg_master = ("CHANGE MASTER TO MASTER_HOST='%s',MASTER_PORT=%s,"
                     "MASTER_LOG_FILE='%s',MASTER_LOG_POS=%s,"
                     "MASTER_USER='%s',MASTER_PASSWORD='%s';" 
                     % (master_cstring.host, master_cstring.port, master_log_file, master_log_pos, 
                        repl_user, repl_pass))
        cur.execute(chg_master)
        cur.execute("START SLAVE;")
    except MySQLdb.Error as e:
        print e

def show_status(master_cstring,slave_cstring):
    master = master_cstring.connect_db()
    f, p = get_master_status(master)
    print "[INFO] Master log file is: %s & Master log pos is: %d" % (f,p)
    slave = slave_cstring.connect_db()
    slave_status = get_slave_status(slave)
    if len(slave_status) == 0:
        sf = "NULL"
        sp = "NULL"
        print "[WARNING] Slave is not yet set"
    else:
        sf = slave_status[0][9]
        sp = slave_status[0][21]
        print "[INFO] Slave log file is: %s & Slave log pos is: %d" % (sf,sp)
    return f, p, sf, sp

def clone_slave(master_cstring,slave_cstring,repl_user,repl_pass):
    master = master_cstring.connect_db()
    s = get_slave_status(master)
    if len(s) == 0:
        print "[WARNING] Source node is a MASTER node, cloning will incur load / locking"
    else:
        print "[INFO] Source node is a SLAVE node (unless master / master configuration is used)"

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((slave_cstring.host, 837))
    except socket.error, v:
        errorcode=v[0]
        if errorcode == 111:
            print "[ERROR] Connection Refused - ensure flipover-agent is running on " \
                  "destination node and ports 836 & 837 are open"
            print
            sys.exit(errorcode)
    print "[INFO] Connected successfully to flipover agent"
    print "[INFO] Running xbcloning process..."
    s.send("xbclone")
    data = s.recv(1024)
    if data != 'NCUP':
        print "[ERROR] Problem starting 'nc' on slave"
        sys.exit(3)
    time.sleep(1)
    p1 = subprocess.Popen("innobackupex --stream=tar /var/lib/mysql | nc " + slave_cstring.host + " 836", shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    out, err = p1.communicate()
    while p1.poll() is None:
        time.sleep(0.5)
    print "[INFO] Process for xbclone complete - status:", p1.returncode
    print "[INFO] Preparing backup and starting replication"
    matched_lines = [line for line in err.split('\n') if "MySQL binlog position" in line]
    s.send(matched_lines[0])
    data = s.recv(1024)
    if data == "READY":
        bl_coord = matched_lines[0].split("'")
        slave = slave_cstring.connect_db()
        change_master(slave, master_cstring, bl_coord[1], bl_coord[3], repl_user, repl_pass)
    s.close
    print "[INFO] Cloning complete, slave is replicating"

def promote_slave(master_cstring,slave_cstring,repl_pass): 
    slave = slave_cstring.connect_db()
    s = get_slave_status(slave)
    if len(s) == 0:
        print "[ERROR] Specified slave is actually a master, check parameters for '-n'"
        sys.exit(4)
    else:
        master_host = s[0][1]
        if master_host != master_cstring.host:
            print "[ERROR] The master host is %s in the SHOW SLAVE STATUS output and you have " \
                  "        specified %s as the master, which are different - please use the same " \
                  "        value defined in the runtime configuration i.e. SHOW SLAVE STATUS."
        repl_user = s[0][2]
        master_port = s[0][3]
        master = master_cstring.connect_db()
        slave_host_list = run_single_command(master,"SHOW SLAVE HOSTS")
        run_single_command(slave,"FLUSH TABLES WITH READ LOCK")
        master_log_file, master_log_pos = get_master_status(slave)
        for slave_info in slave_host_list:
            si_host = slave_info[1]
            si_port = slave_info[2]
            if slave_cstring.host != si_host:
                tmp_slave = node(user=slave_cstring.user, passwd=slave_cstring.passwd,host=si_host,port=si_port).connect_db()
                change_master(tmp_slave, slave_cstring, master_log_file, master_log_pos, repl_user, repl_pass)
                run_single_command(tmp_slave,"SET GLOBAL READ_ONLY=1")
        run_single_command(master,"SET GLOBAL READ_ONLY=1")
        change_master(master, slave_cstring, master_log_file, master_log_pos, repl_user, repl_pass)        
        print "[INFO] Previous MASTER %s set as SLAVE of new MASTER %s" % (master_cstring.host, slave_cstring.host)
        run_single_command(slave,"UNLOCK TABLES")
        run_single_command(slave,"STOP SLAVE")
        run_single_command(slave,"RESET SLAVE ALL")
        run_single_command(slave,"SET GLOBAL READ_ONLY=0")

def replace_master(slave_cstring,repl_pass):
    slave = slave_cstring.connect_db()
    s = get_slave_status(slave)
    if len(s) == 0:
        print "[ERROR] Specified slave is actually a master, check parameters for '-n'"
        sys.exit(4)
    else:
        master_host = s[0][1]
        repl_user = s[0][2]
        master_port = s[0][3]
        run_single_command(slave,"FLUSH TABLES WITH READ LOCK")
        master_log_file, master_log_pos = get_master_status(slave)
        print "[INFO] %s:%s became master while processing binlog file " \
              "%s at position %s" % (slave_cstring.host,slave_cstring.host,master_log_file, master_log_pos)
#        # Add logic here to chain existing slaves automagically (requires server inventory)
#        for servers in slave_server_list:
#            change_master(<DEFINE_HOST_NODE>, slave_cstring, master_log_file, master_log_pos, repl_user, repl_pass)
        run_single_command(slave,"UNLOCK TABLES")
        run_single_command(slave,"STOP SLAVE")
        run_single_command(slave,"RESET SLAVE ALL")
        run_single_command(slave,"SET GLOBAL READ_ONLY=0")
