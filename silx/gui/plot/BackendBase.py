# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2004-2016 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ############################################################################*/
"""Base class for Plot backends.

It documents the Plot backend API.

This API is a simplified version of PyMca PlotBackend API.
"""

__authors__ = ["V.A. Sole", "T. Vincent"]
__license__ = "MIT"
__date__ = "18/02/2016"


import weakref


# Names for setCursor
CURSOR_DEFAULT = 'default'
CURSOR_POINTING = 'pointing'
CURSOR_SIZE_HOR = 'size horizontal'
CURSOR_SIZE_VER = 'size vertical'
CURSOR_SIZE_ALL = 'size all'


class BackendBase(object):
    """Class defining the API a backend of the Plot should provide."""

    def __init__(self, plot, parent=None):
        """Init.

        :param Plot plot: The Plot this backend is attached to
        :param parent: The parent widget of the plot widget.
        """
        # Store a weakref to get access to the plot state.
        self._setPlot(plot)

    @property
    def _plot(self):
        """The plot this backend is attached to."""
        if self._plotRef is None:
            raise RuntimeError('This backend is not attached to a Plot')

        plot = self._plotRef()
        if plot is None:
            raise RuntimeError('This backend is no more attached to a Plot')
        return plot

    def _setPlot(self, plot):
        """Allow to set plot after init.

        Use with caution, basically **immediately** after init.
        """
        self._plotRef = weakref.ref(plot)

    # Add methods

    def addCurve(self, x, y, legend,
                 color, symbol, linewidth, linestyle,
                 yaxis,
                 xerror, yerror, z, selectable,
                 fill):
        """Add a 1D curve given by x an y to the graph.

        :param numpy.ndarray x: The data corresponding to the x axis
        :param numpy.ndarray y: The data corresponding to the y axis
        :param str legend: The legend to be associated to the curve
        :param color: color(s) to be used
        :type color: string ("#RRGGBB") or (npoints, 4) unsigned byte array or
                     one of the predefined color names defined in Colors.py
        :param str symbol: Symbol to be drawn at each (x, y) position::

            - ' ' or '' no symbol
            - 'o' circle
            - '.' point
            - ',' pixel
            - '+' cross
            - 'x' x-cross
            - 'd' diamond
            - 's' square

        :param float linewidth: The width of the curve in pixels

            - ' ' or ''  no line
            - '-'  solid line
            - '--' dashed line
            - '-.' dash-dot line
            - ':'  dotted line

        :param str yaxis: The Y axis this curve belongs to in: 'left', 'right'
        :param xerror: Values with the uncertainties on the x values
        :type xerror: numpy.ndarray or None
        :param yerror: Values with the uncertainties on the y values
        :type yerror: numpy.ndarray or None
        :param int z: Layer on which to draw the cuve
        :param bool selectable: indicate if the curve can be selected
        :returns: The handle used by the backend to univocally access the curve
        """
        raise NotImplementedError()

    def addImage(self, data, legend,
                 xScale, yScale, z,
                 selectable, draggable,
                 colormap):
        """Add an image to the plot.

        :param numpy.ndarray data: (nrows, ncolumns) data or
                     (nrows, ncolumns, RGBA) ubyte array
        :param str legend: The legend to be associated to the image
        :param xScale: (origin, scale) of the data on the X axis
        :type xScale: 2-tuple of float
        :param yScale: (origin, scale) of the data on the Y axis
        :type yScale: 2-tuple of float
        :param int z: Layer on which to draw the image
        :param bool selectable: indicate if the image can be selected
        :param bool draggable: indicate if the image can be moved
        :param colormap: Dictionary describing the colormap to use.
                         Ignored if data is RGB(A).
        :type colormap: dict or None
        :returns: The handle used by the backend to univocally access the image
        """
        raise NotImplementedError()

    def addItem(self, x, y, legend, shape, color, fill, overlay):
        """Add an item (i.e. a shape) to the plot.

        :param numpy.ndarray x: The X coords of the points of the shape
        :param numpy.ndarray y: The Y coords of the points of the shape
        :param str legend: The legend to be associated to the item
        :param str shape: Type of item to be drawn in
                          hline, polygon, rectangle, vline
        :param bool fill: True to fill the shape
        :param bool overlay: True if item is an overlay, False otherwise
        :returns: The handle used by the backend to univocally access the item
        """
        raise NotImplementedError()

    def addMarker(self, x, y, legend, text, color,
                  selectable, draggable,
                  symbol, constraint):
        """Add a point, vertical line or horizontal line marker to the plot.

        :param float x: Horizontal position of the marker in graph coordinates.
                        If None, the marker is a horizontal line.
        :param float y: Vertical position of the marker in graph coordinates.
                        If None, the marker is a vertical line.
        :param str legend: Legend associated to the marker
        :param str text: Text associated to the marker (or None for no text)
        :param str color: Color to be used for instance 'blue', 'b', '#FF0000'
        :param bool selectable: indicate if the marker can be selected
        :param bool draggable: indicate if the marker can be moved
        :param str symbol: Symbol representing the marker.
        Only relevant for point markers where X and Y are not None.
        Value in:

            - 'o' circle
            - '.' point
            - ',' pixel
            - '+' cross
            - 'x' x-cross
            - 'd' diamond
            - 's' square

        :param constraint: A function filtering marker displacement by
                           dragging operations or None for no filter.
                           This function is called each time a marker is
                           moved.
                           This parameter is only used if draggable is True.
        :type constraint: None or a callable that takes the coordinates of
                          the current cursor position in the plot as input
                          and that returns the filtered coordinates.
        :return: Handle used by the backend to univocally access the marker
        """
        raise NotImplementedError()

    # Remove methods

    def clear(self):
        """Remove all items from the plot."""
        raise NotImplementedError()

    def remove(self, item):
        """Remove an existing item from the plot.

        :param item: A backend specific item handle returned by a add* method
        """
        raise NotImplementedError()

    # Interaction methods

    def setGraphCursorShape(self, cursor):
        """Set the cursor shape.

        To override in interactive backends.

        :param str cursor: Name of the cursor shape or None
        """
        pass

    def setGraphCursor(self, flag, color, linewidth, linestyle):
        """Toggle the display of a crosshair cursor and set its attributes.

        To override in interactive backends.

        :param bool flag: Toggle the display of a crosshair cursor.
        :param color: The color to use for the crosshair.
        :type color: A string (either a predefined color name in Colors.py
                    or "#RRGGBB")) or a 4 columns unsigned byte array.
        :param int linewidth: The width of the lines of the crosshair.
        :param linestyle: Type of line::

                - ' ' no line
                - '-' solid line
                - '--' dashed line
                - '-.' dash-dot line
                - ':' dotted line

        :type linestyle: None or one of the predefined styles.
        """
        pass

    # Active curve

    def setCurveColor(self, curve, color):
        """Set the color of a curve.

        :param curve: The curve handle
        :param str color: The color to use.
        """
        raise NotImplementedError()

    # Misc.

    def getWidgetHandle(self):
        """Return the widget this backend is drawing to."""
        raise NotImplementedError()

    def replot(self):
        """Redraw the plot."""
        raise NotImplementedError()

    def saveGraph(self, fileName, fileFormat, dpi):
        """Save the graph to a file (or a StringIO)

        :param fileName: Destination
        :type fileName: String or StringIO or BytesIO
        :param str fileFormat: String specifying the format
        :param int dpi: The resolution to use or None.
        """
        raise NotImplementedError()

    # Graph labels

    def setGraphTitle(self, title):
        """Set the main title of the plot.

        :param str title: Title associated to the plot
        """
        raise NotImplementedError()

    def setGraphXLabel(self, label):
        """Set the X axis label.

        :param str label: label associated to the plot bottom X axis
        """
        raise NotImplementedError()

    def setGraphYLabel(self, label):
        """Set the left Y axis label.

        :param str label: label associated to the plot left Y axis
        """
        raise NotImplementedError()

    # Graph limits

    def resetZoom(self, dataMargins):
        """Reset the displayed area of the plot.

        Autoscale any axis that is in autoscale mode.
        Keep current limits on axes not in autoscale mode

        Extra margins can be added around the data inside the plot area.
        Margins are given as one ratio of the data range per limit of the
        data (xMin, xMax, yMin and yMax limits).
        For log scale, extra margins are applied in log10 of the data.

        :param dataMargins: Ratios of margins to add around the data inside
                            the plot area for each side
        :type dataMargins: A 4-tuple of float as (xMin, xMax, yMin, yMax).
        """
        raise NotImplementedError()

    def setLimits(self, xmin, xmax, ymin, ymax, y2min=None, y2max=None):
        """Set the limits of the X and Y axes at once.

        :param float xmin: minimum bottom axis value
        :param float xmax: maximum bottom axis value
        :param float ymin: minimum left axis value
        :param float ymax: maximum left axis value
        :param float y2min: minimum right axis value
        :param float y2max: maximum right axis value
        """
        raise NotImplementedError()

    def getGraphXLimits(self):
        """Get the graph X (bottom) limits.

        :return:  Minimum and maximum values of the X axis
        """
        raise NotImplementedError()

    def setGraphXLimits(self, xmin, xmax):
        """Set the limits of X axis.

        :param float xmin: minimum bottom axis value
        :param float xmax: maximum bottom axis value
        """
        raise NotImplementedError()

    def getGraphYLimits(self, axis):
        """Get the graph Y (left) limits.

        :param str axis: The axis for which to get the limits: left or right
        :return: Minimum and maximum values of the Y axis
        """
        raise NotImplementedError()

    def setGraphYLimits(self, ymin, ymax):
        """Set the limits of the Y axis.

        :param float ymin: minimum left axis value
        :param float ymax: maximum left axis value
        """
        raise NotImplementedError()

    # Graph axes

    def setXAxisLogarithmic(self, flag):
        """Set the X axis scale between linear and log.

        :param bool flag: If True, the bottom axis will use a log scale
        """
        raise NotImplementedError()

    def setYAxisLogarithmic(self, flag):
        """Set the Y axis scale between linear and log.

        :param bool flag: If True, the left axis will use a log scale
        """
        raise NotImplementedError()

    def invertYAxis(self, flag):
        """Invert the Y axis.

        :param bool flag: If True, put the vertical axis origin on the top
        """
        raise NotImplementedError()

    def isYAxisInverted(self):
        """Return True if left Y axis is inverted, False otherwise."""
        raise NotImplementedError()

    def isKeepDataAspectRatio(self):
        """Returns whether the plot is keeping data aspect ratio or not."""
        raise NotImplementedError()

    def keepDataAspectRatio(self, flag):
        """
        :param flag:  True to respect data aspect ratio
        :type flag: Boolean, default True
        """
        raise NotImplementedError()

    def showGrid(self, flag):
        """Set grid

        :param flag: False to disable grid, 1 or True for major grid,
                     2 for major and minor grid"""
        raise NotImplementedError()

    # colormap

    def getSupportedColormaps(self):
        """Get a list of strings with the supported colormap names.

        The list should at least contain and start by:
        ['gray', 'reversed gray', 'temperature', 'red', 'green', 'blue']
        """
        return ('gray', 'reversed gray', 'temperature', 'red', 'green', 'blue')

    # Data <-> Pixel coordinates conversion

    def dataToPixel(self, x, y, axis):
        """Convert a position in data space to a position in pixels
        in the widget.

        :param float x: The X coordinate in data space. If None
                            the middle position of the displayed data is used.
        :param float y: The Y coordinate in data space. If None
                            the middle position of the displayed data is used.
        :param str axis: The Y axis to use for the conversion
                         ('left' or 'right').
        :returns: The corresponding position in pixels or
                  None if the data position is not in the displayed area.
        :rtype: A tuple of 2 floats: (xPixel, yPixel) or None.
        """
        raise NotImplementedError()

    def pixelToData(self, x, y, axis):
        """Convert a position in pixels in the widget to a position in
        the data space.

        :param float x: The X coordinate in pixels. If None
                            the center of the widget is used.
        :param float y: The Y coordinate in pixels. If None
                            the center of the widget is used.
        :param str axis: The Y axis to use for the conversion
                         ('left' or 'right').
        :returns: The corresponding position in data space or
                  None if the pixel position is not in the plot area.
        :rtype: A tuple of 2 floats: (xData, yData) or None.
        """
        raise NotImplementedError()

    def getPlotBoundsInPixels(self):
        """Plot area bounds in widget coordinates in pixels.

        :return: bounds as a 4-tuple of int: (left, top, width, height)
        """
        raise NotImplementedError()
