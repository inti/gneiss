# ----------------------------------------------------------------------------
# Copyright (c) 2016--, gneiss development team.
#
# Distributed under the terms of the GPLv3 License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# ----------------------------------------------------------------------------
import numpy as np
import pandas as pd
from functools import partial
from gneiss.util import match


def mean_niche_estimator(abundances, gradient):
    """ Estimates the mean niche of an organism.

    Calculates the mean niche of an organism along a gradient.
    This is done by calculating the expected value of an organism
    across the gradient.

    Specifically, this module calculates the following

    .. math::
        E[g | x] =
         \sum\limits_{i=1}^N g_i \frac{x_i}{\sum\limits_{j=1}^N x_j}

    Where :math:`N` is the number of samples, :math:`x_i` is the proportion of
    species :math:`x` in sample :math:`i`, :math:`g_i` is the gradient value
    at sample `i`.

    Parameters
    ----------
    abundances : pd.Series, np.float
        Vector of fraction abundances of an organism over
        a list of samples.
    gradient : pd.Series, np.float
        Vector of numerical gradient values.

    Returns
    -------
    np.float :
        The mean gradient that the organism lives in.

    Raises
    ------
    ValueError:
        If the length of `abundances` is not the same length as `gradient`.
    ValueError:
        If the length of `gradient` contains nans.
    """
    len_abundances = len(abundances)
    len_gradient = len(gradient)
    if len_abundances != len_gradient:
        raise ValueError("Length of `abundances` (%d) doesn't match the length"
                         " of the `gradient` (%d)" % (len_abundances,
                                                      len_gradient))
    if np.any(pd.isnull(gradient)):
        raise ValueError("`gradient` cannot have any nans.")

    # normalizes the proportions of the organism across all of the
    # samples to add to 1.
    v = abundances / abundances.sum()
    m = np.dot(gradient, v)
    return m


def niche_sort(table, gradient, niche_estimator=mean_niche_estimator):
    """ Sort the table according to estimated niches.

    Sorts the table by samples along the gradient
    and otus by their estimated niche along the gradient.

    Parameters
    ----------
    table : pd.DataFrame
        Contingency table where samples are rows and
        features (i.e. OTUs) are columns.
    gradient : pd.Series
        Vector of numerical gradient values.
    niche_estimator : function, optional
        A function that takes in two pandas series and returns an ordered
        object. The ability for the object to be ordered is critical, since
        this will allow the table to be sorted according to this ordering.
        By default, `mean_niche_estimator` will be used.

    Returns
    -------
    pd.DataFrame :
        Sorted table according to the gradient of the samples, and the niches
        of the organisms along that gradient.

    Raises
    ------
    ValueError :
        Raised if `niche_estimator` is not a function.
    """
    if not callable(niche_estimator):
        raise ValueError("`niche_estimator` is not a function.")

    table, gradient = match(table, gradient)

    niche_estimator = partial(niche_estimator,
                              gradient=gradient)

    # normalizes feature abundances to sum to 1, for each sample.
    # (i.e. scales values in each row to sum to 1).
    normtable = table.apply(lambda x: x/x.sum(), axis=1)

    # calculates estimated niche for each feature
    est_niche = normtable.apply(niche_estimator, axis=0)
    gradient = gradient.sort_values()
    est_niche = est_niche.sort_values()

    table = table.reindex(index=gradient.index,
                          columns=est_niche.index)
    return table


def ladderize(tree, ascending=True):
    """
    Sorts tree according to the size of the subtrees.

    Parameters
    ----------
    tree : skbio.TreeNode
       Input tree where leafs correspond to features
       contained in the index in `grouping1.
    gradient : pd.Series
       Gradient where the index correspond to features.

    Returns
    -------
    skbio.TreeNode
       A tree whose tips are sorted along the gradient.

    Examples
    --------
    >>> from skbio import TreeNode
    >>> tree = TreeNode.read([u'((a,b)c, ((g,h)e,f)d)r;'])
    >>> print(tree.ascii_art())
                        /-a
              /c-------|
             |          \-b
    -r-------|
             |                    /-g
             |          /e-------|
              \d-------|          \-h
                       |
                        \-f
    >>> sorted_tree = ladderize(tree)
    >>> print(sorted_tree.ascii_art())
                        /-a
              /c-------|
             |          \-b
    -r-------|
             |          /-f
              \d-------|
                       |          /-g
                        \e-------|
                                  \-h
    """
    sorted_tree = tree.copy()
    # Note that this is an extremely slow
    # See https://github.com/biocore/gneiss/issues/58
    for n in sorted_tree.postorder(include_self=True):
        sizes = [len(list(k.tips())) for k in n.children]
        if ascending:
            idx = np.argsort(sizes)
        else:
            idx = np.argsort(sizes)[::-1]
        n.children = [n.children[i] for i in idx]
    return sorted_tree


def order_tips(tree, gradient, ascending=True):
    """
    Sorts tree according to ordering in tree.

    Parameters
    ----------
    tree : skbio.TreeNode
       Input tree where leafs correspond to features
       contained in the index in `gradient`.
    gradient : pd.Series
       Gradient where the index correspond to feature names.
       The index in the gradient must be consistent with
       names of the tips in the `tree`.

    Returns
    -------
    skbio.TreeNode
       A tree whose tips are sorted along the gradient.

    Examples
    --------
    >>> from skbio import TreeNode
    >>> import pandas as pd
    >>> tree = TreeNode.read([u'((a,b)c, ((g,h)e,f)d)r;'])
    >>> x = pd.Series({'f':3, 'g':1, 'h':2, 'a':4, 'b':5})
    >>> print(tree.ascii_art())
                        /-a
              /c-------|
             |          \-b
    -r-------|
             |                    /-g
             |          /e-------|
              \d-------|          \-h
                       |
                        \-f
    >>> res = order_tips(tree, x)
    >>> print(res.ascii_art())
                                  /-g
                        /e-------|
              /d-------|          \-h
             |         |
    -r-------|          \-f
             |
             |          /-a
              \c-------|
                        \-b
    """
    sorted_tree = tree.copy()
    # Note that this is an extremely slow
    # See https://github.com/biocore/gneiss/issues/58
    for n in sorted_tree.postorder(include_self=True):
        means = [gradient.loc[list(k.subset())].mean() for k in n.children]
        if ascending:
            idx = np.argsort(means)
        else:
            idx = np.argsort(means)[::-1]
        n.children = [n.children[i] for i in idx]
    return sorted_tree
