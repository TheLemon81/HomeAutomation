from jnpr.junos.op.arp import ArpTable
from jnpr.junos import Device
from pprint import pprint
from flask import render_template
from app import app
from collections import defaultdict
from myTables.srxadddresses import AddressTable
import os.path
import requests
import json


#
# match IP to SRX address-book entry
#
def get_srx_address(ip_addr, arp_tbl):
	KNOWN_ENTRIES = {}
	for ANAME, value in ip_addr.items():
		for mac, details in arp_tbl.items():
			if details[1][1] in value[0][1]:
				KNOWN_ENTRIES[details[1][1]]=ANAME
	return KNOWN_ENTRIES
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
	dev.close()
	#
	# connect to the SRX and get the address book info
	#
	dev = Device(host="10.10.10.5", user="dlemon", password="w00ti3s").open()
	address = AddressTable(dev)
	address.get(values=True)
	dev.close()
	#
	# sort through the arp_table dictionary and add the manufacture of the NIC's to the dictionary
	#
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
	#
	# Add the name of the address-book entry to the tempdict dictionary if it exists on the SRX
	#
	KNOWN_AENTRIES = {}
	KNOWN_AENTRIES = get_srx_address(address, arp_table)
	for mac, values in tempdict.items():
		if values[1][1] in KNOWN_AENTRIES:
			newvalue = list(values[1])
			newvalue.append(KNOWN_AENTRIES[values[1][1]])
			newvalue = tuple(newvalue)
			values[1]=newvalue
			tempdict[mac]=values
		else:
			newvalue = list(values[1])
			newvalue.append("-----")
			newvalue = tuple(newvalue)
			values[1]=newvalue
			tempdict[mac]=values
	#
	# Return to the client HTTP session a rendered html page based off of details.html with the above data
	#
	return render_template('details.html', macdict=tempdict)
