import socket
import subprocess
import fcntl
import struct

def cmd_exists(cmd):
    return subprocess.call("type " + cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

#####################################
# Todo security stuff (not crucial) #
#####################################

## Client - Call this method to encrypt your data and send the encrypted data

# from Crypto.Cipher import AES

# def do_encrypt(message):
#     obj = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
#     ciphertext = obj.encrypt(message)
#     return ciphertext

## Server - Receive data and call this method to decrypt the data

# from Crypto.Cipher import AES

# def do_decrypt(ciphertext):
#     obj2 = AES.new('This is a key123', AES.MODE_CBC, 'This is an IV456')
#    message = obj2.decrypt(ciphertext)
#    return message


