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
projectref = None

def scan(sourcename, servername, inputfile, outputfile):

	xsltversion = '2.0.0'
	sourcename = sourcename or 'ESP'
	servername = servername or 'ESPM'
	schema = 'schema-esp:/'
	schemaref = schema + '/' + sourcename
	serverref = schemaref + '/' + servername
	global repositoryref
	repositoryref = schema + '/' + sourcename + '/' + servername

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

	e = {'type': 'DI Repository', 'name': servername, 'tag': sourcename, 'desc': 'CA WA ESP Edition', 'ref': repositoryref}
	add2xml(model_xn, 'object', e)
	
	with open(inputfile, 'rb') as f:
		ls = f.readlines()
	i = 0
	while True:
		if i >= len(ls):
			break	
		found, i = read_event(ls, i)
		if found:
			continue
		found, i = read_job(ls, i)
		if found:
			continue
		i += 1
	#tree = ET.ElementTree(model_xn)
	#tree.write(outputfile)
	with open(outputfile, 'w') as f:
		f.write(minidom.parseString(ET.tostring(model_xn, 'utf-8')).toprettyxml(indent='\t'))
	
def read_job(ls, i):
	start_i = i
	while True:
		m = re.search('^\\s*/\\*|^\\s*$', ls[i])
		if not m:
			break
		i += 1		
	m = re.search('^\\s*APPL\\s+(.*?)(\\s|$)', ls[i])
	if not m:
		return False, i
	o = {'type': 'DI Job', 'name': m.group(1), 'desc': '', 'notes': ''}
	o['ref'] = projectref + '/' + m.group(1)
	o['pref'] = projectref
	last_i = i
	for i in range(start_i, last_i):
		m = re.search('^\\s*/\\*', ls[i])
		if m:
			o['desc'] = o['desc'] + ls[i]
	i = last_i
	while True:
		i += 1
		if i >= len(ls):
			break
		m = re.search('^\\s{4}|^\s*$', ls[i])
		if m:
			continue
		m = re.search('^\\s*(NOTIFY|OPTIONS|RESOURCE|EXITCODE)\\s', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			continue
		break
	add2xml(model_xn, 'object', o)
	return True, i

def read_event(ls, i):
	m = re.search('^\\s*EVENT\\s', ls[i])
	if not m:
		return False, i
	o = {'type': 'DI Project'}
	m = re.search('\\sSYSTEM\\((.*?)\\)', ls[i])
	if m:
		o['name'] = m.group(1)
		global projectref
		projectref = repositoryref + '/' + m.group(1)
		o['ref'] = projectref
		add2xml(model_xn, 'object', o)
	o = {'type': 'DI Event', 'ptype': 'DI Project', 'pref': projectref, 'notes': '', 'desc': ''}
	m = re.search('\\sID\\((.*?)\\)', ls[i])
	if m:
		o['name'] = m.group(1)
		eventref = repositoryref + '/' + m.group(1)
		o['ref'] = eventref
	m = re.search('\\sOWNER\\((.*?)\\)', ls[i])
	if m:
		p = {'type': 'Owner', 'ptype': 'DI Event', 'pref': o['ref']}
		p['value'] = m.group(1)
		add2xml(model_xn, 'property', p)
	
	while True:
		i += 1
		if i >= len(ls):
			break
		m = re.search('^\\s{4}|^\s*$', ls[i])
		if m:
			continue
		m = re.search('^\\s*CALENDAR\\s', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*SYMLIB\\s', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*INVOKE\\s+(.*)$', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			o['contents'] = m.group(1)
			continue
		m = re.search('^\\s*SCHEDULE\\s+(.*)$', ls[i])
		if m:
			p = {'type': 'Schedule', 'ptype': 'DI Event', 'pref': o['ref']}
			p['value'] = m.group(1)
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*COM\\s+(.*)$', ls[i])
		if m:
			o['desc'] = o['desc'] + ls[i]
			continue
		break
	add2xml(model_xn, 'object', o)
	return True, i

def add2xml(parent_xn, xn_name, e):
	xn = ET.SubElement(parent_xn, xn_name)
	for k,v in e.iteritems():
		if v:
			ET.SubElement(xn, k).text = v
	return

scan(sourcename=None, servername=None , inputfile='./_spec/IDP1COD$.txt', outputfile='./_spec/test2.txt')

