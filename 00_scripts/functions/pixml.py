#!/usr/bin/python
# -*- coding: utf-8 -*-
# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

from xml.etree import ElementTree

import argparse
import copy
import datetime
import numpy as np
import re
import os
import glob

TAG_START = 'startDate'
TAG_END = 'endDate'
TAG_STEP = 'timeStep'
TAG_MISSVAL = 'missVal'
TAG_PARAMETER_ID = 'parameterId'


class Series(object):
    """
    like etree, but:
        events stored as numpy array
        start, stop and step stored as python objects
        closing and opening tags and timezone included.
    """

    def __init__(self, tree, start=None, end=None,
                 step=None, ma=None, missval=None):
        """
        If start, stop or step are None, their values are taken from
        the tree representing the timeseries without events.

        If ma is None, initialize it with nodata from start, stop and step.
        """
        self.tree = tree

        if start is None:
            self.start = self._get_tree_value(TAG_START)
        else:
            self.start = start
            
        if end is None:
            self.end = self._get_tree_value(TAG_END)
        else:
            self.end = end
        
        if step is None:
            self.step = self._get_tree_value(TAG_STEP)
        else:
            self.step = step

        if missval is None:
            self.missval = self._get_tree_value(TAG_MISSVAL)
        else:
            self.missval = missval

        if ma is None:
            size = int(
                (self.end - self.start).total_seconds() /
                self.step.total_seconds()
            ) + 1
            self.ma = np.ma.array(np.zeros(size), mask=True)
        else:
            self.ma = ma
            
    def __len__(self):
        """ Return length of timeseries if complete. """
        return self.ma.size

    def __getitem__(self, key):
        """
        self[datetime.datetime] -> value
        self[0] -> {datetime, value}
        """
        if isinstance(key, datetime.datetime):
            return self.ma[self._index(key)]
        else:
            return self.ma[key]

    def __setitem__(self, key, value):
        """
        self[datetime.datetime] = value, or
        self[index] = value
        """
        if isinstance(key, datetime.datetime):
            self.ma[self._index(key)] = value
        else:
            self.ma[key] = value

    def __iter__(self):
        for i in range(len(self)):
            yield self._datetime_from_index(i), self[i]

    def _index(self, dt):
        span = dt - self.start
        step = self.step
        return int(span.total_seconds() / step.total_seconds())

    def _datetime_from_index(self, index):
        return self.start + index * self.step

    # Methods to facilitate modifying tree elements
    def _get_tree_element(self, tag):
        """ Get attrib of element with tag in tree. """
        for element in self.tree.iter():
            if element.tag.endswith(tag):
                return element

    def _set_tree_value(self, tag, value):
        """ Set element properties based on tag. """
        element = self._get_tree_element(tag)
        if tag in (TAG_START, TAG_END):
            element.attrib['date'] = value.strftime('%Y-%m-%d')
            element.attrib['time'] = value.strftime('%H:%M:%S')
        elif tag == TAG_STEP:
            element.attrib['unit'] = 'second'
            element.attrib['multiplier'] = str(int(value.total_seconds()))
        elif tag == TAG_PARAMETER_ID:
            element.text = value
        elif tag == TAG_MISSVAL:
            element.text = str(value)
            
    def _get_tree_value(self, tag):
        """ Get element properties based on tag. """
        element = self._get_tree_element(tag)
        if tag in (TAG_START, TAG_END):
            return datetime.datetime.strptime('{date} {time}'.format(
                date=element.attrib['date'], time=element.attrib['time'],
            ), '%Y-%m-%d %H:%M:%S')
        elif tag == TAG_STEP:
            td_kwargs = {
                '{}s'.format(element.attrib['unit']):
                    int(element.attrib['multiplier']),
            }
            return datetime.timedelta(**td_kwargs)
        elif tag == TAG_PARAMETER_ID:
            return element.text
        elif tag == TAG_MISSVAL:
            try:
                return float(element.text)
            except ValueError:
                return element.text

    # Keep tree in sync with the start attribute
    def _get_start(self):
        return self._start

    def _set_start(self, start):
        self._start = start
        self._set_tree_value(TAG_START, start)

    start = property(_get_start, _set_start)

    # Keep tree in sync with the end attribute
    def _get_end(self):
        return self._end

    def _set_end(self, end):
        self._end = end
        self._set_tree_value(TAG_END, end)

    end = property(_get_end, _set_end)

    # Keep tree in sync with the step attribute
    def _get_step(self):
        return self._step

    def _set_step(self, step):
        self._step = step
        self._set_tree_value(TAG_STEP, step)

    step = property(_get_step, _set_step)
    
    # Keep tree in sync with the missval attribute
    def _get_missval(self):
        return self._missval

    def _set_missval(self, missval):
        self._missval = missval
        self._set_tree_value(TAG_MISSVAL, missval)

    missval = property(_get_missval, _set_missval)


class SeriesReader(object):

    def __init__(self, xml_input_path):
        self.xml_input_path = xml_input_path

        bin_input_path =  re.sub('xml$','bin', xml_input_path)
        if os.path.exists(bin_input_path):
            self.bin_input_path = bin_input_path
            self.binary = True
        else:
            self.bin_input_path = None
            self.binary = False

    def _datetime_from_elem(self, elem):
        """ Return python datetime object. """
        return datetime.datetime.strptime(
            '{date} {time}'.format(
                date=elem.attrib['date'],
                time=elem.attrib['time'],
            ),
            '%Y-%m-%d %H:%M:%S',
        )

    def _set_values(self, series, inputfile):
        """ Set series values from binary inputfile. """
        values = np.fromfile(
            inputfile,
            dtype=np.float32,
            count=len(series),
        )

        try:
            missval = float(series.missval)
        except ValueError:
            missval = None
        
        if missval is None:
            mask = False
            fill_value=-999
        else:
            mask = np.equal(values, series.missval),
            fill_value = missval
            
        series.ma[:] = np.ma.array(
            values,
            mask=mask,
            fill_value=fill_value,
        )

    def read(self):
        """
        Returns a generator of series objects.

        As etree parses the tree, it keeps an internal tree that is not
        necessarily in sync with the events returned by iterparse.

        Therefore we keep a copy of selected elements of the tree that
        is used to instantiate the series.
        """
        iterator = iter(ElementTree.iterparse(
            self.xml_input_path, events=('start', 'end'),
        ))
        if self.binary:
            bin_input_file = open(self.bin_input_path, 'rb')


        # Flake8 does not like the order of the assignments below.
        result = None
        series = None
        wildseries = None
        tree = None
        wildtree = None

        for parse_event, elem in iterator:
            # At the end of an event, write it to current result
            if parse_event == 'end' and elem.tag.endswith('event'):
                dt = self._datetime_from_elem(elem)
                value = float(elem.attrib['value'])
                if value != result.missval:
                    result[dt] = value
                wildseries.remove(elem)
            # Instantiate a new result when the header is complete
            elif parse_event == 'end' and elem.tag.endswith('header'):
                series.append(copy.deepcopy(elem))
                result = Series(tree=copy.deepcopy(tree))
                if self.binary:
                    self._set_values(series=result, inputfile=bin_input_file)
            # After the series is completed, yield the result object.
            elif parse_event == 'end' and elem.tag.endswith('series'):
                yield result
                wildtree.remove(wildseries)
                tree.remove(series)
            # New series. Copy to series, remove unwanted children.
            elif parse_event == 'start' and elem.tag.endswith('series'):
                wildseries = elem
                series = copy.deepcopy(elem)
                tree.append(series)
                map(series.remove, series.getchildren()[:])
            # Timezone should be in the copy of the tree
            elif parse_event == 'end' and elem.tag.endswith('timeZone'):
                tree.append(copy.deepcopy(elem))
            elif parse_event == 'start' and elem.tag.endswith('TimeSeries'):
            # New timeseries, make a copy and keep that copy nice and tidy.
                wildtree = elem
                tree = copy.deepcopy(elem)
                map(tree.remove, tree.getchildren()[:])

        if self.binary:
            bin_input_file.close()


class SeriesWriter(object):

    def __init__(self, xml_output_path, binary=False):
        self.initialized = False
        self.binary = binary

        self.xml_output_file = open(xml_output_path, 'w')
        self.bin_output_path =  re.sub('xml$','bin', xml_output_path)

    def _register_namespace(self, series):
        """ Register default namespace for etree output. """
        namespace = re.search(
            '\{([^{}]*)\}([^{}]*)',
            series.tree.tag
        ).group(1)
        ElementTree.register_namespace('', namespace)

    def _write_flat_element(self, series, tag, attrib, indent):
        """ Write a single element with indentation. """
        element = ElementTree.Element(tag)
        element.attrib = attrib
        self.xml_output_file.write(
            indent * ' ' + ElementTree.tostring(element) + '\n',
        )

    def _remove_namespace(self, tree):
        for element in tree.iter():
            element.tag = re.sub('{.*}', '', element.tag)

    def _write_tree(self, tree, begin=None, end=None, indent=0):
        """
        Write a part of the tree stringlist.

        Begin and end are strings that mark begin and end of the part of
        the tree that needs to be written. May not work if elementtrees
        splitting behaviour gets really weird.
        """

        self.xml_output_file.write(indent * ' ')

        write = True if begin is None else False

        for text in ElementTree.tostringlist(tree):
            if begin is not None and begin in text:
                write = True

            if write:
                self.xml_output_file.write(text)

            if end is not None and end in text:
                break

        if (not text.endswith('\n')) and (end is not None):
            self.xml_output_file.write('\n')

    def _write_series(self, series, bin_output_file=None):
        """
        Write series to xmlfile.

        Event elements are generated and written one by one to keep
        memory consumption low.
        """
        # We are going to modify the tree.
        tree = copy.deepcopy(series.tree)
        self._remove_namespace(tree)

        # Write header
        self._write_tree(tree, begin='<series', end='</header>', indent=4)

        # Write the events
        if self.binary:
            np.float32(series.ma.filled(series.missval)).tofile(bin_output_file)
        else:
            for dt, npvalue in series:
                if np.ma.is_masked(npvalue):
                    value='{:.2f}'.format(series.missval)
                else:
                    value='{:.2f}'.format(npvalue)
                
                self._write_flat_element(
                    series=series, tag='event', attrib=dict(
                        date=dt.strftime('%Y-%m-%d'),
                        time=dt.strftime('%H:%M:%S'),
                        value=value,
                        flag='0',
                    ), indent=8,
                )

        # Write the series closing tag
        self._write_tree(tree, begin='</series', end='</series>', indent=4)

    def write(self, series_iterable):

        if self.binary:
            bin_output_file = open(self.bin_output_path, 'wb')
        else:
            bin_output_file = None

        for series in series_iterable:
            tree = copy.deepcopy(series.tree)

            if not self.initialized:
                self._register_namespace(series)
                self.xml_output_file.write(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                )
                self._write_tree(tree, begin=None, end='</timeZone>')
                self.initialized = True

            self._write_series(series=series, bin_output_file=bin_output_file)

        if self.initialized:
            self._write_tree(tree, begin='</TimeSeries')

        self.xml_output_file.close()
        if self.binary:
            bin_output_file.close()


class SeriesProcessor(object):
    """
    Base class for any script that does
    some kind of modification to timeseries.
    """

    def _parser(self):
        """
        Return basic parser.
        """
        parser = argparse.ArgumentParser(
            description='Argument parser description.',
        )
        parser.add_argument(
            'input',
            metavar='INPUT',
            type=str,
            help='Input file or directory',
        )
        parser.add_argument(
            'output',
            metavar='OUTPUT',
            type=str,
            help='Output file or directory, depending on input.',
        )
        parser.add_argument(
            '-f', '--format',
            metavar='FORMAT',
            type=str,
            choices='br',
            help='Force (b)inary or (r)egular format.',
        )
        return parser

    def _process_series(self, series_iterable):
        """
        Return generator of resulting series.
        """
        for series in series_iterable:
            for result in self.process(series):
                yield result

    def _process_file(self, input_file, output_file):
        reader = SeriesReader(input_file)
        if self.args['format'] == 'b':
            binary = True
        elif self.args['format'] == 'r':
            binary = False
        else:
            binary = reader.binary
        writer = SeriesWriter(output_file, binary=binary)
        writer.write(self._process_series(reader.read()))

    def _process_dir(self, input_dir, output_dir):
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        for input_path in glob.glob(os.path.join(input_dir, '*.xml')):

            # Determine name of output files.
            input_file = os.path.basename(input_path)
            output_file = re.sub('^input', 'output', input_file)

            output_path = os.path.join(output_dir, output_file)

            # Process pair of files
            self._process_file(
                input_file=input_path,
                output_file=output_path,
            )

    def main(self):
        parser = self._parser()
        self.add_arguments(parser)
        self.args = vars(parser.parse_args())
        input_path = self.args['input']
        output_path = self.args['output']

        if os.path.isfile(input_path):
            return self._process_file(
                input_file=input_path,
                output_file=output_path,
            )

        if os.path.isdir(input_path):
            return self._process_dir(
                input_dir=input_path,
                output_dir=output_path,
            )

    def add_arguments(self, parser):
        """
        Override this method in scripts to add arguments to the parser,
        or change its description attribute.
        """
        pass

    def process(self, series):
        """
        Return series.

        Override this method in scripts.
        """
        yield series
