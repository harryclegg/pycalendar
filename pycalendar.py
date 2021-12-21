"""Generate a printable calendar in PDF format, suitable for embedding
into another document.

Tested with Python 3.8.

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
Further changed 2020-01-02 by Harry Clegg.

TODO:
- Implement diagonal/overlapped cells for months which touch six weeks to avoid
  wasting space on six rows.
- Reimplement ordinals
- Make options such as font more cusomisable and stored in a better data structure.
"""

from __future__ import (
    absolute_import,
    division,
    print_function,
    with_statement,
    unicode_literals,
)

__author__ = "Bill Mill; Stephan Sokolow (deitarion/SSokolow)"
__license__ = "CC0-1.0"  # https://creativecommons.org/publicdomain/zero/1.0/

import calendar, collections, datetime
from contextlib import contextmanager
import colorsys
import numpy as np

from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics.charts.textlabels import _text2Path

# Supporting languages like French should be as simple as editing this
ORDINALS = {
    1: "st",
    2: "nd",
    3: "rd",
    21: "st",
    22: "nd",
    23: "rd",
    31: "st",
    None: "th",
}

USE_ORDINALS = False

DAY_NAMES = ["M", "T", "W", "T", "F", "S", "S"]

# Something to help make code more readable
Font = collections.namedtuple("Font", ["name", "size", "pad", "bold"])
Geom = collections.namedtuple("Geom", ["x", "y", "width", "height", "bg", "col"])
Size = collections.namedtuple("Size", ["width", "height"])


@contextmanager
def save_state(canvas):
    """Simple context manager to tidy up saving and restoring canvas state"""
    canvas.saveState()
    yield
    canvas.restoreState()


def add_calendar_page(
    canvas, colours, rect, datetime_obj, cell_cb, first_weekday=calendar.SUNDAY
):
    """Create a one-month pdf calendar, and return the canvas

    @param rect: A C{Geom} or 4-item iterable of floats defining the shape of
        the calendar in points with any margins already applied.
    @param datetime_obj: A Python C{datetime} object specifying the month
        the calendar should represent.
    @param cell_cb: A callback taking (canvas, day, rect, font) as arguments
        which will be called to render each cell.
        (C{day} will be 0 for empty cells.)

    @type canvas: C{reportlab.pdfgen.canvas.Canvas}
    @type rect: C{Geom}
    @type cell_cb: C{function(Canvas, int, Geom, Font)}
    """
    calendar.setfirstweekday(first_weekday)
    cal = calendar.monthcalendar(datetime_obj.year, datetime_obj.month)
    rect = Geom(*rect)

    # set up constants
    scale_factor = min(rect.width, rect.height)
    line_width = scale_factor * 0.0025
    rows = 8

    # Leave room for the stroke width around the outermost cells
    rect = Geom(
        rect.x + line_width,
        rect.y + line_width,
        rect.width - (line_width * 2),
        rect.height - (line_width * 2),
        "red",
        "white",
    )
    cellsize = Size(rect.width / 7, rect.height / rows)

    # TODO: make customisable
    monthFont = Font("Helvetica", scale_factor * 0.060, 5, True)
    dayFont = Font("Helvetica", scale_factor * 0.050, 4, True)
    mainFont = Font("Helvetica", scale_factor * 0.090, 7, True)

    canvas.setLineWidth(line_width)

    # print month name
    with save_state(canvas):

        month_str = (
            calendar.month_name[datetime_obj.month] + " " + str(datetime_obj.year)
        )

        cell_cb(
            canvas,
            month_str,
            Geom(
                x=rect.x,
                y=rect.y + ((rows) * cellsize.height),
                width=cellsize.width * 7,
                height=cellsize.height,
                bg=colours["titleBackground"],
                col=colours["titleText"],
            ),
            monthFont,
            scale_factor,
        )

    # print day of week headers
    for col, day in enumerate(DAY_NAMES):
        with save_state(canvas):

            cell_cb(
                canvas,
                day,
                Geom(
                    x=rect.x + (cellsize.width * col),
                    y=rect.y + ((rows - 1) * cellsize.height),
                    width=cellsize.width,
                    height=cellsize.height,
                    bg=colours["cellBackground"],
                    col=colours["cellText"],
                ),
                dayFont,
                scale_factor,
            )

    # now fill in the day numbers and any data
    lastRow = 0
    for row, week in enumerate(cal):
        for col, day in enumerate(week):
            with save_state(canvas):

                cell_cb(
                    canvas,
                    day,
                    Geom(
                        x=rect.x + (cellsize.width * col),
                        y=rect.y + ((rows - row - 2) * cellsize.height),
                        width=cellsize.width,
                        height=cellsize.height,
                        bg=colours["cellBackground"],
                        col=colours["cellText"],
                    ),
                    mainFont,
                    scale_factor,
                )
        lastRow = row

    if lastRow < 5:
        row = 5
        for col, day in enumerate(week):
            with save_state(canvas):
                cell_cb(
                    canvas,
                    "",
                    Geom(
                        x=rect.x + (cellsize.width * col),
                        y=rect.y + ((rows - row - 2) * cellsize.height),
                        width=cellsize.width,
                        height=cellsize.height,
                        bg=colours["cellBackground"],
                        col=colours["cellText"],
                    ),
                    mainFont,
                    scale_factor,
                )

    # finish this page
    return canvas


def generate_colours(hue):
    """Generate a dict of various colour shades, from a single hue value.

    @param hue: colour hue value, 0-1.
    """
    colours = dict()
    colours["cellBackground"] = colorsys.hls_to_rgb(hue, 0.90, 1)
    colours["cellText"] = colorsys.hls_to_rgb(hue, 0.15, 1)
    colours["titleBackground"] = colorsys.hls_to_rgb(hue, 0.15, 1)
    colours["titleText"] = colorsys.hls_to_rgb(hue, 0.90, 1)

    return colours


def draw_cell(canvas, day, rect, font, scale_factor):
    """Draw a calendar cell with the given characteristics

    @param day: The date in the range 0 to 31.
    @param rect: A Geom(x, y, width, height) tuple defining the shape of the
        cell in points.
    @param scale_factor: A number which can be used to calculate sizes which
        will remain proportional to the size of the entire calendar.
        (Currently the length of the shortest side of the full calendar)

    @type rect: C{Geom}
    @type font: C{Font}
    @type scale_factor: C{float}
    """

    # bold enabled by appending to font name
    if font.bold:
        font_name = font.name + "-Bold"
    else:
        font_name = font.name
    canvas.setFont(font_name, font.size)

    # Draw the cell border
    canvas.setFillColor(rect.bg)
    canvas.rect(rect.x, rect.y - rect.height, rect.width, rect.height, fill=1)
    canvas.setFillColor(rect.col)

    # Skip drawing text for cells that don't correspond to a date in this month
    if not day:
        return

    day = str(day)

    # TODO: implement ordinals
    if USE_ORDINALS:
        raise NotImplementedError("ordinals not implemented yet")
        ordinal_str = ORDINALS.get(int(day), ORDINALS[None])
    else:
        ordinal_str = ""

    # Draw the number
    text_x = rect.x + (rect.width / 2)
    text_y = rect.y - (rect.height / 2) - font.pad
    canvas.setFillColor(rect.col)
    canvas.drawCentredString(text_x, text_y, day)


def generate_pdf(year_date, size, hue=0, first_weekday=calendar.MONDAY):
    """
    Generate calendar PDF pages for every month of the year.

    @param year_date: datetime object to extract year from.
    @param size: size in points to make the calendar.
    @param hue: hue [0-1] colour value.
    @param first_weekday: when to start the week.

    """
    page_size = Size(*size)

    # margins for page
    wmar, hmar = page_size.width / 50, page_size.height / 50
    size = Size(page_size.width - (2 * wmar), page_size.height - (2 * hmar))

    year = year_date.year

    for month in range(0, 12):
        if len(hue) == 12:
            month_hue = hue[month]
        elif len(hue) == 1:
            month_hue = hue
        else:
            raise ValueError("expect either 12 or 1 hues")

        if month_hue > 1:
            month_hue = month_hue / 360

        month_colours = generate_colours(month_hue)

        file_name = "cal-" + str(year) + "-" + str(month + 1) + ".pdf"
        canvas = Canvas(file_name, page_size)

        current_month = datetime.date(year, month + 1, 1)
        add_calendar_page(
            canvas,
            month_colours,
            Geom(wmar, hmar, size.width, size.height, "red", "white"),
            current_month,
            draw_cell,
            first_weekday,
        ).save()


if __name__ == "__main__":

    # Use the date 6 months from now - should ensure that at the end of
    # the year, we use next year
    upcoming_year = datetime.datetime.now() + datetime.timedelta(days=180)

    # calendar size
    page_size = (130 * mm, 90 * mm)

    # select a hue value float 0-1, or integer 0-360
    calendar_hue = np.linspace(120, 330, 12)

    # create the pdfs
    generate_pdf(upcoming_year, page_size, hue=calendar_hue)
