from jnpr.junos.op.arp import ArpTable
from jnpr.junos import Device
from pprint import pprint
from flask import render_template
from app import app
from collections import defaultdict
from myTables.srxadddresses import AddressTable
import collections
import os.path
import requests
import json

#
# method to convert unicode dictionary to utf-8
#
def convert(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data
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
	# Read the only tempdict from the file.  Used to limit mac api queries and save time
	# Then converts the JSON/Unicode dictionary to utf-8 so we can use it in the below
	# for loop to be able to match dictionaryies
	#
	oldtempdict=json.load(open('tempdict.txt'))
	oldtempdict=convert(oldtempdict)
	#
	# Sort through the arp_table dictionary and add the manufacture of the NIC's to the dictionary
	# This also checks if the mac isn't already resolved via the MAC OUI function then add old entry
	#
	tempdict = {}
	for mac, details in arp_table.items():
		if mac not in oldtempdict:
			macs = list(details[2])
			macs.append(get_vendor(mac))
			macs = tuple(macs)
			details[2]=macs
			tempdict[mac]=details
		else:
			tempdict[mac]=oldtempdict[mac]
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
	# Write tempdict to a file so next time app loads it uses this to populate tempdict
	#
	with open('tempdict.txt', 'w') as file:
		file.write(json.dumps(tempdict))	
	#
	# Return to the client HTTP session a rendered html page based off of details.html with the above data
	#
	return render_template('details.html', macdict=tempdict)
