#!/usr/bin/env python
# encoding: utf-8

import os
import struct
import xml.etree.cElementTree as ET
import re
from collections import namedtuple
from xml.dom import minidom

repositoryref = None
model_xn = None

def scan(sourcename, servername, inputfile, outputfile):

	xsltversion = '2.0.0'
	sourcename = sourcename or "ESP"
	servername = servername or "ESPM"
	schema = "schema-esp:/"
	schemaref = schema + '/' + sourcename
	serverref = schemaref + '/' + servername

	global model_xn
	model_xn = ET.Element('model')
	model_xn.set('name', 'DataIntegration')
	model_xn.set('schemaref', schemaref)
	model_xn.set('xslt-version', xsltversion)
	model_xn.set('implicit-types', 'yes')

	#object = namedtuple('object', 'type ptype name tag ext desc contents notes order version pdate pname edate ename ref pref')
	#property = namedtuple('property', 'type ptype name value vref ref pref')
	#relation = namedtuple('relation', 'type rtype reltype desc contents ref relref')
	#scheduletype = {'RUN': 'Schedule', 'NORUN': 'Unschedule'}

	global repositoryref
	repositoryref = schema + sourcename + servername
	e = {'type': 'DI Repository', 'name': servername, 'tag': sourcename, 'desc': 'CA WA ESP Edition', 'ref': repositoryref}
	add2xml(model_xn, 'object', e)

	f = open(inputfile, 'rb')
	l = f.readline()
	while l:
		if re.search('^\\s*\\*', l):
			l = f.readline()
			continue
		found, l = read_event(f, l)
		if found:
			continue
		l = f.readline()
	tree = ET.ElementTree(model_xn)
	tree.write(outputfile)
	
def read_event(f, l):
	m = re.search('^\\s*EVENT\\s', l)
	if not m:
		return False, l
	o = {'type': 'DI Project'}
	m = re.search('\\sSYSTEM\\((.*?)\\)', l)
	if m:
		o['name'] = m.group(1)
		projectref = repositoryref + m.group(1)
		o['ref'] = projectref
		add2xml(model_xn, 'object', o)
	o = {'type': 'DI Event', 'ptype': 'DI Project', 'pref': projectref}
	m = re.search('\\sID\\((.*?)\\)', l)
	if m:
		o['name'] = m.group(1)
		eventref = repositoryref + m.group(1)
		o['ref'] = eventref
	m = re.search('\\sOWNER\\((.*?)\\)', l)
	if m:
		p = {'type': 'Owner', 'ptype': 'DI Event', 'pref': o['ref']}
		p['value'] = m.group(1)
		add2xml(model_xn, 'property', p)
	while True:
		l = f.readline()
		if not l:
			break
		m = re.search('^\\s*CALENDAR\\s', l)
		if m:
			o['notes'] = o.notes + l + '\r\n'
			continue
		m = re.search('^\\s*SYMLIB\\s', l)
		if m:
			o['notes'] = o['notes'] + l + '\r\n'
			continue
		m = re.search('^\\s*INVOKE\\s+(.*)$', l)
		if m:
			o['notes'] = o['notes'] + l + '\r\n'
			o['contents'] = m.group(1)
			continue
		m = re.search('^\\s*SCHEDULE\\s+(.*)$', l)
		if m:
			p = {'type': 'Schedule', 'ptype': 'DI Event', 'pref': o['ref']}
			p['value'] = m.group(1)
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*COM\\s+(.*)$', l)
		if m:
			o['desc'] = o['desc'] + l + '\r\n'
			continue			
		break
	add2xml(model_xn, 'object', o)
	return True, l

def add2xml(parent_xn, xn_name, e):
	xn = ET.SubElement(parent_xn, xn_name)
	for k,v in e.iteritems():
		if v:
			ET.SubElement(xn, k).text = v
	return

scan(sourcename=None, servername=None , inputfile='./_spec/IDP1COD$.txt', outputfile='./_spec/test2.txt')

