#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs

XML_EXT = '.xml'
ENCODE_METHOD = 'utf-8'

class PascalVocWriter:

    def __init__(self, foldername, filename, imgSize,databaseSrc='Unknown', localImgPath=None):
        self.foldername = foldername
        self.filename = filename
        self.databaseSrc = databaseSrc
        self.imgSize = imgSize
        self.boxlist = []
        self.localImgPath = localImgPath
        self.verified = False

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())
        # minidom does not support UTF-8
        '''reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="\t", encoding=ENCODE_METHOD)'''

    def genXML(self):
        """
            Return XML root
        """
        # Check conditions
        if self.filename is None or \
                self.foldername is None or \
                self.imgSize is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', 'yes')

        folder = SubElement(top, 'folder')
        folder.text = self.foldername

        filename = SubElement(top, 'filename')
        filename.text = self.filename

        if self.localImgPath is not None:
            localImgPath = SubElement(top, 'path')
            localImgPath.text = self.localImgPath

        source = SubElement(top, 'source')
        database = SubElement(source, 'database')
        database.text = self.databaseSrc

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        width.text = str(self.imgSize[1])
        height.text = str(self.imgSize[0])
        if len(self.imgSize) == 3:
            depth.text = str(self.imgSize[2])
        else:
            depth.text = '1'

        segmented = SubElement(top, 'segmented')
        segmented.text = '0'
        return top

    def addBndBox(self, xmin, ymin, xmax, ymax, name, difficult):
        bndbox = {'xmin': xmin, 'ymin': ymin, 'xmax': xmax, 'ymax': ymax}
        bndbox['name'] = name
        bndbox['difficult'] = difficult
        bndbox['type'] = 'bndbox'
        self.boxlist.append(bndbox)

    def addCircle(self, cx, cy, r, name, difficult):
        circle = {'cx': cx, 'cy': cy, 'r': r}
        circle['name'] = name
        circle['difficult'] = difficult
        circle['type'] = 'circle'
        self.boxlist.append(circle)

    def appendObjects(self, top):
        for each_object in self.boxlist:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            try:
                name.text = unicode(each_object['name'])
            except NameError:
                # Py3: NameError: name 'unicode' is not defined
                name.text = each_object['name']
            pose = SubElement(object_item, 'pose')
            pose.text = "Unspecified"
            truncated = SubElement(object_item, 'truncated')
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str( bool(each_object['difficult']) & 1 )

            if each_object['type'] == 'bndbox':
                if int(each_object['ymax']) == int(self.imgSize[0]) or (int(each_object['ymin'])== 1):
                    truncated.text = "1" # max == height or min
                elif (int(each_object['xmax'])==int(self.imgSize[1])) or (int(each_object['xmin'])== 1):
                    truncated.text = "1" # max == width or min
                else:
                    truncated.text = "0"
                bndbox = SubElement(object_item, 'bndbox')
                xmin = SubElement(bndbox, 'xmin')
                xmin.text = str(each_object['xmin'])
                ymin = SubElement(bndbox, 'ymin')
                ymin.text = str(each_object['ymin'])
                xmax = SubElement(bndbox, 'xmax')
                xmax.text = str(each_object['xmax'])
                ymax = SubElement(bndbox, 'ymax')
                ymax.text = str(each_object['ymax'])
            elif each_object['type'] == 'circle':
                if int(each_object['cy'])+int(each_object['r']) == int(self.imgSize[0]) or (int(each_object['cy'])-int(each_object['r']) == 1):
                    truncated.text = "1" # max == height or min
                elif (int(each_object['cx'])+int(each_object['r'])==int(self.imgSize[1])) or (int(each_object['cx'])-int(each_object['r']) == 1):
                    truncated.text = "1" # max == width or min
                else:
                    truncated.text = "0"
                circle = SubElement(object_item, 'circle')
                cx = SubElement(circle, 'cx')
                cx.text = str(each_object['cx'])
                cy = SubElement(circle, 'cy')
                cy.text = str(each_object['cy'])
                r = SubElement(circle, 'r')
                r.text = str(each_object['r'])

    def save(self, targetFile=None):
        root = self.genXML()
        self.appendObjects(root)
        out_file = None
        if targetFile is None:
            out_file = codecs.open(
                self.filename + XML_EXT, 'w', encoding=ENCODE_METHOD)
        else:
            out_file = codecs.open(targetFile, 'w', encoding=ENCODE_METHOD)

        prettifyResult = self.prettify(root)
        out_file.write(prettifyResult.decode('utf8'))
        out_file.close()


class PascalVocReader:

    def __init__(self, filepath):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.filepath = filepath
        self.verified = False
        try:
            #self.parseXML()

            # Add by michaelwan 2019-07-20
            self.parseXMLEx()
        except:
            pass

    def getShapes(self):
        return self.shapes

    # Add by michaelwan 2019-07-20
    def getObject(self, object_iter):
        objects = ['point','line','bndbox','polygon','circle']
        for object in objects:
            obj = object_iter.find(object)
            label = object_iter.find('name').text if obj is not None else None
            difficult = bool(int(object_iter.find('difficult').text)) if obj is not None else False
            if obj is not None:
                return obj, label, difficult 
        return None, None, False

    # Add by michaelwan 2019-07-20
    def getPoints(self, obj):
        object_type = obj.tag
        if object_type == 'point':
            x1 = int(obj.find('x1').text)
            y1 = int(obj.find('y1').text)
            points = [(x1, y1)]
        elif object_type == 'line':
            x1 = int(obj.find('x1').text)
            y1 = int(obj.find('y1').text)
            x2 = int(obj.find('x2').text)
            y2 = int(obj.find('y2').text)
            points = [(x1, y1), (x2, y2)]
        elif object_type == 'bndbox':
            xmin = int(obj.find('xmin').text)
            ymin = int(obj.find('ymin').text)
            xmax = int(obj.find('xmax').text)
            ymax = int(obj.find('ymax').text)
            points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        elif object_type == 'polygon':
            points = []
            c = len(list(obj)) / 2
            co_ords = [('x'+str(i), 'y'+str(i)) for i in range(1, c+1)]
            for (x, y) in co_ords:
                x_ord = int(obj.find(x).text)
                y_ord = int(obj.find(y).text)
                points.append((x_ord, y_ord))
        elif object_type == 'circle':
            cx = int(obj.find('cx').text)
            cy = int(obj.find('cy').text)
            r = int(obj.find('r').text)
            points = [(cx, cy), (r, r)]
        return object_type, points

    # Add by michaelwan 2019-07-20
    def addShapeEx(self, label, obj, difficult):
        object_type, points = self.getPoints(obj)
        self.shapes.append((label, object_type, points, None, None, difficult))

    # Add by michaelwan 2019-07-20
    def parseXMLEx(self):
        assert self.filepath.endswith(XML_EXT), "Unsupport file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xmltree = ElementTree.parse(self.filepath, parser=parser).getroot()
        filename = xmltree.find('filename').text
        try:
            verified = xmltree.attrib['verified']
            if verified == 'yes':
                self.verified = True
        except KeyError:
            self.verified = False

        for object_iter in xmltree.findall('object'):
            obj, label, difficult = self.getObject(object_iter)
            self.addShapeEx(label, obj, difficult)
        return True

    def addShape(self, label, bndbox, difficult):
        xmin = int(bndbox.find('xmin').text)
        ymin = int(bndbox.find('ymin').text)
        xmax = int(bndbox.find('xmax').text)
        ymax = int(bndbox.find('ymax').text)
        points = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        self.shapes.append((label, points, None, None, difficult))

    def parseXML(self):
        assert self.filepath.endswith(XML_EXT), "Unsupport file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xmltree = ElementTree.parse(self.filepath, parser=parser).getroot()
        filename = xmltree.find('filename').text
        try:
            verified = xmltree.attrib['verified']
            if verified == 'yes':
                self.verified = True
        except KeyError:
            self.verified = False

        for object_iter in xmltree.findall('object'):
            bndbox = object_iter.find("bndbox")
            label = object_iter.find('name').text
            # Add chris
            difficult = False
            if object_iter.find('difficult') is not None:
                difficult = bool(int(object_iter.find('difficult').text))
            self.addShape(label, bndbox, difficult)
        return True
