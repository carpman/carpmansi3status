#!/usr/bin/env python2

import json
import sys
import time
import datetime
import os
import socket
import struct
import fcntl

SIOCGIFADDR = 0x8915
BATT_YELLOW_THRESH = 40
BATT_RED_THRESH = 20

def output(out_array):
    sys.stdout.write(',')
    sys.stdout.write(json.dumps(out_array))
    sys.stdout.flush()

def add_line(out_array, line, color=None, seperator=True):
    if not line:
        return
    output = {}
    output['full_text'] = line
    if color:
        output['color'] = color
    output['seperator'] = seperator
    out_array.append(output)

def read_value(path):
    with open(path, 'r') as value_file:
        return value_file.read().strip()

def format_minutes(minutes):
    hours = minutes/60
    minutes = minutes%60
    return "%02d:%02d" % (hours,minutes)

def tp_battery(root, label='BAT'):
    color = None
    try:
        power_avg = int(read_value(os.path.join(root, 'power_avg')))
        percent_remain = read_value(os.path.join(root, 'remaining_percent'))
        remaining_time = read_value(os.path.join(root, 'remaining_running_time_now'))
        remaining_charge_time = read_value(os.path.join(root, 'remaining_charging_time'))

        if(remaining_time == 'not_discharging' and remaining_charge_time == 'not_charging'):
            return ("%s: %s%%@STBY" % (label, percent_remain), color)
        elif(remaining_charge_time == 'not_charging'):
            if int(percent_remain) < BATT_RED_THRESH:
                color = "#ff0000"
            elif int(percent_remain) < BATT_YELLOW_THRESH:
                color = "#00ffff"
            else:
                color = "#00ff00"
            return ("%s: %s%%@%.2fW %s" % (label, percent_remain, power_avg/1000.0, format_minutes(int(remaining_time))), color)
        elif(remaining_time == 'not_discharging'):
            color = "#0000ff"
            return ("%s: %s%%@CHRG %s" % (label, percent_remain, format_minutes(int(remaining_charge_time))), color)
        else:
            return ("%s: UNKN" % label, color)
    except:
        return (None, None)

def get_ip(interface):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockfd = sock.fileno()
    ifreq = struct.pack('16sH14s', interface, socket.AF_INET, '\x00'*14)
    try:
        res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
    except:
        return None
    ip = struct.unpack('16sH2x4s8x', res)[2]
    return socket.inet_ntoa(ip)

def is_wireless(interface):
    return 'wireless' in os.listdir('/sys/class/net/%s/' % interface)

def net_interface(interface):
    ip = get_ip(interface)
    color = "#00ff00"
    if not ip:
        ip = "Down"
        color = "#ff0000"
    if is_wireless(interface):
        return ("%s: W %s" % (interface, ip), color)
    else:
        return ("%s: %s" % (interface, ip), color)

def dynamic_interfaces(out_array, reject=['lo']):
    for interface in os.listdir('/sys/class/net/'):
        if interface not in reject:
            add_line(out_array, *net_interface(interface))

def time_string():
    return (datetime.datetime.now().strftime("%a %m-%d-%y %H:%M:%S"), None)

if __name__ == '__main__':
    sys.stdout.write("{\"version\":1}[[]")
    sys.stdout.flush()
    while True:
        out_array = []
        add_line(out_array, *tp_battery('/sys/devices/platform/smapi/BAT0/', 'BAT0'))
        add_line(out_array, *tp_battery('/sys/devices/platform/smapi/BAT1/', 'BAT1'))
        dynamic_interfaces(out_array)
        add_line(out_array, *time_string())
        output(out_array)
        time.sleep(5)
