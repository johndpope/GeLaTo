# coding: utf-8

# TODO add action of diff operators on sympy known functions

import numpy as np
from itertools import groupby
from collections import OrderedDict

#from sympy.core.sympify import sympify
from sympy.simplify.simplify import simplify
from sympy import Symbol
from sympy import Lambda
from sympy import Function
from sympy import bspline_basis
from sympy import lambdify
from sympy import cos
from sympy import sin
from sympy import Rational
from sympy import diff
from sympy import Matrix, ImmutableDenseMatrix
from sympy import latex
from sympy import Integral
from sympy import I as sympy_I
from sympy.core import Basic
from sympy.core.singleton import S
from sympy.simplify.simplify import nsimplify
from sympy.utilities.lambdify import implemented_function
from sympy.matrices.dense import MutableDenseMatrix
from sympy import Mul, Add
from sympy import postorder_traversal
from sympy import preorder_traversal

from sympy.core.expr import Expr
from sympy.core.containers import Tuple
from sympy import Integer, Float

from sympy import Add, Mul
from sympy import preorder_traversal, Expr
from sympy import simplify
from sympy import S
from sympy.core.compatibility import is_sequence
from sympy import Basic
from sympy import Indexed, IndexedBase

# ...
class LinearOperator(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Grad'
    is_commutative = True

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        expr = _args[0]
        if isinstance(expr, Add):
            args = expr.args
            args = [cls.eval(a) for a in expr.args]
            return Add(*args)

        if isinstance(expr, Mul):
            coeffs  = [a for a in expr.args if isinstance(a, _coeffs_registery)]
            vectors = [a for a in expr.args if not(a in coeffs)]

            a = S.One
            if coeffs:
                a = Mul(*coeffs)

            b = S.One
            if vectors:
                b = cls(Mul(*vectors), evaluate=False)

            return Mul(a, b)

        return cls(expr, evaluate=False)
# ...

# ...
class DifferentialOperator(LinearOperator):
    """
    This class is a linear operator that applies the Leibniz formula

    Examples
    ========

    """
    coordinate = None

    @classmethod
    def eval(cls, *_args):
        """."""

        expr = _args[0]
        if isinstance(expr, Add):
            args = expr.args
            args = [cls.eval(a) for a in expr.args]
            return Add(*args)

        if isinstance(expr, Mul):
            coeffs  = [a for a in expr.args if isinstance(a, _coeffs_registery)]
            vectors = [a for a in expr.args if not(a in coeffs)]

            c = S.One
            if coeffs:
                c = Mul(*coeffs)

            V = S.One
            if vectors:
                if len(vectors) == 1:
                    V = cls(Mul(vectors[0]), evaluate=False)

                elif len(vectors) == 2:
                    a = vectors[0]
                    b = vectors[1]

                    fa = cls(a, evaluate=False)
                    fb = cls(b, evaluate=False)

                    V = a * fb + fa * b

                else:
                    V = cls(Mul(*vectors), evaluate=False)

            return Mul(c, V)

        return cls(expr, evaluate=False)
# ...

# ...
class dx(DifferentialOperator):
    coordinate = 'x'
    grad_index = 0 # index in grad
    pass

class dy(DifferentialOperator):
    coordinate = 'y'
    grad_index = 1 # index in grad
    pass

class dz(DifferentialOperator):
    coordinate = 'z'
    grad_index = 2 # index in grad
    pass

_partial_derivatives = (dx, dy, dz)
# ...

# ...
def find_partial_derivatives(expr):
    """
    returns all partial derivative expressions
    """
    if isinstance(expr, (Add, Mul)):
        return find_partial_derivatives(expr.args)

    elif isinstance(expr, (list, tuple, Tuple)):
        args = []
        for a in expr:
            args += find_partial_derivatives(a)
        return args

    elif isinstance(expr, _partial_derivatives):
        return [expr]

    return []
# ...

# ...
def get_number_derivatives(expr):
    """
    returns the number of partial derivatives in expr.
    this is still an experimental version, and it assumes that expr is of the
    form d(a) where a is a single atom.
    """
    n = 0
    if isinstance(expr, _partial_derivatives):
        assert(len(expr.args) == 1)

        n += 1 + get_number_derivatives(expr.args[0])
    return n
# ...

# ...
def sort_partial_derivatives(expr):
    """returns the partial derivatives of an expression, sorted.
    """
    ls = []

    args = find_partial_derivatives(expr)

#    # ... Note
#    #     group by is given the wrong answer for expr =mu * u + dx(u) + dx(dx(u))
#    for key, group in groupby(args, lambda x: get_number_derivatives(x)):
#        g = [a for a in group]
#        for a in group:
#            ls.append(a)
#    # ...

    # ...
    d = {}
    for a in args:
        n = get_number_derivatives(a)
        if n in d.keys():
            d[n] += [a]
        else:
            d[n] = [a]
    # ...

    # ...
    if not d:
        return []
    # ...

    # ... sort keys from high to low
    keys = np.asarray(list(d.keys()))
    keys.sort()
    keys = keys[::-1]
    # ...

    # ... construct a list of partial derivatives from high to low order
    ls = []
    for k in keys:
        ls += d[k]
    # ...

    return ls
# ...

# ...
def get_index_derivatives(expr):
    """
    """
    coord = ['x','y','z']

    d = OrderedDict()
    for c in coord:
        d[c] = 0

    ops = [a for a in preorder_traversal(expr) if isinstance(a, _partial_derivatives)]
    for i in ops:
        op = type(i)

        if isinstance(i, dx):
            d['x'] += 1

        elif isinstance(i, dy):
            d['y'] += 1

        elif isinstance(i, dz):
            d['z'] += 1

    return d
# ...

# ...
def get_atom_derivatives(expr):
    """
    """

    if isinstance(expr, _partial_derivatives):
        assert(len(expr.args) == 1)

        return get_atom_derivatives(expr.args[0])

    elif isinstance(expr, _calculus_operators):
        raise TypeError('remove this raise later')

    else:
        return expr
# ...


# ...
class DotBasic(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Dot'

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

class Dot_1d(DotBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        if not( len(_args) == 2):
            raise ValueError('Expecting two arguments')

        u = _args[0]
        v = _args[1]

        return u * v

class Dot_2d(DotBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        if not( len(_args) == 2):
            raise ValueError('Expecting two arguments')

        u = _args[0]
        v = _args[1]

        if isinstance(u, (Matrix, ImmutableDenseMatrix)):
            if isinstance(v, (Matrix, ImmutableDenseMatrix)):
                raise NotImplementedError('TODO')

            else:
                return Tuple(u[0,0]*v[0] + u[0,1]*v[1], u[1,0]*v[0] + u[1,1]*v[1])

        else:
            if isinstance(v, (Matrix, ImmutableDenseMatrix)):
                raise NotImplementedError('TODO')

            else:
                return u[0]*v[0] + u[1]*v[1]

class Dot_3d(DotBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        if not( len(_args) == 2):
            raise ValueError('Expecting two arguments')

        u = _args[0]
        v = _args[1]

        if isinstance(u, (Matrix, ImmutableDenseMatrix)):
            if isinstance(v, (Matrix, ImmutableDenseMatrix)):
                raise NotImplementedError('TODO')

            else:
                return Tuple(u[0,0]*v[0] + u[0,1]*v[1] + u[0,2]*v[2],
                             u[1,0]*v[0] + u[1,1]*v[1] + u[1,2]*v[2],
                             u[2,0]*v[0] + u[2,1]*v[1] + u[2,2]*v[2])

        else:
            if isinstance(v, (Matrix, ImmutableDenseMatrix)):
                raise NotImplementedError('TODO')

            else:
                return u[0]*v[0] + u[1]*v[1] + u[2]*v[2]
# ...

# ...
class CrossBasic(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Cross'

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

class Cross_2d(CrossBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]
        v = _args[1]

        return u[0]*v[1] - u[1]*v[0]

class Cross_3d(CrossBasic):
    """

    Examples
    ========

    """

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]
        v = _args[1]

        return Tuple(u[1]*v[2] - u[2]*v[1],
                     u[2]*v[0] - u[0]*v[2],
                     u[0]*v[1] - u[1]*v[0])
# ...


# ...
class GradBasic(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Grad'

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

class Grad_1d(GradBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return dx(u)

class Grad_2d(GradBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return Tuple(dx(u), dy(u))

class Grad_3d(GradBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return Tuple(dx(u), dy(u), dz(u))
# ...


# ...
class CurlBasic(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Curl'

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

class Curl_2d(CurlBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return Tuple( dy(u),
                     -dx(u))

class Curl_3d(CurlBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return Tuple(dy(u[2]) - dz(u[1]),
                     dz(u[0]) - dx(u[2]),
                     dx(u[1]) - dy(u[0]))
# ...

# ...
class Rot_2d(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Grad'

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return dy(u[0]) - dx(u[1])
# ...

# ...
class DivBasic(CalculusFunction):
    """

    Examples
    ========

    """

    nargs = None
    name = 'Div'

    def __new__(cls, *args, **options):
        # (Try to) sympify args first

        if options.pop('evaluate', True):
            r = cls.eval(*args)
        else:
            r = None

        if r is None:
            return Basic.__new__(cls, *args, **options)
        else:
            return r

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

class Div_1d(DivBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return dx(u)

class Div_2d(DivBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return dx(u[0]) + dy(u[1])

class Div_3d(DivBasic):
    """

    Examples
    ========

    """

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        u = _args[0]

        return dx(u[0]) + dy(u[1]) + dz(u[2])
# ...


# ...
_coord_registery = ['x', 'y', 'z']
# ...

# ...
_operators_1d = [Dot_1d,
                 Grad_1d, Div_1d]

_operators_2d = [Dot_2d, Cross_2d,
                 Grad_2d, Curl_2d, Rot_2d, Div_2d]

_operators_3d = [Dot_3d, Cross_3d,
                 Grad_3d, Curl_3d, Div_3d]
# ...


# ... generic operators
class GenericFunction(CalculusFunction):

    def __getitem__(self, indices, **kw_args):
        if is_sequence(indices):
            # Special case needed because M[*my_tuple] is a syntax error.
            return Indexed(self, *indices, **kw_args)
        else:
            return Indexed(self, indices, **kw_args)

class Dot(GenericFunction):
    pass

class Cross(GenericFunction):
    pass

class Grad(GenericFunction):
    pass

class Curl(GenericFunction):
    pass

class Rot(GenericFunction):
    pass

class Div(GenericFunction):
    pass

_generic_ops  = (Dot, Cross,
                 Grad, Curl, Rot, Div)
# ...

# ... alias for ufl compatibility
cross = Cross
dot = Dot

Inner = Dot # TODO do we need to add the Inner class Function?
inner = Inner

grad = Grad
curl = Curl
rot = Rot
div = Div

_calculus_operators = (Grad, Dot, Inner, Cross, Rot, Curl, Div)
# ...

# ...
def partial_derivative_as_symbol(expr, name=None, dim=None):
    """Returns a Symbol from a partial derivative expression."""
    if not isinstance(expr, _partial_derivatives):
        raise TypeError('Expecting a partial derivative expression')

    index = get_index_derivatives(expr)
    var = get_atom_derivatives(expr)

    if not isinstance(var, (Symbol, Indexed)):
        print(type(var))
        raise TypeError('Expecting a Symbol, Indexed')

    code = ''
    for k,n in list(index.items()):
        code += k*n

    if var.is_Indexed:
        if name is None:
            name = var.base

        indices = ''.join('{}'.format(i) for i in var.indices)
        name = '{name}_{code}'.format(name=name, code=code)
        shape = None
        if dim:
            shape = [dim]
        return IndexedBase(name, shape=shape)[indices]

    else:
        if name is None:
            name = var.name

        name = '{name}_{code}'.format(name=name, code=code)
        return Symbol(name)
# ...
