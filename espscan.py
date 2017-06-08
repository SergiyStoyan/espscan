#!/usr/bin/env python
# encoding: utf-8

import os
import struct
import xml.etree.ElementTree as ET
#import re
from collections import namedtuple
from xml.dom import minidom

""" 
annotation
    CA Workload Automation (ESP Edition) scanner. 
    Revision: V1.2.1
    Features:
        Supports MMX ProcessControl metamodel
        Utilizes MMXML transformation format/pg-store-mmxml storage agent.

    Object mappings:
EVENT
APPL
"NT_JOB
LINUX_JOB 
AIX_JOB"
FILE_TRIGGER
@@ENDTPL
<variable> = 

	CLANG commands:
CALENDAR
SYMLIB
INVOKE
SCHEDULE
COM
NOTIFY
OPTIONS
RESOURCE
EXITCODE
LONGNAME
CMDNAME, ARGS
SCRIPTNAME, ARGS
CMDNAME, SCRIPTNAME, ARGS
DUEOUT, EARLYSUB
RUN, NORUN
RELEASE.. ADD
RUN REF
AFTER
RESOURCE ADD
AGENT
ENVAR
IF
SUBAPPL
FILENAME
EARLYSUB, AFTER
RELEASE..ADD
RUN REF
AFTER
AGENT

	
	

    Parameters:
        sourcename: Unique ID assigned in dLineage Administration UI 
        servername: Server name referring a file/application server with xml files.
"""

def scan(sourcename, servername, inputfile, outputfile):

    global object_columns, property_columns, relation_columns
    global model

#    sourcename = "QV"
#    servername = 'QvServer'
#    filepath = "/Project/QlikView/Ramesh"
#    filename = "GoSales Revenue by Go Subsidary.qvw"

    xsltversion = '2.0.0'
    sourcename = sourcename or "ESP"
    servername = servername or "ESPM"
    schemaname = "schema-esp:/"
    schemaref = schemaname + '/' + sourcename
    serverref = schemaref + '/' + servername


    object_columns = namedtuple('object_columns', 'type ptype name tag ext desc contents notes order version pdate pname edate ename ref pref')
    property_columns = namedtuple('property_columns', 'type ptype name value vref ref pref')
    relation_columns = namedtuple('relation_columns', 'type rtype reltype desc contents ref relref')
    scheduletype = {'RUN': 'Schedule', 'NORUN': 'Unschedule'}

    try:
        with open(inputfile, 'rb') as fi:

            model = ET.Element('model')
            model.set('name', 'ProcessControl')
            model.set('schemaref', schemaref)
            model.set('xslt-version', xsltversion) 
            model.set('implicit-types', 'yes')
            o = object_columns("PC Framework", "", servername, sourcename, "CA Workload Automation (ESP Edition)", "", "", "", "", "", "", "", "", "", serverref, "") 

            comment = "" 
            state = ""
            while True:
                line = fi.readline()
                if not line: break
                line = line.strip()
                if line == "": continue
                if line[:2] == "/*":
                    comment += line + '\n'
                    continue 
                if line[-1:] in ['+', '-']:
                    line = line[:-1] + fi.readline().strip()
                cmd = line.split()[0]    
                arg = line.split()
                if len(arg) > 1:
                    args = line.split(' ', 1)[1]
                if cmd in ("EVENT", "APPL", "NT_JOB", "FILE_TRIGGER"):
                    state = cmd
                    ogen(o)

                if state == "EVENT":
                    if cmd == "EVENT":
                        event = line2dict(line)
                        eventref = serverref + '/' + event['ID'] 
                        o = object_columns("PC Event", "PC Framework", event['ID'], "", "", "", "", "", "", "", "", "", "", "", eventref, serverref) 
                        if comment != "":
                            o = o._replace(desc = comment)
                            comment = ""
                        p = property_columns("Owner", "PC Event", "Owner", event['OWNER'], "", "", eventref)
                        pgen(p)
                    if cmd in ["CALENDAR", "SYMLIB", "INVOKE"]:
                        o = o._replace(notes = o.notes + line + '\n')
                    if cmd == "INVOKE":
                        o = o._replace(contents = args)
                    if cmd == "SCHEDULE":
                        p = property_columns("Schedule", "PC Event", "Schedule", args, "", "", eventref)
                        pgen(p)
                    if cmd == "":
# ??? to be determined how
                        pass         

                if state == "APPL":
                    if cmd == "APPL":
                        applref = serverref + '/' + arg[1] 
                        o = object_columns("PC Job", "PC Framework", arg[1], "", "", "", "", "", "", "", "", "", "", "", applref, serverref) 
                        if comment != "":
                            o = o._replace(desc = comment)
                            comment = ""
# ??? NOTIFY

                if state == "NT_JOB":
                    if cmd == "NT_JOB":
                        jobref = serverref + '/' + arg[1]
                        o = object_columns("PC Process", "PC Job", arg[1], "", state, "", "", "", "", "", "", "", "", "", jobref, applref) 
                        if comment != "":
                            o = o._replace(desc = comment)
                            comment = ""
                        if len(arg) > 2:
                            longname = line2dict(arg[2])
                            o = o._replace(tag = longname['LONGNAME'].strip("'"))
                    if cmd == "CMDNAME":
                        o = o._replace(contents = args)
                    if cmd == "ARGS":
                        o = o._replace(contents = o.contents + ' ' + args)
                    if cmd in ["DUEOUT", "EARLYSUB"]:
                        o = o._replace(notes = o.notes + line + '\n')
                    if cmd == "RUN" and arg[1] == "REF":
                        o = o._replace(notes = o.notes + line + '\n')

                    if cmd in ["RUN", "NORUN"] and arg[1] != "REF":
                        p = property_columns("Schedule", "PC Process", scheduletype[cmd], args, "", "", jobref)
                        pgen(p)
                    if cmd == "AGENT":
                        p = property_columns("Location", "PC Process", "Location", args, "", "", jobref)
                        pgen(p)
                    if cmd == "RELEASE":
                        if "ADD(" in args:
                            for next in args[args.index("("):].strip('(').strip(')').split():
                                nextref = serverref + '/' + next
                                p = property_columns("Next", "PC Process", "Next", next, nextref, "", jobref)
                                pgen(p)

# ??? ENVAR, NOTIFY, IF..RUN, IF..RELEASE

                if state == "FILE_TRIGGER":
                    if cmd == "FILE_TRIGGER":
                        jobref = serverref + '/' + arg[1]
                        o = object_columns("PC Process", "PC Job", arg[1], "", state, "", "", "", "", "", "", "", "", "", jobref, applref) 
                        if comment != "":
                            o = o._replace(desc = comment)
                            comment = ""
                    if cmd == "FILENAME":
                        o = o._replace(contents = arg[1].strip("'"))
                    if cmd in ["EARLYSUB", "AFTER"]:
                        o = o._replace(notes = o.notes + line + '\n')
                    if cmd == "RUN" and arg[1] == "REF":
                        o = o._replace(notes = o.notes + line + '\n')
                    if cmd == "AGENT":
                        p = property_columns("Location", "PC Process", "Location", args, "", "", jobref)
                        pgen(p)
                    if cmd == "RELEASE":
                        if "ADD(" in args:
                            for next in args[args.index("("):].strip('(').strip(')').split():
                                nextref = serverref + '/' + next
                                p = property_columns("Next", "PC Process", "Next", next, nextref, "", jobref)
                                pgen(p)
                    if cmd == "AFTER":
                        nextref = serverref + '/' + arg[1]
                        p = property_columns("Next", "PC Process", "Next", o.name, jobref, "", nextref)
                        pgen(p)

# ??? ENDJOB  

                if cmd == "TEMPLATE":
                    template = line

                if cmd == "@@ENDTPL":
                    o = o._replace(notes = o.notes + template + '\n')

            ogen(o)

        rough_string = ET.tostring(model, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        try:    
            with open(outputfile, 'w+') as fo:
                fo.write(reparsed.toprettyxml(indent="  "))
        except IOError as error:
            print >> sys.stderr, "Unable to write to %s: %s (error %d)" % (error.filename, error.strerror, error.errno)
            return 1
    except IOError as error:
        print >> sys.stderr, "Unable to read from %s: %s (error %d)" % (error.filename, error.strerror, error.errno)
        return 1
    return 0

def line2dict(line):
    d = {}
    s = line.split()
    for s1 in s:
        if '(' in s1:
            d[s1[:s1.index("(")]] = s1[s1.index("("):].strip('(').strip(')')
    return d

def ogen(o):
    object = ET.SubElement(model, 'object')
    for f in (object_columns._fields):
        if getattr(o, f) != "":
            ochild = ET.SubElement(object, f)
            ochild.text = getattr(o, f)
    return

def pgen(p):
    property = ET.SubElement(model, 'property')
    for f in (property_columns._fields):
        if getattr(p, f) != "":
            pchild = ET.SubElement(property, f)
            pchild.text = getattr(p, f)
    return

def rgen(r):
    relation = ET.SubElement(model, 'relation')
    for f in (relation_columns._fields):
        if getattr(r, f) != "":
            rchild = ET.SubElement(relation, f)
            rchild.text = getattr(r, f)
    return



scan(sourcename=None, servername=None , inputfile='IDP1COD$.txt', outputfile='test.txt')	
	