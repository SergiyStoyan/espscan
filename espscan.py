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
jobref = None

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

	e = {'type': 'DI Repository', 'name': servername, 'tag': sourcename, 'desc': 'CA WA ESP Edition', 'ref': repositoryref}
	add2xml(model_xn, 'object', e)
	
	with open(inputfile, 'rb') as f:
		ls = f.readlines()
	i = 0
	while True:
		if i >= len(ls):
			break	
		found, i = read_EVENT(ls, i)
		if found:
			continue
		found, i = read_APPL(ls, i)
		if found:
			continue
		found, i = read_JOB(ls, i)
		if found:
			continue
		found, i = read_FILE_TRIGGER(ls, i)
		if found:
			continue
		i += 1
	for p_xn in model_xn.findall('property'):
		v = p_xn.find('pref')
		if v != None:
			continue
		if p_xn.find('type').text != 'Next':
			continue
		#print '1-' + ET.tostring(p_xn)
		p_vref = re.sub('^.*/', '', p_xn.find('vref').text)
		for o_xn in model_xn.findall('object'):
			if o_xn.find('name').text == p_vref:
				pref_xn = ET.SubElement(p_xn, 'pref')
				pref_xn.text = o_xn.find('ref').text
				#print '2-' + ET.tostring(p_xn)
				break
	#tree = ET.ElementTree(model_xn)
	#tree.write(outputfile)
	with open(outputfile, 'w') as f:
		f.write(minidom.parseString(ET.tostring(model_xn, 'utf-8')).toprettyxml(indent='\t'))

def read_FILE_TRIGGER(ls, i):
	start_i = i
	while True:
		m = re.search('^\\s*/\\*|^\\s*$', ls[i])
		if not m:
			break
		i += 1		
	m = re.search('^\\s*FILE_TRIGGER\\s+(.*)', ls[i])
	if not m:
		return False, i
	o = {'type': 'DI Step', 'name': m.group(1), 'ext': 'FILE_TRIGGER', 'desc': '', 'notes': ''}
	stepref = jobref + '/' + m.group(1)
	o['ref'] = stepref
	o['pref'] = jobref
	for j in range (start_i, i):
		m = re.search('^\\s*/\\*', ls[j])
		if m:
			o['desc'] = o['desc'] + ls[j]		
	while True:
		i += 1
		if i >= len(ls):
			break
		m = re.search('^\\s*/\\*', ls[i])
		if m:
			o['desc'] = o['desc'] + ls[i]		
			continue
		m = re.search('^\\s*FILENAME\\s+(.*)', ls[i])
		if m:
			o['contents'] = m.group(1)
			continue
		m = re.search('^\\s*(EARLYSUB|AFTER)\\s+(.*)', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]		
			continue
		m = re.search('^\\s*RELEASE\\s+ADD\\((.*)\\)', ls[i])
		if m:
			p = {'type': 'Next', 'ptype': 'DI Step', 'pref': o['ref']}
			p['vref'] = jobref + '/' + m.group(1)
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*AGENT\\s+(.*)\\s', ls[i])
		if m:
			p = {'type': 'Location', 'ptype': 'DI Step', 'pref': o['ref'], 'value': m.group(1)}
			add2xml(model_xn, 'property', p)
			continue			
		m = re.search('^\\s*ENDJOB\\s', ls[i])
		if m:
			i += 1
			break
		m = re.search('^\\s*RUN\\s+REF\\s+(.*)\\s', ls[i])
		if m:
			p = {'type': 'Next', 'ptype': 'DI Step', 'pref': None, 'vref': jobref + '/' + m.group(1)}
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*AFTER\\s+(.*)\\s', ls[i])
		if m:
			p = {'type': 'Next', 'ptype': 'DI Step', 'pref': None, 'vref': jobref + '/' + m.group(1)}
			add2xml(model_xn, 'property', p)
			continue		
	add2xml(model_xn, 'object', o)
	return True, i
		
def read_JOB(ls, i):
	start_i = i
	while True:
		m = re.search('^\\s*/\\*|^\\s*$', ls[i])
		if not m:
			break
		i += 1		
	m = re.search('^\\s*(NT_JOB|LINUX_JOB|AIX_JOB)\\s+(.*?)(\\s|$)', ls[i])
	if not m:
		return False, i
	o = {'type': 'DI Step', 'name': m.group(2), 'desc': '', 'notes': ''}
	o['ext'] = m.group(1)
	o['ref'] = jobref + '/' + m.group(2)
	o['pref'] = jobref
	m = re.search('\\s*LONGNAME\\((.*)\\)', ls[i])
	if m:
		o['tag'] = m.group(1)
	for j in range (start_i, i):
		m = re.search('^\\s*/\\*', ls[j])
		if m:
			o['desc'] = o['desc'] + ls[j]		
	schedule_p = {'type': 'Schedule', 'ptype': 'DI Step', 'pref': o['ref'], 'value': ''}
	while True:
		i += 1
		if i >= len(ls):
			break
		m = re.search('^\\s*/\\*', ls[i])
		if m:
			o['desc'] = o['desc'] + ls[i]		
			continue
		m = re.search('^\\s*CMDNAME\\s.*', ls[i])
		if m:
			o['CMDNAME'] = m.group(0)
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*ARGS\\s.*', ls[i])
		if m:
			o['ARGS'] = m.group(0)
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*SCRIPTNAME\\s.*', ls[i])
		if m:
			o['SCRIPTNAME'] = m.group(0)
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*(DUEOUT|EARLYSUB)\\s', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*(RUN|NORUN)\\s', ls[i])
		if m:
			schedule_p['value'] = schedule_p['value'] + ls[i]
			continue
		m = re.search('^\\s*RESOURCE ADD\\((.*)\\)', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*ENVAR\\s+(.*)', ls[i])
		if m:
			o['notes'] = o['notes'] + ls[i]
			continue
		m = re.search('^\\s*AGENT\\s+(.*)\\s', ls[i])
		if m:
			p = {'type': 'Location', 'ptype': 'DI Step', 'pref': o['ref'], 'value': m.group(1)}
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*ENDJOB\\s', ls[i])
		if m:
			i += 1
			break
		m = re.search('^\\s*RELEASE\\s+ADD\\((.*)\\)', ls[i])
		if m:
			p = {'type': 'Next', 'ptype': 'DI Step', 'pref': o['ref']}
			p['vref'] = jobref + '/' + m.group(1)
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*RUN\\s+REF\\s+(.*)\\s', ls[i])
		if m:
			p = {'type': 'Next', 'ptype': 'DI Step', 'pref': None, 'vref': jobref + '/' + m.group(1)}
			add2xml(model_xn, 'property', p)
			continue
		m = re.search('^\\s*AFTER\\s+(.*)\\s', ls[i])
		if m:
			p = {'type': 'Next', 'ptype': 'DI Step', 'pref': None, 'vref': jobref + '/' + m.group(1)}
			add2xml(model_xn, 'property', p)
			continue		
#		m = re.search('^\\s*TEMPLATE\\s+(.*)', ls[i])
#		if m:
#			p = {'type': 'Template', 'ptype': 'DI Step', 'pref': o['ref']}
#			p['value'] = m.group(1)
#			add2xml(model_xn, 'property', p)
#			continue
	o['contents'] = []
	if 'CMDNAME' in o:
		if 'ARGS' in o:
			o['contents'].append(o['CMDNAME'] + ' ' + o['ARGS'])
		else:
			o['contents'].append(o['CMDNAME'])
		del o['CMDNAME'] 
	if 'SCRIPTNAME' in o:
		if 'ARGS' in o:
			o['contents'].append(o['SCRIPTNAME'] + ' ' + o['ARGS'])
		else:
			o['contents'].append(o['SCRIPTNAME'])
		del o['SCRIPTNAME']		
	if 'ARGS' in o:
		del o['ARGS']	
	add2xml(model_xn, 'object', o)	
	add2xml(model_xn, 'property', schedule_p)
	return True, i

def read_APPL(ls, i):
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
	global jobref
	jobref = projectref + '/' + m.group(1)
	o['ref'] = jobref
	o['pref'] = projectref
	for j in range (start_i, i):
		m = re.search('^\\s*/\\*', ls[j])
		if m:
			o['desc'] = o['desc'] + ls[j]		
	while True:
		i += 1
		if i >= len(ls):
			break
		m = re.search('^\\s*/\\*', ls[i])
		if m:
			o['desc'] = o['desc'] + ls[i]		
			continue
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
	
def read_EVENT(ls, i):
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
			if isinstance(v, list):
				for v_ in v:
					ET.SubElement(xn, k).text = v_.strip()
			else:
				ET.SubElement(xn, k).text = v.strip()
	return

scan(sourcename=None, servername=None , inputfile='./_spec/IDP1COD$.txt', outputfile='./_spec/test2.txt')

