#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Generate a printable calendar in PDF format, suitable for embedding
into another document.

Tested with Python 2.7.

Dependencies:
- Python
- Reportlab

Resources Used:
- https://stackoverflow.com/a/37443801/435253
  (Originally present at http://billmill.org/calendar )
- https://www.reportlab.com/docs/reportlab-userguide.pdf

Originally created by Bill Mill on 11/16/05, this script is in the public
domain. There are no express warranties, so if you mess stuff up with this
script, it's not my fault.

Refactored and improved 2017-11-23 by Stephan Sokolow (http://ssokolow.com/).

TODO:
- Implement diagonal/overlapped cells for months which touch six weeks to avoid
  wasting space on six rows.
"""

from __future__ import (absolute_import, division, print_function,
                        with_statement, unicode_literals)

__author__ = "Bill Mill; Stephan Sokolow (deitarion/SSokolow); Bill Mill"
__license__ = "CC0-1.0"  # https://creativecommons.org/publicdomain/zero/1.0/

import calendar, collections, datetime
from contextlib import contextmanager

from reportlab.lib import pagesizes
from reportlab.pdfgen.canvas import Canvas

ORDINALS = {
    1: 'st', 2: 'nd', 3: 'rd',
    21: 'st', 22: 'nd', 23: 'rd',
    31: 'st',
    None: 'th'}

# Something to help make code more readable
Font = collections.namedtuple('Font', ['name', 'size'])
Geom = collections.namedtuple('Geom', ['x', 'y', 'width', 'height'])
Size = collections.namedtuple('Size', ['width', 'height'])

@contextmanager
def save_state(canvas):
    """Simple context manager to tidy up saving and restoring canvas state"""
    canvas.saveState()
    yield
    canvas.restoreState()

def create_calendar(canvas, rect, datetime_obj, first_weekday=calendar.SUNDAY):
    """Create a one-month pdf calendar, and return the canvas

    @param rect: A C{Geom} or 4-item iterable of floats defining the shape of
        the calendar in points with any margins already applied.
    @param datetime_obj: A Python C{datetime} object specifying the month
        the calendar should represent.

    @type canvas: C{reportlab.pdfgen.canvas.Canvas}
    @type rect: C{Geom}
    """
    calendar.setfirstweekday(first_weekday)
    cal = calendar.monthcalendar(datetime_obj.year, datetime_obj.month)
    rect = Geom(*rect)

    # set up constants
    font = Font('Helvetica', min(rect.width, rect.height) * 0.028)
    rows = len(cal)
    cellsize = Size(rect.width / 7, rect.height / rows)

    with save_state(canvas):
        canvas.setFont(*font)

        # now fill in the day numbers and any data
        for row, week in enumerate(cal):
            for col, day in enumerate(week):
                draw_cell(canvas, day, Geom(
                    x=rect.x + (cellsize.width * col),
                    y=rect.y + ((rows - row) * cellsize.height),
                    width=cellsize.width, height=cellsize.height), font)

    # finish this page
    canvas.showPage()
    return canvas

def draw_cell(canvas, day, rect, font):
    """Draw a calendar cell with the given characteristics

    @param rect: An (x, y, width, height) tuple defining the shape of the cell
        in points.
    @type rect: (float, float, float, float)
    """
    # Skip drawing cells that don't correspond to a date in this month
    if not day:
        return

    margin = Size(font.size * 0.5, font.size * 1.3)

    # Draw the cell border
    canvas.rect(rect.x, rect.y - rect.height, rect.width, rect.height)

    day = str(day)
    ordinal_str = ORDINALS.get(int(day), ORDINALS[None])

    # Draw the number
    text_x = rect.x + margin.width
    text_y = rect.y - margin.height
    canvas.drawString(text_x, text_y, day)

    # Draw the lifted ordinal number suffix
    number_width = canvas.stringWidth(day, font.name, font.size)
    canvas.drawString(text_x + number_width,
                      text_y + (margin.height * 0.1),
                      ordinal_str)

def generate_pdf(datetime_obj, outfile, size):
    """Helper to apply create_calendar to save a ready-to-print file to disk.

    @param datetime_obj: A Python C{datetime} object specifying the month
        the calendar should represent.
    @param outfile: The path to which to write the PDF file.
    @param size: A (width, height) tuple (specified in points) representing
        the target page size.
    """
    size = Size(*size)
    canvas = Canvas(outfile, size)

    # margins
    wmar, hmar = size.width / 50, size.height / 50
    size = Size(size.width - (2 * wmar), size.height - (2 * hmar))

    create_calendar(canvas,
                    Geom(wmar, hmar, size.width, size.height),
                    datetime_obj).save()

if __name__ == "__main__":
    generate_pdf(datetime.datetime.now(), 'calendar.pdf',
                 pagesizes.landscape(pagesizes.letter))
