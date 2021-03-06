# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2016 European Synchrotron Radiation Facility
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
# ###########################################################################*/
"""Widget providing a set of tools to draw masks on a PlotWidget.

This widget is meant to work with :class:`PlotWidget`.

- :class:`Mask`: Handle mask bitmap update and history
- :class:`MaskToolsWidget`: GUI for :class:`Mask`
- :class:`MaskToolsDockWidget`: DockWidget to integrate in :class:`PlotWindow`
"""

from __future__ import division

__authors__ = ["T. Vincent"]
__license__ = "MIT"
__data__ = "08/06/2016"


import os
import sys
import numpy
import logging

from silx.image import shapes
from .Colors import cursorColorForColormap, rgba
from .. import icons, qt

from silx.third_party.EdfFile import EdfFile
from silx.third_party.TiffIO import TiffIO

_logger = logging.getLogger(__name__)


class Mask(qt.QObject):
    """A mask field with update operations.

    Coords follows (row, column) convention and are in mask array coords.

    This is meant for internal use by :class:`MaskToolsWidget`.
    """

    sigChanged = qt.Signal()
    """Signal emitted when the mask has changed"""

    sigUndoable = qt.Signal(bool)
    """Signal emitted when undo becomes possible/impossible"""

    sigRedoable = qt.Signal(bool)
    """Signal emitted when redo becomes possible/impossible"""

    def __init__(self):
        self.historyDepth = 10
        """Maximum number of operation stored in history list for undo"""

        self._mask = numpy.array((), dtype=numpy.uint8)  # Store the mask

        # Init lists for undo/redo
        self._history = []
        self._redo = []

        super(Mask, self).__init__()

    def _notify(self):
        """Notify of mask change."""
        self.sigChanged.emit()

    def getMask(self, copy=True):
        """Get the current mask as a 2D array.

        :param bool copy: True (default) to get a copy of the mask.
                          If False, the returned array MUST not be modified.
        :return: The array of the mask with dimension of the 'active' image.
                 If there is no active image, an empty array is returned.
        :rtype: 2D numpy.ndarray of uint8
        """
        return numpy.array(self._mask, copy=copy)

    def setMask(self, mask, copy=True):
        """Set the mask to a new array.

        :param numpy.ndarray mask: The array to use for the mask.
        :type mask: numpy.ndarray of uint8 of dimension 2, C-contiguous.
                    Array of other types are converted.
        :param bool copy: True (the default) to copy the array,
                          False to use it as is if possible.
        """
        assert len(mask.shape) == 2
        self._mask = numpy.array(mask, copy=copy, order='C', dtype=numpy.uint8)
        self._notify()

    def save(self, filename, kind):
        """Save current mask in a file

        :param str filename: The file where to save to mask
        :param str kind: The kind of file to save in 'edf', 'tif', 'npy'
        :return: True if save succeeded, False otherwise
        """
        if kind == 'edf':
            edfFile = EdfFile(filename, access="w+")
            edfFile.WriteImage({}, self.getMask(copy=False), Append=0)
            return True

        elif kind == 'tif':
            tiffFile = TiffIO(filename, mode='w')
            tiffFile.writeImage(self.getMask(copy=False), software='silx')
            return True

        elif kind == 'npy':
            try:
                numpy.save(filename, self.getMask(copy=False))
            except IOError:
                return False
            return True
        return False

    # History control

    def resetHistory(self):
        """Reset history"""
        self._history = [numpy.array(self._mask, copy=True)]
        self._redo = []
        self.sigUndoable.emit(False)
        self.sigRedoable.emit(False)

    def commit(self):
        """Append the current mask to history if changed"""
        if (not self._history or self._redo or
                not numpy.all(numpy.equal(self._mask, self._history[-1]))):
            if self._redo:
                self._redo = []  # Reset redo as a new action as been performed
                self.sigRedoable[bool].emit(False)

            while len(self._history) >= self.historyDepth:
                self._history.pop(0)
            self._history.append(numpy.array(self._mask, copy=True))

            if len(self._history) == 2:
                self.sigUndoable.emit(True)

    def undo(self):
        """Restore previous mask if any"""
        if len(self._history) > 1:
            self._redo.append(self._history.pop())
            self._mask = numpy.array(self._history[-1], copy=True)
            self._notify()  # Do not store this change in history

            if len(self._redo) == 1:  # First redo
                self.sigRedoable.emit(True)
            if len(self._history) == 1:  # Last value in history
                self.sigUndoable.emit(False)

    def redo(self):
        """Restore previously undone modification if any"""
        if self._redo:
            self._mask = self._redo.pop()
            self._history.append(numpy.array(self._mask, copy=True))
            self._notify()

            if not self._redo:  # No more redo
                self.sigRedoable.emit(False)
            if len(self._history) == 2:  # Something to undo
                self.sigUndoable.emit(True)

    # Whole mask operations

    def clear(self, level):
        """Set all values of the given mask level to 0.

        :param int level: Value of the mask to set to 0.
        """
        assert level > 0 and level < 256
        self._mask[self._mask == level] = 0
        self._notify()

    def reset(self, shape=None):
        """Reset the mask to zero and change its shape

        :param shape: Shape of the new mask or None to have an empty mask
        :type shape: 2-tuple of int
        """
        if shape is None:
            shape = 0, 0  # Empty 2D array
        assert len(shape) == 2

        shapeChanged = (shape != self._mask.shape)
        self._mask = numpy.zeros(shape, dtype=numpy.uint8)
        if shapeChanged:
            self.resetHistory()

        self._notify()

    def invert(self, level):
        """Invert mask of the given mask level.

        0 values become level and level values become 0.

        :param int level: The level to invert.
        """
        assert level > 0 and level < 256
        masked = self._mask == level
        self._mask[self._mask == 0] = level
        self._mask[masked] = 0
        self._notify()

    # Drawing operations

    def updateRectangle(self, level, row, col, height, width, mask=True):
        """Mask/Unmask a rectangle of the given mask level.

        :param int level: Mask level to update.
        :param int row: Starting row of the rectangle
        :param int col: Starting column of the rectangle
        :param int height:
        :param int width:
        :param bool mask: True to mask (default), False to unmask.
        """
        assert level > 0 and level < 256
        selection = self._mask[max(0, row):row+height+1,
                               max(0, col):col+width+1]
        if mask:
            selection[:, :] = level
        else:
            selection[selection == level] = 0
        self._notify()

    def updatePolygon(self, level, vertices, mask=True):
        """Mask/Unmask a polygon of the given mask level.

        :param int level: Mask level to update.
        :param vertices: Nx2 array of polygon corners as (row, col)
        :param bool mask: True to mask (default), False to unmask.
        """
        fill = shapes.polygon_fill_mask(vertices, self._mask.shape)
        if mask:
            self._mask[fill != 0] = level
        else:
            self._mask[numpy.logical_and(fill != 0,
                                         self._mask == level)] = 0
        self._notify()

    def updatePoints(self, level, rows, cols, mask=True):
        """Mask/Unmask points with given coordinates.

        :param int level: Mask level to update.
        :param rows: Rows of selected points
        :type rows: 1D numpy.ndarray
        :param cols: Columns of selected points
        :type cols: 1D numpy.ndarray
        :param bool mask: True to mask (default), False to unmask.
        """
        valid = numpy.logical_and(
            numpy.logical_and(rows >= 0, cols >= 0),
            numpy.logical_and(rows < self._mask.shape[0],
                              cols < self._mask.shape[1]))
        rows, cols = rows[valid], cols[valid]

        if mask:
            self._mask[rows, cols] = level
        else:
            inMask = self._mask[rows, cols] == level
            self._mask[rows[inMask], cols[inMask]] = 0
        self._notify()

    def updateStencil(self, level, stencil, mask=True):
        """Mask/Unmask area from boolean mask.

        :param int level: Mask level to update.
        :param stencil: Boolean mask of mask values to update
        :type stencil: numpy.array of same dimension as the mask
        :param bool mask: True to mask (default), False to unmask.
        """
        rows, cols = numpy.nonzero(stencil)
        self.updatePoints(level, rows, cols, mask)

    def updateDisk(self, level, crow, ccol, radius, mask=True):
        """Mask/Unmask a disk of the given mask level.

        :param int level: Mask level to update.
        :param int crow: Disk center row.
        :param int ccol: Disk center column.
        :param float radius: Radius of the disk in mask array unit
        :param bool mask: True to mask (default), False to unmask.
        """
        rows, cols = shapes.circle_fill(crow, ccol, radius)
        self.updatePoints(level, rows, cols, mask)

    def updateLine(self, level, row0, col0, row1, col1, width, mask=True):
        """Mask/Unmask a line of the given mask level.

        :param int level: Mask level to update.
        :param int row0: Row of the starting point.
        :param int col0: Column of the starting point.
        :param int row1: Row of the end point.
        :param int col1: Column of the end point.
        :param int width: Width of the line in mask array unit.
        :param bool mask: True to mask (default), False to unmask.
        """
        rows, cols = shapes.draw_line(row0, col0, row1, col1, width)
        self.updatePoints(level, rows, cols, mask)


class MaskToolsWidget(qt.QWidget):
    """Widget with tools for drawing mask on an image in a PlotWidget."""

    def __init__(self, plot, parent=None):
        self._plot = plot
        self._maskName = '__MASK_TOOLS_%d' % id(self)  # Legend of the mask

        self._colormap = {
            'name': None,
            'normalization': 'linear',
            'autoscale': False,
            'vmin': 0, 'vmax': 255,
            'colors': None}
        self._overlayColor = rgba('gray')  # Color of the mask
        self._setMaskColors(1, 0.5)

        self._doMask = None  # Store mask/unmask state while interacting
        self._origin = (0., 0.)  # Mask origin in plot
        self._scale = (1., 1.)  # Mask scale in plot
        self._z = 1  # Mask layer in plot
        self._data = numpy.zeros((0, 0), dtype=numpy.uint8)  # Store image

        self._mask = Mask()
        self._mask.sigChanged.connect(self._updatePlotMask)

        self._drawingMode = None  # Store current drawing mode
        self._lastPencilPos = None

        self._multipleMasks = 'exclusive'

        super(MaskToolsWidget, self).__init__(parent)
        self._initWidgets()

        self._maskFileDir = qt.QDir.home().absolutePath()

        self.plot.sigInteractiveModeChanged.connect(
            self._interactiveModeChanged)

    def getMask(self, copy=True):
        """Get the current mask as a 2D array.

        :param bool copy: True (default) to get a copy of the mask.
                          If False, the returned array MUST not be modified.
        :return: The array of the mask with dimension of the 'active' image.
                 If there is no active image, an empty array is returned.
        :rtype: 2D numpy.ndarray of uint8
        """
        return self._mask.getMask(copy=copy)

    def multipleMasks(self):
        """Return the current mode of multiple masks support.

        See :meth:`setMultipleMasks`
        """
        return self._multipleMasks

    def setMultipleMasks(self, mode):
        """Set the mode of multiplt masks support.

        Available modes:

        - 'single': Edit a single level of mask
        - 'exclusive': Supports to 256 levels of non overlapping masks

        :param str mode: The mode to use
        """
        assert mode in ('exclusive', 'single')
        if mode != self._multipleMasks:
            self._multipleMasks = mode
            self.levelWidget.setVisible(self._multipleMasks != 'single')
            self.clearAllBtn.setVisible(self._multipleMasks != 'single')

    @property
    def maskFileDir(self):
        """The directory from which to load/save mask from/to files."""
        if not os.path.isdir(self._maskFileDir):
            self._maskFileDir = qt.QDir.home().absolutePath()
        return self._maskFileDir

    @maskFileDir.setter
    def maskFileDir(self, maskFileDir):
        self._maskFileDir = str(maskFileDir)

    @property
    def plot(self):
        """The :class:`.PlotWindow` this widget is attached to."""
        return self._plot

    def setDirection(self, direction=qt.QBoxLayout.LeftToRight):
        """Set the direction of the layout of the widget

        :param direction: QBoxLayout direction
        """
        self.layout().setDirection(direction)

    def _initWidgets(self):
        """Create widgets"""
        layout = qt.QBoxLayout(qt.QBoxLayout.LeftToRight)
        layout.addWidget(self._initMaskGroupBox())
        layout.addWidget(self._initDrawGroupBox())
        layout.addWidget(self._initThresholdGroupBox())
        layout.addStretch(1)
        self.setLayout(layout)

    def _hboxWidget(self, *widgets, **kwargs):
        """Place widgets in widget with horizontal layout

        :param widgets: Widgets to position horizontally
        :param bool stretch: True for trailing stretch (default),
                             False for no trailing stretch
        :return: A QWidget with a QHBoxLayout
        """
        stretch = kwargs.get('stretch', True)

        layout = qt.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            layout.addWidget(widget)
        if stretch:
            layout.addStretch(1)
        widget = qt.QWidget()
        widget.setLayout(layout)
        return widget

    def _initMaskGroupBox(self):
        """Init general mask operation widgets"""
        self.levelSpinBox = qt.QSpinBox()
        self.levelSpinBox.setRange(1, 255)
        self.levelSpinBox.setToolTip(
            'Choose which mask level is edited.\n'
            'A mask can have up to 255 non-overlapping levels.')
        self.levelSpinBox.valueChanged[int].connect(self._updateColors)
        self.levelWidget = self._hboxWidget(qt.QLabel('Mask level:'),
                                            self.levelSpinBox)

        grid = qt.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        self.transparencySlider = qt.QSlider(qt.Qt.Horizontal)
        self.transparencySlider.setRange(3, 10)
        self.transparencySlider.setValue(5)
        self.transparencySlider.setToolTip(
            'Set the transparency of the mask display')
        self.transparencySlider.valueChanged.connect(self._updateColors)
        grid.addWidget(qt.QLabel('Display:'), 0, 0)
        grid.addWidget(self.transparencySlider, 0, 1, 1, 3)
        grid.addWidget(qt.QLabel('<small><b>Transparent</b></small>'), 1, 1)
        grid.addWidget(qt.QLabel('<small><b>Opaque</b></small>'), 1, 3)
        transparencyWidget = qt.QWidget()
        transparencyWidget.setLayout(grid)

        invertBtn = qt.QPushButton('Invert')
        invertBtn.setShortcut(qt.Qt.CTRL + qt.Qt.Key_I)
        invertBtn.setToolTip('Invert current mask <b>%s</b>' %
                             invertBtn.shortcut().toString())
        invertBtn.clicked.connect(self._handleInvertMask)

        clearBtn = qt.QPushButton('Clear')
        clearBtn.setShortcut(qt.QKeySequence.Delete)
        clearBtn.setToolTip('Clear current mask <b>%s</b>' %
                            clearBtn.shortcut().toString())
        clearBtn.clicked.connect(self._handleClearMask)

        invertClearWidget = self._hboxWidget(
            invertBtn, clearBtn, stretch=False)

        undoBtn = qt.QPushButton('Undo')
        undoBtn.setShortcut(qt.QKeySequence.Undo)
        undoBtn.setToolTip('Undo last mask change <b>%s</b>' %
                           undoBtn.shortcut().toString())
        self._mask.sigUndoable.connect(undoBtn.setEnabled)
        undoBtn.clicked.connect(self._mask.undo)

        redoBtn = qt.QPushButton('Redo')
        redoBtn.setShortcut(qt.QKeySequence.Redo)
        redoBtn.setToolTip('Redo last undone mask change <b>%s</b>' %
                           redoBtn.shortcut().toString())
        self._mask.sigRedoable.connect(redoBtn.setEnabled)
        redoBtn.clicked.connect(self._mask.redo)

        undoRedoWidget = self._hboxWidget(undoBtn, redoBtn, stretch=False)

        self.clearAllBtn = qt.QPushButton('Clear all')
        self.clearAllBtn.setToolTip('Clear all mask levels')
        self.clearAllBtn.clicked.connect(self.resetMask)

        loadBtn = qt.QPushButton('Load...')
        loadBtn.clicked.connect(self._loadMask)

        saveBtn = qt.QPushButton('Save...')
        saveBtn.clicked.connect(self._saveMask)

        loadSaveWidget = self._hboxWidget(loadBtn, saveBtn, stretch=False)

        layout = qt.QVBoxLayout()
        layout.addWidget(self.levelWidget)
        layout.addWidget(transparencyWidget)
        layout.addWidget(invertClearWidget)
        layout.addWidget(undoRedoWidget)
        layout.addWidget(self.clearAllBtn)
        layout.addWidget(loadSaveWidget)
        layout.addStretch(1)

        maskGroup = qt.QGroupBox('Mask')
        maskGroup.setLayout(layout)
        return maskGroup

    def _initDrawGroupBox(self):
        """Init drawing tools widgets"""
        layout = qt.QVBoxLayout()

        # Draw tools
        self.browseAction = qt.QAction(
            icons.getQIcon('normal'), 'Browse', None)
        self.browseAction.setShortcut(qt.QKeySequence(qt.Qt.Key_B))
        self.browseAction.setToolTip(
            'Disables drawing tools, enables zooming interaction mode'
            ' <b>B</b>')
        self.browseAction.setCheckable(True)
        self.browseAction.triggered[bool].connect(self._browseActionTriggered)

        self.rectAction = qt.QAction(
            icons.getQIcon('shape-rectangle'), 'Rectangle selection', None)
        self.rectAction.setToolTip(
            'Rectangle selection tool: (Un)Mask a rectangular region <b>R</b>')
        self.rectAction.setShortcut(qt.QKeySequence(qt.Qt.Key_R))
        self.rectAction.setCheckable(True)
        self.rectAction.toggled[bool].connect(self._rectActionToggled)

        self.polygonAction = qt.QAction(
            icons.getQIcon('shape-polygon'), 'Polygon selection', None)
        self.polygonAction.setShortcut(qt.QKeySequence(qt.Qt.Key_S))
        self.polygonAction.setToolTip(
            'Polygon selection tool: (Un)Mask a polygonal region <b>S</b><br>'
            'Left-click to place polygon corners<br>'
            'Right-click to place the last corner')
        self.polygonAction.setCheckable(True)
        self.polygonAction.toggled[bool].connect(self._polygonActionToggled)

        self.pencilAction = qt.QAction(
            icons.getQIcon('draw-pencil'), 'Pencil tool', None)
        self.pencilAction.setShortcut(qt.QKeySequence(qt.Qt.Key_P))
        self.pencilAction.setToolTip(
            'Pencil tool: (Un)Mask using a pencil <b>P</b>')
        self.pencilAction.setCheckable(True)
        self.pencilAction.toggled[bool].connect(self._pencilActionToggled)

        self.drawActionGroup = qt.QActionGroup(self)
        self.drawActionGroup.setExclusive(True)
        self.drawActionGroup.addAction(self.browseAction)
        self.drawActionGroup.addAction(self.rectAction)
        self.drawActionGroup.addAction(self.polygonAction)
        self.drawActionGroup.addAction(self.pencilAction)

        self.browseAction.setChecked(True)

        drawButtons = []
        for action in self.drawActionGroup.actions():
            btn = qt.QToolButton()
            btn.setDefaultAction(action)
            drawButtons.append(btn)
        container = self._hboxWidget(*drawButtons)
        layout.addWidget(container)

        # Mask/Unmask radio buttons
        maskRadioBtn = qt.QRadioButton('Mask')
        maskRadioBtn.setToolTip(
            'Drawing masks with current level. Press <b>Ctrl</b> to unmask')
        maskRadioBtn.setChecked(True)

        unmaskRadioBtn = qt.QRadioButton('Unmask')
        unmaskRadioBtn.setToolTip(
            'Drawing unmasks with current level. Press <b>Ctrl</b> to mask')

        self.maskStateGroup = qt.QButtonGroup()
        self.maskStateGroup.addButton(maskRadioBtn, 1)
        self.maskStateGroup.addButton(unmaskRadioBtn, 0)

        self.maskStateWidget = self._hboxWidget(maskRadioBtn, unmaskRadioBtn)
        layout.addWidget(self.maskStateWidget)

        # Connect mask state widget visibility with browse action
        self.maskStateWidget.setHidden(self.browseAction.isChecked())
        self.browseAction.toggled[bool].connect(
            self.maskStateWidget.setHidden)

        # Pencil settings

        self.pencilSpinBox = qt.QSpinBox()
        self.pencilSpinBox.setRange(1, 1024)
        self.pencilSpinBox.setToolTip(
            """Set pencil drawing tool size in pixels of the image
            on which to make the mask.""")

        self.pencilSetting = self._hboxWidget(
            qt.QLabel('Pencil Size:'), self.pencilSpinBox)
        self.pencilSetting.setVisible(False)
        layout.addWidget(self.pencilSetting)

        layout.addStretch(1)

        drawGroup = qt.QGroupBox('Draw tools')
        drawGroup.setLayout(layout)
        return drawGroup

    def _initThresholdGroupBox(self):
        """Init thresholding widgets"""
        layout = qt.QVBoxLayout()

        # Thresholing

        self.belowThresholdAction = qt.QAction(
            icons.getQIcon('plot-roi-below'), 'Mask below threshold', None)
        self.belowThresholdAction.setToolTip(
            'Mask image where values are below given threshold')
        self.belowThresholdAction.setCheckable(True)
        self.belowThresholdAction.triggered[bool].connect(
            self._belowThresholdActionTriggered)

        self.betweenThresholdAction = qt.QAction(
            icons.getQIcon('plot-roi-between'), 'Mask within range', None)
        self.betweenThresholdAction.setToolTip(
            'Mask image where values are within given range')
        self.betweenThresholdAction.setCheckable(True)
        self.betweenThresholdAction.triggered[bool].connect(
            self._betweenThresholdActionTriggered)

        self.aboveThresholdAction = qt.QAction(
            icons.getQIcon('plot-roi-above'), 'Mask above threshold', None)
        self.aboveThresholdAction.setToolTip(
            'Mask image where values are above given threshold')
        self.aboveThresholdAction.setCheckable(True)
        self.aboveThresholdAction.triggered[bool].connect(
            self._aboveThresholdActionTriggered)

        self.thresholdActionGroup = qt.QActionGroup(self)
        self.thresholdActionGroup.setExclusive(False)
        self.thresholdActionGroup.addAction(self.belowThresholdAction)
        self.thresholdActionGroup.addAction(self.betweenThresholdAction)
        self.thresholdActionGroup.addAction(self.aboveThresholdAction)
        self.thresholdActionGroup.triggered.connect(
            self._thresholdActionGroupTriggered)

        self.loadColormapRangeAction = qt.QAction(
            icons.getQIcon('view-refresh'), 'Set min-max from colormap', None)
        self.loadColormapRangeAction.setToolTip(
            'Set min and max values from current colormap range')
        self.loadColormapRangeAction.setCheckable(False)
        self.loadColormapRangeAction.triggered.connect(
            self._loadRangeFromColormapTriggered)

        widgets = []
        for action in self.thresholdActionGroup.actions():
            btn = qt.QToolButton()
            btn.setDefaultAction(action)
            widgets.append(btn)

        spacer = qt.QWidget()
        spacer.setSizePolicy(qt.QSizePolicy.Expanding,
                             qt.QSizePolicy.Preferred)
        widgets.append(spacer)

        loadColormapRangeBtn = qt.QToolButton()
        loadColormapRangeBtn.setDefaultAction(self.loadColormapRangeAction)
        widgets.append(loadColormapRangeBtn)

        container = self._hboxWidget(*widgets, stretch=False)
        layout.addWidget(container)

        form = qt.QFormLayout()

        self.minLineEdit = qt.QLineEdit()
        self.minLineEdit.setText('0')
        self.minLineEdit.setValidator(qt.QDoubleValidator())
        self.minLineEdit.setEnabled(False)
        form.addRow('Min:', self.minLineEdit)

        self.maxLineEdit = qt.QLineEdit()
        self.maxLineEdit.setText('0')
        self.maxLineEdit.setValidator(qt.QDoubleValidator())
        self.maxLineEdit.setEnabled(False)
        form.addRow('Max:', self.maxLineEdit)

        maskBtn = qt.QPushButton('Apply mask')
        maskBtn.clicked.connect(self._maskBtnClicked)
        form.addRow(maskBtn)

        self.thresholdWidget = qt.QWidget()
        self.thresholdWidget.setLayout(form)
        self.thresholdWidget.setEnabled(False)
        layout.addWidget(self.thresholdWidget)

        layout.addStretch(1)

        thresholdGroup = qt.QGroupBox('Threshold')
        thresholdGroup.setLayout(layout)
        return thresholdGroup

    # Handle mask refresh on the plot

    def _updatePlotMask(self):
        """Update mask image in plot"""
        mask = self.getMask(copy=False)
        if len(mask):
            self.plot.addImage(mask, legend=self._maskName,
                               colormap=self._colormap,
                               origin=self._origin,
                               scale=self._scale,
                               z=self._z,
                               replace=False, resetzoom=False)
        elif self.plot.getImage(self._maskName):
            self.plot.remove(self._maskName, kind='image')

    # track widget visibility and plot active image changes

    def changeEvent(self, event):
        """Reset drawing action when disabling widget"""
        if (event.type() == qt.QEvent.EnabledChange and
                not self.isEnabled() and
                not self.browseAction.isChecked()):
            self.browseAction.trigger()  # Disable drawing tool

    def showEvent(self, event):
        try:
            self.plot.sigActiveImageChanged.disconnect(
                self._activeImageChangedAfterCare)
        except (RuntimeError, TypeError):
            pass
        self._activeImageChanged()  # Init mask + enable/disable widget
        self.plot.sigActiveImageChanged.connect(self._activeImageChanged)

    def hideEvent(self, event):
        self.plot.sigActiveImageChanged.disconnect(self._activeImageChanged)
        if not self.browseAction.isChecked():
            self.browseAction.trigger()  # Disable drawing tool

        if len(self.getMask(copy=False)):
            self.plot.sigActiveImageChanged.connect(
                self._activeImageChangedAfterCare)

    def _activeImageChangedAfterCare(self, *args):
        """Check synchro of active image and mask when mask widget is hidden.

        If active image has no more the same size as the mask, the mask is
        removed, otherwise it is adjusted to origin, scale and z.
        """
        activeImage = self.plot.getActiveImage()
        if activeImage is None or activeImage[1] == self._maskName:
            # No active image or active image is the mask...
            self.plot.sigActiveImageChanged.disconnect(
                self._activeImageChangedAfterCare)
        else:
            colormap = activeImage[4]['colormap']
            self._overlayColor = rgba(cursorColorForColormap(colormap['name']))
            self._setMaskColors(self.levelSpinBox.value(),
                                self.transparencySlider.value() /
                                self.transparencySlider.maximum())

            self._origin = activeImage[4]['origin']
            self._scale = activeImage[4]['scale']
            self._z = activeImage[4]['z'] + 1
            self._data = activeImage[0]
            if self._data.shape != self.getMask(copy=False).shape:
                # Image has not the same size, remove mask and stop listening
                if self.plot.getImage(self._maskName):
                    self.plot.remove(self._maskName, kind='image')

                self.plot.sigActiveImageChanged.disconnect(
                    self._activeImageChangedAfterCare)
            else:
                # Refresh in case origin, scale, z changed
                self._updatePlotMask()

    def _activeImageChanged(self, *args):
        """Update widget and mask according to active image changes"""
        activeImage = self.plot.getActiveImage()
        if activeImage is None or activeImage[1] == self._maskName:
            # No active image or active image is the mask...
            self.setEnabled(False)

            self._data = numpy.zeros((0, 0), dtype=numpy.uint8)
            self._mask.reset()
            self._mask.commit()

        else:  # There is an active image
            self.setEnabled(True)

            colormap = activeImage[4]['colormap']
            self._overlayColor = rgba(cursorColorForColormap(colormap['name']))
            self._setMaskColors(self.levelSpinBox.value(),
                                self.transparencySlider.value() /
                                self.transparencySlider.maximum())

            self._origin = activeImage[4]['origin']
            self._scale = activeImage[4]['scale']
            self._z = activeImage[4]['z'] + 1
            self._data = activeImage[0]
            if self._data.shape != self.getMask(copy=False).shape:
                self._mask.reset(self._data.shape)
                self._mask.commit()
            else:
                # Refresh in case origin, scale, z changed
                self._updatePlotMask()

    # Handle whole mask operations

    def load(self, filename):
        """Load a mask from an image file.

        :param str filename: File name from which to load the mask
        :return: False on failure, True on success or a resized message
                 when loading succeeded but shape of the image and the mask
                 are different.
        :rtype: bool or str
        """
        try:
            mask = numpy.load(filename)
        except IOError:
            _logger.debug('Not a numpy file: %s', filename)
            try:
                mask = EdfFile(filename, access='r').GetData(0)
            except Exception:
                _logger.error('Error while opening image file\n'
                              '%s', (sys.exc_info()[1]))
                return False

        if len(mask.shape) != 2:
            _logger.error('Not an image, shape: %d', len(mask.shape))
            return False

        if mask.shape == self._data.shape:
            self._mask.setMask(mask, copy=False)
            result = True
        else:
            _logger.warning('Mask has not the same size as current image.'
                            ' Mask will be cropped or padded to fit image'
                            ' dimensions. %s != %s',
                            str(mask.shape), str(self._data.shape))
            resizedMask = numpy.zeros(self._data.shape, dtype=numpy.uint8)
            height = min(self._data.shape[0], mask.shape[0])
            width = min(self._data.shape[1], mask.shape[1])
            resizedMask[:height, :width] = mask[:height, :width]
            self._mask.setMask(resizedMask, copy=False)
            result = 'Mask was resized from %s to %s' % (
                str(mask.shape), str(resizedMask.shape))

        self._mask.commit()
        return result

    def _loadMask(self):
        """Open load mask dialog"""
        dialog = qt.QFileDialog(self)
        dialog.setWindowTitle("Load Mask")
        dialog.setModal(1)
        dialog.setNameFilters(
            ['EDF  *.edf', 'TIFF *.tif', 'NumPy binary file *.npy'])
        dialog.setFileMode(qt.QFileDialog.ExistingFile)
        dialog.setDirectory(self.maskFileDir)
        if not dialog.exec_():
            dialog.close()
            return

        filename = dialog.selectedFiles()[0]
        dialog.close()

        self.maskFileDir = os.path.dirname(filename)
        loaded = self.load(filename)
        if not loaded:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Cannot load mask from file.")
            msg.exec_()
        elif loaded is not True:
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Warning)
            msg.setText(loaded)
            msg.exec_()

    def save(self, filename, kind):
        """Save current mask in a file

        :param str filename: The file where to save to mask
        :param str kind: The kind of file to save in 'edf', 'tif', 'npy'
        :return: True if save succeeded, False otherwise
        """
        return self._mask.save(filename, kind)

    def _saveMask(self):
        """Open Save mask dialog"""
        dialog = qt.QFileDialog(self)
        dialog.setWindowTitle("Save Mask")
        dialog.setModal(1)
        dialog.setNameFilters(
            ['EDF  *.edf', 'TIFF *.tif', 'NumPy binary file *.npy'])
        dialog.setFileMode(qt.QFileDialog.AnyFile)
        dialog.setAcceptMode(qt.QFileDialog.AcceptSave)
        dialog.setDirectory(self.maskFileDir)
        if not dialog.exec_():
            dialog.close()
            return

        extension = dialog.selectedNameFilter().split()[-1][1:]
        filename = dialog.selectedFiles()[0]
        dialog.close()

        if not filename.lower().endswith(extension):
            filename += extension

        if os.path.exists(filename):
            try:
                os.remove(filename)
            except IOError:
                msg = qt.QMessageBox(self)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setText("Cannot save.\n"
                            "Input Output Error: %s" % (sys.exc_info()[1]))
                msg.exec_()
                return

        self.maskFileDir = os.path.dirname(filename)
        if not self.save(filename, extension[1:]):
            msg = qt.QMessageBox(self)
            msg.setIcon(qt.QMessageBox.Critical)
            msg.setText("Cannot save file %s\n" % filename)
            msg.exec_()

    def _setMaskColors(self, level, alpha):
        """Set-up the mask colormap to highlight current mask level.

        :param int level: The mask level to highlight
        :param float alpha: Alpha level of mask in [0., 1.]
        """
        assert level > 0 and level < 256

        colors = numpy.empty((256, 4), dtype=numpy.float32)

        # Set color
        colors[:, :3] = self._overlayColor[:3]

        # Set alpha
        colors[:, -1] = alpha / 2.

        # Set highlighted level color
        colors[level, 3] = alpha

        # Set no mask level
        colors[0] = (0., 0., 0., 0.)

        self._colormap['colors'] = colors

    def _updateColors(self, *args):
        """Rebuild mask colormap when selected level or transparency change"""
        self._setMaskColors(self.levelSpinBox.value(),
                            self.transparencySlider.value() /
                            self.transparencySlider.maximum())
        self._updatePlotMask()

    def _handleClearMask(self):
        """Handle clear button clicked: reset current level mask"""
        self._mask.clear(self.levelSpinBox.value())
        self._mask.commit()

    def resetMask(self):
        """Reset the mask"""
        self._mask.reset(shape=self._data.shape)
        self._mask.commit()

    def _handleInvertMask(self):
        """Invert the current mask level selection."""
        self._mask.invert(self.levelSpinBox.value())
        self._mask.commit()

    # Handle drawing tools UI events

    def _interactiveModeChanged(self, source):
        """Handle plot interactive mode changed:

        If changed from elsewhere, disable drawing tool
        """
        if source is not self:
            self.browseAction.setChecked(True)

    def _browseActionTriggered(self, checked):
        """Handle browse action mode triggered by user.

        Set plot interactive mode only when
        the user is triggering the browse action.
        """
        if checked:
            self.plot.setInteractiveMode('zoom', source=self)

    def _rectActionToggled(self, checked):
        """Handle rect action mode triggering"""
        if checked:
            self._drawingMode = 'rectangle'
            self.plot.sigPlotSignal.connect(self._plotDrawEvent)
            self.plot.setInteractiveMode(
                'draw', shape='rectangle', source=self)
        else:
            self.plot.sigPlotSignal.disconnect(self._plotDrawEvent)
            self._drawingMode = None

    def _polygonActionToggled(self, checked):
        """Handle polygon action mode triggering"""
        if checked:
            self._drawingMode = 'polygon'
            self.plot.sigPlotSignal.connect(self._plotDrawEvent)
            self.plot.setInteractiveMode('draw', shape='polygon', source=self)
        else:
            self.plot.sigPlotSignal.disconnect(self._plotDrawEvent)
            self._drawingMode = None

    def _pencilActionToggled(self, checked):
        """Handle pencil action mode triggering"""
        if checked:
            self._drawingMode = 'pencil'
            self.plot.sigPlotSignal.connect(self._plotDrawEvent)
            self.plot.setInteractiveMode(
                'draw', shape='polylines', color=None, source=self)
        else:
            self.plot.sigPlotSignal.disconnect(self._plotDrawEvent)
            self._drawingMode = None

        self.pencilSetting.setVisible(checked)

    # Handle plot drawing events

    def _plotDrawEvent(self, event):
        """Handle draw events from the plot"""
        if (self._drawingMode is None or
                event['event'] not in ('drawingProgress', 'drawingFinished')):
            return

        if not len(self._data):
            return

        if self._doMask is None:
            # First draw event, use current modifiers for all draw sequence
            self._doMask = (self.maskStateGroup.checkedId() == 1)
            if qt.QApplication.keyboardModifiers() & qt.Qt.ControlModifier:
                self._doMask = not self._doMask

        level = self.levelSpinBox.value()

        if (self._drawingMode == 'rectangle' and
                event['event'] == 'drawingFinished'):
            # Convert from plot to array coords
            ox, oy = self._origin
            sx, sy = self._scale
            self._mask.updateRectangle(
                level,
                row=int((event['y'] - oy) / sy),
                col=int((event['x'] - ox) / sx),
                height=int(event['height'] / sy),
                width=int(event['width'] / sx),
                mask=self._doMask)
            self._mask.commit()

        elif (self._drawingMode == 'polygon' and
                event['event'] == 'drawingFinished'):
            # Convert from plot to array coords
            vertices = event['points'] / self._scale - self._origin
            vertices = vertices.astype(numpy.int)[:, (1, 0)]  # (row, col)
            self._mask.updatePolygon(level, vertices, self._doMask)
            self._mask.commit()

        elif self._drawingMode == 'pencil':
            # convert from plot to array coords
            col, row = event['points'][-1] / self._scale - self._origin
            row, col = int(row), int(col)
            brushSize = self.pencilSpinBox.value()

            # Draw point
            self._mask.updateDisk(level, row, col, brushSize / 2.,
                                  self._doMask)

            if self._lastPencilPos and self._lastPencilPos != (row, col):
                # Draw the line
                self._mask.updateLine(
                    level,
                    self._lastPencilPos[0], self._lastPencilPos[1],
                    row, col,
                    brushSize,
                    self._doMask)

            if event['event'] == 'drawingFinished':
                self._mask.commit()
                self._lastPencilPos = None
            else:
                self._lastPencilPos = row, col

        if event['event'] == 'drawingFinished':
            # Last draw sequence event: reset doMask
            self._doMask = None

    # Handle threshold UI events

    def _belowThresholdActionTriggered(self, triggered):
        if triggered:
            self.minLineEdit.setEnabled(True)
            self.maxLineEdit.setEnabled(False)

    def _betweenThresholdActionTriggered(self, triggered):
        if triggered:
            self.minLineEdit.setEnabled(True)
            self.maxLineEdit.setEnabled(True)

    def _aboveThresholdActionTriggered(self, triggered):
        if triggered:
            self.minLineEdit.setEnabled(False)
            self.maxLineEdit.setEnabled(True)

    def _thresholdActionGroupTriggered(self, triggeredAction):
        """Threshold action group listener."""
        if triggeredAction.isChecked():
            # Uncheck other actions
            for action in self.thresholdActionGroup.actions():
                if action is not triggeredAction and action.isChecked():
                    action.setChecked(False)

        self.thresholdWidget.setEnabled(triggeredAction.isChecked())

    def _maskBtnClicked(self):
        if self.belowThresholdAction.isChecked():
            if len(self._data) and self.minLineEdit.text():
                min_ = float(self.minLineEdit.text())
                self._mask.updateStencil(self.levelSpinBox.value(),
                                         self._data < min_)
                self._mask.commit()

        elif self.betweenThresholdAction.isChecked():
            if (len(self._data) and
                    self.minLineEdit.text() and self.maxLineEdit.text()):
                min_ = float(self.minLineEdit.text())
                max_ = float(self.maxLineEdit.text())
                self._mask.updateStencil(self.levelSpinBox.value(),
                                         numpy.logical_and(min_ <= self._data,
                                                           self._data <= max_))
                self._mask.commit()

        elif self.aboveThresholdAction.isChecked():
            if len(self._data) and self.maxLineEdit.text():
                max_ = float(self.maxLineEdit.text())
                self._mask.updateStencil(self.levelSpinBox.value(),
                                         self._data > max_)
                self._mask.commit()

    def _loadRangeFromColormapTriggered(self):
        """Set range from active image colormap range"""
        activeImage = self.plot.getActiveImage()
        if activeImage is not None and activeImage[1] != self._maskName:
            # Update thresholds according to colormap
            colormap = activeImage[4]['colormap']
            if colormap['autoscale']:
                min_ = numpy.nanmin(activeImage[0])
                max_ = numpy.nanmax(activeImage[0])
            else:
                min_, max_ = colormap['vmin'], colormap['vmax']
            self.minLineEdit.setText(str(min_))
            self.maxLineEdit.setText(str(max_))


class MaskToolsDockWidget(qt.QDockWidget):
    """:class:`MaskToolsDockWidget` embedded in a QDockWidget.

    For integration in a :class:`PlotWindow`.

    :param PlotWidget plot: The PlotWidget this widget is operating on
    :paran str name: The title of this widget
    :param parent: See :class:`QDockWidget`
    """

    def __init__(self, plot, name='Mask', parent=None):
        super(MaskToolsDockWidget, self).__init__(parent)
        self.setWindowTitle(name)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setWidget(MaskToolsWidget(plot))
        self.dockLocationChanged.connect(self._dockLocationChanged)
        self.topLevelChanged.connect(self._topLevelChanged)

    def getMask(self, copy=False):
        """Get the current mask as a 2D array.

        :param bool copy: True (default) to get a copy of the mask.
                          If False, the returned array MUST not be modified.
        :return: The array of the mask with dimension of the 'active' image.
                 If there is no active image, an empty array is returned.
        :rtype: 2D numpy.ndarray of uint8
        """
        return self.widget().getMask(copy=copy)

    def toggleViewAction(self):
        """Returns a checkable action that shows or closes this widget.

        See :class:`QMainWindow`.
        """
        action = super(MaskToolsDockWidget, self).toggleViewAction()
        action.setIcon(icons.getQIcon('image-select-brush'))
        return action

    def _dockLocationChanged(self, area):
        if area in (qt.Qt.LeftDockWidgetArea, qt.Qt.RightDockWidgetArea):
            direction = qt.QBoxLayout.TopToBottom
        else:
            direction = qt.QBoxLayout.LeftToRight
        self.widget().setDirection(direction)

    def _topLevelChanged(self, topLevel):
        if topLevel:
            self.widget().setDirection(qt.QBoxLayout.LeftToRight)
            self.resize(self.widget().minimumSize())
            self.adjustSize()
