# coding: utf-8

# TODO: - allow for giving a name for the trial/test basis
#       - Ni/Nj should be Ni_0/Nj_O

from numpy import linspace

from sympy.core.containers import Tuple
from sympy import symbols
from sympy import Symbol
from sympy import Lambda

from gelato.expression   import construct_weak_form
from gelato.calculus     import (Dot, Cross, Grad, Curl, Rot, Div)
from gelato.calculus     import Constant
from gelato.fem.assembly import assemble_matrix
from gelato.fem.utils    import compile_kernel

from spl.fem.splines import SplineSpace
from spl.fem.tensor  import TensorSpace

# ...
def test_3d_1():
    # ... define the weak formulation
    x,y,z = symbols('x y z')

    u = Symbol('u')
    v = Symbol('v')

    expr = Lambda((x,y,z,v,u), Dot(Grad(u), Grad(v)) + u*v)
    # ...

    # ...  create a finite element space
    p1  = 2 ; p2  = 2 ; p3  = 2
    ne1 = 2 ; ne2 = 2 ; ne3 = 2
    # ...

    print('> Grid   :: [{},{},{}]'.format(ne1, ne2, ne3))
    print('> Degree :: [{},{},{}]'.format(p1, p2, p3))

    grid_1 = linspace(0., 1., ne1+1)
    grid_2 = linspace(0., 1., ne2+1)
    grid_3 = linspace(0., 1., ne3+1)

    V1 = SplineSpace(p1, grid=grid_1)
    V2 = SplineSpace(p2, grid=grid_2)
    V3 = SplineSpace(p3, grid=grid_3)

    V = TensorSpace(V1, V2, V3)
    # ...

    # ...
    kernel_py  = compile_kernel('kernel_1', expr, V, backend='python')
    kernel_f90 = compile_kernel('kernel_1', expr, V, backend='fortran')

    M_py  = assemble_matrix(V, kernel_py).tocsr()
    M_f90 = assemble_matrix(V, kernel_f90).tocsr()
    # ...

# ...

# ...
def test_3d_2():
    # ... define the weak formulation
    x,y,z = symbols('x y z')

    u = Symbol('u')
    v = Symbol('v')

    alpha = Symbol('alpha')
    nu = Symbol('nu')

    expr = Lambda((x,v,u), alpha * Dot(Grad(u), Grad(v)) + nu*u*v)
    # ...

    # ...  create a finite element space
    p1  = 2 ; p2  = 2 ; p3  = 2
    ne1 = 2 ; ne2 = 2 ; ne3 = 2
    # ...

    print('> Grid   :: [{},{},{}]'.format(ne1, ne2, ne3))
    print('> Degree :: [{},{},{}]'.format(p1, p2, p3))

    grid_1 = linspace(0., 1., ne1+1)
    grid_2 = linspace(0., 1., ne2+1)
    grid_3 = linspace(0., 1., ne3+1)

    V1 = SplineSpace(p1, grid=grid_1)
    V2 = SplineSpace(p2, grid=grid_2)
    V3 = SplineSpace(p3, grid=grid_3)

    V = TensorSpace(V1, V2, V3)
    # ...

    # ...
    kernel_py  = compile_kernel('kernel_2', expr, V,
                                d_constants={'nu': 0.1},
                                d_args={'alpha': 'double'},
                                backend='python')
    kernel_f90 = compile_kernel('kernel_2', expr, V,
                                d_constants={'nu': 0.1},
                                d_args={'alpha': 'double'},
                                backend='fortran')

    M_py  = assemble_matrix(V, kernel_py, args={'alpha': 2.0}).tocsr()
    M_f90 = assemble_matrix(V, kernel_f90, args={'alpha': 2.0}).tocsr()
    # ...

# ...


# .....................................................
if __name__ == '__main__':

    test_3d_1()
    test_3d_2()