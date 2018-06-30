# coding: utf-8

from numpy import allclose

def assert_identical_coo(A, B):

    if isinstance(A, (list, tuple)) and isinstance(B, (list, tuple)):
        assert len(A) == len(B)

        for a,b in zip(A, B): assert_identical_coo(a, b)

    elif not(isinstance(A, (list, tuple))) and not(isinstance(B, (list, tuple))):
        A = A.tocoo()
        B = B.tocoo()

        assert(A.shape == B.shape)
        assert(A.nnz == B.nnz)

        assert(allclose(A.row,  B.row))
        assert(allclose(A.col,  B.col))
        assert(allclose(A.data, B.data))

#        assert(allclose(A.todense(), B.todense()))

    else:
        raise TypeError('Wrong types for entries')
