from jnpr.junos.op.arp import ArpTable
from jnpr.junos import Device
from pprint import pprint
from flask import render_template
from app import app
from collections import defaultdict
import os.path
import requests
import json




#
# get vendor OUI function
#
def get_vendor(mac_addr):
	MAC_URL = 'http://macvendors.co/api/%s'
        RESPONSE = requests.get(MAC_URL % mac_addr)
	PARSED = RESPONSE.json()
	COMPANY = PARSED['result']['company']
	
	"""This is a simple function that you can use to keep the logic of looking up the vendor nice and separate.
	Obviously this is where you'd use `requests` to actually go look this up, but my dictionary mockup will suffice for now.
	"""
    
	mac_mappings = {
		mac_addr: COMPANY,
	}
    
	return mac_mappings[mac_addr]

@app.route('/')
@app.route('/guestwifi')
def guestwifi():
	#
	# connect to the EX and get the arp info
	#
	dev = Device(host="10.10.10.6", user="dlemon", password="w00ti3s").open()
	arp_table = ArpTable(dev)
	arp_table.get()
	tempdict = {}
	for mac, details in arp_table.items():
	    macs = list(details[2])
            # Calling out to a separate function here keeps our loop clean
            # Also using `append` instead of `insert` so we don't need to know length of list
            macs.append(get_vendor(mac))
            macs = tuple(macs)
            details[2]=macs
            # We want to use `mac` instead of the static `k3y` we were previously setting to 0 statically in the first line.
            # This was causing `tempdict` to overwrite the same value with each loop iteration.
            # Now, we see as many macs as are present in `arp_table`
            tempdict[mac]=details

	return render_template('details.html', macdict=tempdict)
	dev.close()
