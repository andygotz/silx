# coding: utf-8
# /*##########################################################################
# Copyright (C) 2016 European Synchrotron Radiation Facility
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
"""
Nominal tests of the histogramnd function.
"""

import unittest

import numpy as np

from silx.math.chistogramnd import chistogramnd as histogramnd
from silx.math import Histogramnd


def _get_bin_edges(bins_rng, n_bins, n_dims):
    edges = []
    for i_dim in range(n_dims):
        edges.append(bins_rng[i_dim, 0] +
                     np.arange(n_bins[i_dim] + 1) *
                     (bins_rng[i_dim, 1] - bins_rng[i_dim, 0]) /
                     n_bins[i_dim])
    return tuple(edges)


# ==============================================================
# ==============================================================
# ==============================================================


class _Test_chistogramnd_nominal(unittest.TestCase):
    """
    Unit tests of the histogramnd function.
    """

    ndims = None

    def setUp(self):
        ndims = self.ndims
        self.tested_dim = ndims-1

        if ndims is None:
            raise ValueError('ndims class member not set.')

        sample = np.array([5.5,        -3.3,
                           0.,         -0.5,
                           3.3,        8.8,
                           -7.7,       6.0,
                           -4.0])

        weights = np.array([500.5,    -300.3,
                            0.01,      -0.5,
                            300.3,     800.8,
                            -700.7,    600.6,
                            -400.4])

        n_elems = len(sample)

        if ndims == 1:
            shape = (n_elems,)
        else:
            shape = (n_elems, ndims)

        self.sample = np.zeros(shape=shape, dtype=sample.dtype)
        if ndims == 1:
            self.sample = sample
        else:
            self.sample[..., ndims-1] = sample

        self.weights = weights

        # the tests are performed along one dimension,
        #   all the other bins indices along the other dimensions
        #   are expected to be 2
        # (e.g : when testing a 2D sample : [0, x] will go into
        # bin [2, y] because of the bin ranges [-2, 2] and n_bins = 4
        # for the first dimension)
        self.other_axes_index = 2
        self.bins_rng = np.repeat([[-2., 2.]], ndims, axis=0)
        self.bins_rng[ndims-1] = [-4., 6.]

        self.n_bins = np.array([4]*ndims)
        self.n_bins[ndims-1] = 5

        if ndims == 1:
            def fill_histo(h, v, dim, op=None):
                if op:
                    h[:] = op(h[:], v)
                else:
                    h[:] = v
            self.fill_histo = fill_histo
        else:
            def fill_histo(h, v, dim, op=None):
                idx = [self.other_axes_index]*len(h.shape)
                idx[dim] = slice(0, None)
                if op:
                    h[idx] = op(h[idx], v)
                else:
                    h[idx] = v
            self.fill_histo = fill_histo

    def test_nominal(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul, bin_edges = histogramnd(self.sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=self.weights)

        expected_edges = _get_bin_edges(self.bins_rng,
                                        self.n_bins,
                                        self.ndims)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

        for i_edges, edges in enumerate(expected_edges):
            self.assertTrue(np.array_equal(bin_edges[i_edges],
                                           expected_edges[i_edges]),
                            msg='Testing bin_edges for dim {0}'
                                ''.format(i_edges+1))

    def test_nominal_wh_dtype(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.float32)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul, bin_edges = histogramnd(self.sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=self.weights,
                                              wh_dtype=np.float32)

        self.assertEqual(cumul.dtype, np.float32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.allclose(cumul, expected_c))

    def test_nominal_uncontiguous_sample(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        shape = list(self.sample.shape)
        shape[0] *= 2
        sample = np.zeros(shape, dtype=self.sample.dtype)
        uncontig_sample = sample[::2, ...]
        uncontig_sample[:] = self.sample

        self.assertFalse(uncontig_sample.flags['C_CONTIGUOUS'],
                         msg='Making sure the array is not contiguous.')

        histo, cumul, bin_edges = histogramnd(uncontig_sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=self.weights)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_nominal_uncontiguous_weights(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        shape = list(self.weights.shape)
        shape[0] *= 2
        weights = np.zeros(shape, dtype=self.weights.dtype)
        uncontig_weights = weights[::2, ...]
        uncontig_weights[:] = self.weights

        self.assertFalse(uncontig_weights.flags['C_CONTIGUOUS'],
                         msg='Making sure the array is not contiguous.')

        histo, cumul, bin_edges = histogramnd(self.sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=uncontig_weights)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_nominal_wo_weights(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=None)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(cumul is None)

    def test_nominal_wo_weights_w_cumul(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)

        # creating an array of ones just to make sure that
        # it is not cleared by histogramnd
        cumul_in = np.ones(self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=None,
                                   weighted_histo=cumul_in)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(cumul is None)
        self.assertTrue(np.array_equal(cumul_in,
                                       np.ones(shape=self.n_bins,
                                               dtype=np.double)))

    def test_nominal_wo_weights_w_histo(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)

        # creating an array of ones just to make sure that
        # it is not cleared by histogramnd
        histo_in = np.ones(self.n_bins, dtype=np.uint32)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=None,
                                   histo=histo_in)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h + 1))
        self.assertTrue(cumul is None)
        self.assertEqual(id(histo), id(histo_in))

    def test_nominal_last_bin_closed(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 2])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 1101.1])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights,
                                   last_bin_closed=True)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_int32_weights_double_weights_range(self):
        """
        """
        weight_min = -299.9  # ===> will be cast to -299
        weight_max = 499.9  # ===> will be cast to 499

        expected_h_tpl = np.array([0, 1, 1, 1, 0])
        expected_c_tpl = np.array([0., 0., 0., 300., 0.])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights.astype(np.int32),
                                   weight_min=weight_min,
                                   weight_max=weight_max)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_reuse_histo(self):
        """
        """

        expected_h_tpl = np.array([2, 3, 2, 2, 2])
        expected_c_tpl = np.array([0.0, -7007, -5.0, 0.1, 3003.0])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights)[0:2]

        sample_2 = self.sample[:]
        if len(sample_2.shape) == 1:
            idx = [slice(0, None)]
        else:
            idx = [slice(0, None), self.tested_dim]

        sample_2[idx] += 2

        histo_2, cumul = histogramnd(sample_2,          # <==== !!
                                     self.bins_rng,
                                     self.n_bins,
                                     weights=10 * self.weights,  # <==== !!
                                     histo=histo)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))
        self.assertEqual(id(histo), id(histo_2))

    def test_reuse_cumul(self):
        """
        """

        expected_h_tpl = np.array([0, 2, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -7007.5, -4.99, 300.4, 3503.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights)[0:2]

        sample_2 = self.sample[:]
        if len(sample_2.shape) == 1:
            idx = [slice(0, None)]
        else:
            idx = [slice(0, None), self.tested_dim]

        sample_2[idx] += 2

        histo, cumul_2 = histogramnd(sample_2,           # <==== !!
                                     self.bins_rng,
                                     self.n_bins,
                                     weights=10 * self.weights,  # <==== !!
                                     weighted_histo=cumul)[0:2]

        self.assertEqual(cumul.dtype, np.float64)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.allclose(cumul, expected_c, rtol=10e-15))
        self.assertEqual(id(cumul), id(cumul_2))

    def test_reuse_cumul_float(self):
        """
        """

        expected_h_tpl = np.array([0, 2, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -7007.5, -4.99, 300.4, 3503.5],
                                  dtype=np.float32)

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights)[0:2]

        # converting the cumul array to float
        cumul = cumul.astype(np.float32)

        sample_2 = self.sample[:]
        if len(sample_2.shape) == 1:
            idx = [slice(0, None)]
        else:
            idx = [slice(0, None), self.tested_dim]

        sample_2[idx] += 2

        histo, cumul_2 = histogramnd(sample_2,           # <==== !!
                                     self.bins_rng,
                                     self.n_bins,
                                     weights=10 * self.weights,  # <==== !!
                                     weighted_histo=cumul)[0:2]

        self.assertEqual(cumul.dtype, np.float32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertEqual(id(cumul), id(cumul_2))
        self.assertTrue(np.allclose(cumul, expected_c, rtol=10e-15))
        
class _Test_Histogramnd_nominal(unittest.TestCase):
    """
    Unit tests of the Histogramnd class.
    """

    ndims = None

    def setUp(self):
        ndims = self.ndims
        self.tested_dim = ndims-1

        if ndims is None:
            raise ValueError('ndims class member not set.')

        sample = np.array([5.5,        -3.3,
                           0.,         -0.5,
                           3.3,        8.8,
                           -7.7,       6.0,
                           -4.0])

        weights = np.array([500.5,    -300.3,
                            0.01,      -0.5,
                            300.3,     800.8,
                            -700.7,    600.6,
                            -400.4])

        n_elems = len(sample)

        if ndims == 1:
            shape = (n_elems,)
        else:
            shape = (n_elems, ndims)

        self.sample = np.zeros(shape=shape, dtype=sample.dtype)
        if ndims == 1:
            self.sample = sample
        else:
            self.sample[..., ndims-1] = sample

        self.weights = weights

        # the tests are performed along one dimension,
        #   all the other bins indices along the other dimensions
        #   are expected to be 2
        # (e.g : when testing a 2D sample : [0, x] will go into
        # bin [2, y] because of the bin ranges [-2, 2] and n_bins = 4
        # for the first dimension)
        self.other_axes_index = 2
        self.bins_rng = np.repeat([[-2., 2.]], ndims, axis=0)
        self.bins_rng[ndims-1] = [-4., 6.]

        self.n_bins = np.array([4]*ndims)
        self.n_bins[ndims-1] = 5

        if ndims == 1:
            def fill_histo(h, v, dim, op=None):
                if op:
                    h[:] = op(h[:], v)
                else:
                    h[:] = v
            self.fill_histo = fill_histo
        else:
            def fill_histo(h, v, dim, op=None):
                idx = [self.other_axes_index]*len(h.shape)
                idx[dim] = slice(0, None)
                if op:
                    h[idx] = op(h[idx], v)
                else:
                    h[idx] = v
            self.fill_histo = fill_histo

    def test_nominal(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo = Histogramnd(self.sample,
                            self.bins_rng,
                            self.n_bins,
                            weights=self.weights)
                            
        histo, cumul, bin_edges = histo

        expected_edges = _get_bin_edges(self.bins_rng,
                                        self.n_bins,
                                        self.ndims)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

        for i_edges, edges in enumerate(expected_edges):
            self.assertTrue(np.array_equal(bin_edges[i_edges],
                                           expected_edges[i_edges]),
                            msg='Testing bin_edges for dim {0}'
                                ''.format(i_edges+1))

    def test_nominal_wh_dtype(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.float32)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul, bin_edges = Histogramnd(self.sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=self.weights,
                                              wh_dtype=np.float32)

        self.assertEqual(cumul.dtype, np.float32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.allclose(cumul, expected_c))

    def test_nominal_uncontiguous_sample(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        shape = list(self.sample.shape)
        shape[0] *= 2
        sample = np.zeros(shape, dtype=self.sample.dtype)
        uncontig_sample = sample[::2, ...]
        uncontig_sample[:] = self.sample

        self.assertFalse(uncontig_sample.flags['C_CONTIGUOUS'],
                         msg='Making sure the array is not contiguous.')

        histo, cumul, bin_edges = Histogramnd(uncontig_sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=self.weights)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_nominal_uncontiguous_weights(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        shape = list(self.weights.shape)
        shape[0] *= 2
        weights = np.zeros(shape, dtype=self.weights.dtype)
        uncontig_weights = weights[::2, ...]
        uncontig_weights[:] = self.weights

        self.assertFalse(uncontig_weights.flags['C_CONTIGUOUS'],
                         msg='Making sure the array is not contiguous.')

        histo, cumul, bin_edges = Histogramnd(self.sample,
                                              self.bins_rng,
                                              self.n_bins,
                                              weights=uncontig_weights)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_nominal_wo_weights(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)

        histo, cumul = Histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=None)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(cumul is None)



    def test_nominal_last_bin_closed(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 2])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 1101.1])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = Histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights,
                                   last_bin_closed=True)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_int32_weights_double_weights_range(self):
        """
        """
        weight_min = -299.9  # ===> will be cast to -299
        weight_max = 499.9  # ===> will be cast to 499

        expected_h_tpl = np.array([0, 1, 1, 1, 0])
        expected_c_tpl = np.array([0., 0., 0., 300., 0.])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo, cumul = Histogramnd(self.sample,
                                   self.bins_rng,
                                   self.n_bins,
                                   weights=self.weights.astype(np.int32),
                                   weight_min=weight_min,
                                   weight_max=weight_max)[0:2]

        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

    def test_nominal_no_sample(self):
        """
        """

        histo_inst = Histogramnd(None,
                                 self.bins_rng,
                                 self.n_bins)

        histo, weighted_histo, edges = histo_inst

        self.assertIsNone(histo)
        self.assertIsNone(weighted_histo)
        self.assertIsNone(edges)
        self.assertIsNone(histo_inst.histo)
        self.assertIsNone(histo_inst.weighted_histo)
        self.assertIsNone(histo_inst.edges)

    def test_empty_init_accumulate(self):
        """
        """
        expected_h_tpl = np.array([2, 1, 1, 1, 1])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo_inst = Histogramnd(None,
                                 self.bins_rng,
                                 self.n_bins)

        histo_inst.accumulate(self.sample,
                              weights=self.weights)

        histo = histo_inst.histo
        cumul = histo_inst.weighted_histo
        bin_edges = histo_inst.edges

        expected_edges = _get_bin_edges(self.bins_rng,
                                        self.n_bins,
                                        self.ndims)

        self.assertEqual(cumul.dtype, np.float64)
        self.assertEqual(histo.dtype, np.uint32)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

        for i_edges, edges in enumerate(expected_edges):
            self.assertTrue(np.array_equal(bin_edges[i_edges],
                                           expected_edges[i_edges]),
                            msg='Testing bin_edges for dim {0}'
                                ''.format(i_edges+1))

    def test_accumulate(self):
        """
        """

        expected_h_tpl = np.array([2, 3, 2, 2, 2])
        expected_c_tpl = np.array([-700.7, -7007.5, -4.99, 300.4, 3503.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo_inst = Histogramnd(self.sample,
                                 self.bins_rng,
                                 self.n_bins,
                                 weights=self.weights)

        sample_2 = self.sample[:]
        if len(sample_2.shape) == 1:
            idx = [slice(0, None)]
        else:
            idx = [slice(0, None), self.tested_dim]

        sample_2[idx] += 2

        histo_inst.accumulate(sample_2,                   # <==== !!
                              weights=10 * self.weights)  # <==== !!

        histo = histo_inst.histo
        cumul = histo_inst.weighted_histo
        bin_edges = histo_inst.edges

        self.assertEqual(cumul.dtype, np.float64)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.allclose(cumul, expected_c, rtol=10e-15))

    def test_accumulate_no_weights(self):
        """
        """

        expected_h_tpl = np.array([2, 3, 2, 2, 2])
        expected_c_tpl = np.array([-700.7, -0.5, 0.01, 300.3, 500.5])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo_inst = Histogramnd(self.sample,
                                 self.bins_rng,
                                 self.n_bins,
                                 weights=self.weights)

        sample_2 = self.sample[:]
        if len(sample_2.shape) == 1:
            idx = [slice(0, None)]
        else:
            idx = [slice(0, None), self.tested_dim]

        sample_2[idx] += 2

        histo_inst.accumulate(sample_2)  # <==== !!

        histo = histo_inst.histo
        cumul = histo_inst.weighted_histo
        bin_edges = histo_inst.edges

        self.assertEqual(cumul.dtype, np.float64)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.allclose(cumul, expected_c, rtol=10e-15))


    def test_accumulate_no_weights_at_init(self):
        """
        """

        expected_h_tpl = np.array([2, 3, 2, 2, 2])
        expected_c_tpl = np.array([0.0, -700.7, -0.5, 0.01, 300.3])

        expected_h = np.zeros(shape=self.n_bins, dtype=np.double)
        expected_c = np.zeros(shape=self.n_bins, dtype=np.double)

        self.fill_histo(expected_h, expected_h_tpl, self.ndims-1)
        self.fill_histo(expected_c, expected_c_tpl, self.ndims-1)

        histo_inst = Histogramnd(self.sample,
                                 self.bins_rng,
                                 self.n_bins,
                                 weights=None)  # <==== !!

        cumul = histo_inst.weighted_histo
        self.assertIsNone(cumul)

        sample_2 = self.sample[:]
        if len(sample_2.shape) == 1:
            idx = [slice(0, None)]
        else:
            idx = [slice(0, None), self.tested_dim]

        sample_2[idx] += 2

        histo_inst.accumulate(sample_2,
                              weights=self.weights)  # <==== !!

        histo = histo_inst.histo
        cumul = histo_inst.weighted_histo
        bin_edges = histo_inst.edges

        self.assertEqual(cumul.dtype, np.float64)
        self.assertTrue(np.array_equal(histo, expected_h))
        self.assertTrue(np.array_equal(cumul, expected_c))

class Test_chistogram_nominal_1d(_Test_chistogramnd_nominal):
    ndims = 1


class Test_chistogram_nominal_2d(_Test_chistogramnd_nominal):
    ndims = 2


class Test_chistogram_nominal_3d(_Test_chistogramnd_nominal):
    ndims = 3


class Test_Histogramnd_nominal_1d(_Test_Histogramnd_nominal):
    ndims = 1


class Test_Histogramnd_nominal_2d(_Test_Histogramnd_nominal):
    ndims = 2


class Test_Histogramnd_nominal_3d(_Test_Histogramnd_nominal):
    ndims = 3


# ==============================================================
# ==============================================================
# ==============================================================


test_cases = (Test_chistogram_nominal_1d,
              Test_chistogram_nominal_2d,
              Test_chistogram_nominal_3d,
              Test_Histogramnd_nominal_1d,)
              #Test_Histogramnd_nominal_2d,
              #Test_Histogramnd_nominal_3d)


def suite():
    loader = unittest.defaultTestLoader
    test_suite = unittest.TestSuite()
    for test_class in test_cases:
        tests = loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    return test_suite

if __name__ == '__main__':
    unittest.main(defaultTest="suite")
