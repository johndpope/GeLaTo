# -*- coding: utf-8 -*-
#
#
# TODO use to_assign and post processing as expression and not latex => helpful
#      for Fortran and Lua (code gen).
"""This module contains different functions to create and treate the GLT symbols."""

import numpy as np

from sympy.core.sympify import sympify
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
from sympy import Matrix
from sympy import latex
from sympy import Integral
from sympy import I as sympy_I
from sympy.core import Basic
from sympy.core.singleton import S
from sympy.simplify.simplify import nsimplify
from sympy.utilities.lambdify import implemented_function
from sympy.matrices.dense import MutableDenseMatrix
from sympy import Mul, Add
from sympy import Tuple
from sympy import postorder_traversal
from sympy import preorder_traversal
from sympy import Indexed
from sympy import IndexedBase
from sympy import Lambda

from itertools import product

from scipy.linalg import eig

from gelato.calculus import (Dot_1d, Grad_1d, Div_1d)
from gelato.calculus import (Dot_2d, Cross_2d, Grad_2d, Curl_2d, Rot_2d, Div_2d)
from gelato.calculus import (Dot_3d, Cross_3d, Grad_3d, Curl_3d, Div_3d)
from gelato.expression import construct_weak_form

try:
    from pyccel.ast.core import Variable
    ENABLE_PYCCEL = True
except:
    ENABLE_PYCCEL = False


# TODO find a better solution.
#      this code is duplicated in printing.latex
ARGS_x       = ["x", "y", "z"]
ARGS_u       = ["u", "v", "w"]
ARGS_s       = ["s", "ss"]
BASIS_TEST   = "Ni"
BASIS_TRIAL  = "Nj"
BASIS_PREFIX = ["x", "y", "z", "xx", "yy", "zz", "xy", "yz", "xz"]
TOLERANCE    = 1.e-10
#TOLERANCE    = 1.e-4
SETTINGS     = ["glt_integrate", "glt_formatting", "glt_formatting_atoms"]


# ...
_coord_registery = ['x', 'y', 'z']

# ...
def basis_symbols(dim, n_deriv=1):
    """
    Returns a dictionary that contains sympy symbols for the basis and their
    derivatives. The kind of a basis function can be trial or test.

    dim: int
        dimension of the logical/physical domain.

    n_deriv: int
        number of derivatives
    """
    # ...
    args_x = ARGS_x[:dim]
    # ...

    # ...
    words = []
    for i_deriv in range(1, n_deriv+1):
        words += [''.join(i) for i in product(args_x, repeat = i_deriv)]
    # ...

    # ...
    ops = [o for o in words if o in BASIS_PREFIX]
    # ...

    # ...
    ns = {}

    for B in [BASIS_TEST, BASIS_TRIAL]:
        ns[B] = Symbol(B)
        for d in ops:
            B_d = B + "_" + d
            ns[B_d] = Symbol(B_d)
    # ...

    return ns
# ...

# ...
def apply_mapping(expr, dim, instructions=None, **settings):
    """
    Applies a mapping to a given expression

    expr: sympy.Expression
        a sympy expression

    dim: int
        dimension of the logical/physical domain.

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings
    """
    # ...
    args_x = ARGS_x[:dim]
    args_u = ARGS_u[:dim]
    for B in [BASIS_TEST, BASIS_TRIAL]:
        for (x,u) in zip(args_x, args_u):
            B_x = B + "_" + x
            B_u = B + "_" + u
            expr = expr.subs({Symbol(B_x): Symbol(B_u)})
    # ...

    # ... updates the latex expression
    if instructions is not None:
        sets = {}
        for key, value in list(settings.items()):
            sets[key] = value
        sets["mode"] = "equation*"

        instructions.append(glt_latex(expr, **sets))
    # ...

    return expr
# ...

# ...
def apply_tensor(expr, dim, instructions=None, **settings):
    """
    decomposes the basis function to their tensor form

    expr:
        a sympy expression

    dim: int
        dimension of the logical/physical domain.

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings
    """
    args_u = ARGS_u[:dim]
    for B in [BASIS_TEST, BASIS_TRIAL]:
        # ... substruct the basis function
        prod = S.One
        for k in range(0, dim):
            Bk_u = B + str(k+1)
            prod *= Symbol(Bk_u)
        expr = expr.subs({Symbol(B): prod})
        # ...

        # ... substruct the derivatives
        for i,u in enumerate(args_u):
            B_u = B + "_" + u
            prod = S.One
            for k in range(0, dim):
                if k==i:
                    Bk_u = B + str(k+1) + "_s"
                else:
                    Bk_u = B + str(k+1)
                prod *= Symbol(Bk_u)
            expr = expr.subs({Symbol(B_u): prod})
        # ...

    # ... updates the latex expression
    if instructions is not None:
        sets = {}
        for key, value in list(settings.items()):
            sets[key] = value
        sets["mode"] = "equation*"

        instructions.append(glt_latex(expr, **sets))
    # ...

    return expr
# ...

# ...
def apply_factor(expr, dim, instructions=None, **settings):
    """
    factorizes the basis function by coupling the trial/test functions related
    to the same tensor index.

    expr:
        a sympy expression

    dim: int
        dimension of the logical/physical domain.

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings
    """
    Bi = BASIS_TEST
    Bj = BASIS_TRIAL

    for k in range(0, dim):
        # ... mass symbol
        Bik = Bi + str(k+1)
        Bjk = Bj + str(k+1)
        P = Symbol(Bik) * Symbol(Bjk)
        mk = Symbol("m"+str(k+1))

        expr = expr.subs({P: mk})
        # ...

        # ... stiffness symbol
        Bik = Bi + str(k+1) + "_s"
        Bjk = Bj + str(k+1) + "_s"
        P = Symbol(Bik) * Symbol(Bjk)
        sk = Symbol("s"+str(k+1))

        expr = expr.subs({P: sk})
        # ...

        # ... advection symbol
        Bik = Bi + str(k+1)
        Bjk = Bj + str(k+1) + "_s"
        P = Symbol(Bik) * Symbol(Bjk)
        ak = Symbol("a"+str(k+1))

        expr = expr.subs({P: ak})
        # ...

        # ... adjoint advection symbol
        Bik = Bi + str(k+1) + "_s"
        Bjk = Bj + str(k+1)
        P = Symbol(Bik) * Symbol(Bjk)
        ak = Symbol("a"+str(k+1))

        expr = expr.subs({P: -ak})
        # ...

    # ... updates the latex expression
    if instructions is not None:
        # ...
        instruction = "The symbol is then:"
        instructions.append(instruction)
        # ...

        # ...
        sets = {}
        for key, value in list(settings.items()):
            if not(key == "glt_integrate"):
                sets[key] = value
        sets["mode"] = "equation*"

        instructions.append(glt_latex(expr, **sets))
        # ...
    # ...

    return expr
# ...

# ...
def glt_update_atoms(expr, discretization):
    """
    updates the glt symbol with the atomic symbols

    expr:
        a sympy expression

    discretization: dict
        a dictionary that contains the used discretization
    """
    # ...
    dim = len(discretization["n_elements"])
    # ...

    # ...
    args = _coord_registery[:dim]
    args = [Symbol(i) for i in args]
    # ...

    # ...
    for k in range(0, dim):
        # ...
        t = Symbol('t'+str(k+1))

        n = discretization["n_elements"][k]
        p = discretization["degrees"][k]

        m   = glt_symbol_m(n,p,t)
        s   = glt_symbol_s(n,p,t)
        a   = glt_symbol_a(n,p,t)
        t_a = -a
        # ...

        # ...
        expr = expr.subs({Symbol('m'+str(k+1)): m})
        expr = expr.subs({Symbol('s'+str(k+1)): s})
        expr = expr.subs({Symbol('a'+str(k+1)): a})
        expr = expr.subs({Symbol('t_a'+str(k+1)): t_a})
        # ...

        # ...
        args += [t]
        # ...
    # ...

    return Lambda(args, expr)
# ...

# ...
def glt_symbol(expr,
               n_deriv=1,
               space=None,
               verbose=False,
               evaluate=False,
               is_block=False,
               discretization=None,
               instructions=[], **settings):
    """
    computes the glt symbol of a weak formulation given as a sympy expression.

    expr: sympy.Expression
        a sympy expression or a text

    space: spl.fem.SplineSpace, spl.fem.TensorSpace, spl.fem.VectorFemSpace
        a Finite elements space from spl. Default: None

    n_deriv: int
        maximum derivatives that appear in the weak formulation.

    verbose: bool
        talk more

    evaluate: bool
        causes the evaluation of the atomic symbols, if true

    is_block: bool
        treat a block prolbem if True. Must be supplied only when using
        discretization. Otherwise, the fem space should be consistent with the
        weak formulation.

    discretization: dict
        a dictionary that contains the used discretization

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings

    """
    # ...
    if not isinstance(expr, Lambda):
        raise TypeError('Expecting a Lambda expression')
    # ...

    # ...
    if not( discretization is None ):
        dim = len(discretization['n_elements'])

    elif not( space is None ):
        dim = space.pdim

        n_elements = space.ncells
        if not( isinstance(n_elements, (list, tuple))): n_elements = [n_elements]

        degrees = space.degree
        if not( isinstance(degrees, (list, tuple))): degrees = [degrees]

        discretization = {'n_elements': n_elements, 'degrees': degrees}

        from spl.fem.vector  import VectorFemSpace
        is_block = isinstance(space, VectorFemSpace)

        if is_block:
            # TODO make sure all degrees are the same?
            #      or remove discretization and use only the space
            discretization['degrees'] = degrees[0]

        # TODO check that the weak form is consistent with the space (both are blocks)

    else:
        raise ValueError('discretization (dict) or fem space must be given')
    # ...

    # ...
    expr = construct_weak_form(expr, dim=dim, is_block=is_block, verbose=verbose)
    # ...

    # ...
    if verbose:
        print(("*** Input expression : ", expr))
    # ...

    # ...
    if type(expr) == dict:
        d_expr = {}
        for key, txt in list(expr.items()):
            # ... when using vale, we may get also a coefficient.
            if type(txt) == list:
                txt = str(txt[0]) + " * (" + txt[1] + ")"
            # ...

            # ...
            title  = "Computing the GLT symbol for the block " + str(key)
            instructions.append(latex_title_as_paragraph(title))
            # ...

            # ...
            d_expr[key] = glt_symbol(txt,
                                     n_deriv=n_deriv,
                                     verbose=verbose,
                                     evaluate=evaluate,
                                     discretization=discretization,
                                     instructions=instructions,
                                     **settings)
            # ...

        if len(d_expr) == 1:
            key = d_expr.keys()[0]
            return d_expr[key]

        return dict_to_matrix(d_expr, instructions=instructions, **settings)
    else:
        # ...
        ns = {}
        # ...

        # ...
        d = basis_symbols(dim, n_deriv)
        for key, item in list(d.items()):
            ns[key] = item
        # ...

        # ...
        if isinstance(expr, Lambda):
            expr = normalize_weak_from(expr)
        # ...

        # ...
        expr = sympify(expr, locals=ns)
        expr = expr.expand()
        # ...
    # ...

    # ...
    if verbose:
        # ...
        instruction = "We consider the following weak formulation:"
        instructions.append(instruction)
        instructions.append(glt_latex(expr, **settings))
        # ...

        print((">>> weak formulation: ", expr))
    # ...

    # ...
    expr = apply_mapping(expr, dim=dim, \
                         instructions=instructions, \
                         **settings)
    if verbose:
        print(expr)
    # ...

    # ...
    expr = apply_tensor(expr, dim=dim, \
                         instructions=instructions, \
                         **settings)
    if verbose:
        print(expr)
    # ...

    # ...
    expr = apply_factor(expr, dim, \
                         instructions=instructions, \
                         **settings)
    if verbose:
        print(expr)
    # ...

    # ...
    if not evaluate:
        return expr
    # ...

    # ...
    if not discretization:
        return expr
    # ...

    # ...
    expr = glt_update_atoms(expr, discretization)
    # ...

    return expr
# ...

# ...
def glt_lambdify(expr):
    """
    it is supposed that glt_symbol has been called before.

    expr: sympy.Expression
        a sympy expression or a text
    """
    if not isinstance(expr, Lambda):
        raise TypeError('Expecting a Lambda expression')

    return lambdify(expr.variables, expr.expr, "numpy")
# ...

# ... TODO: use pyccel rather than lambdify
def glt_approximate_eigenvalues(expr,
                                space=None,
                                discretization=None,
                                mapping=None,
                                is_block=False,
                                symbolic_eigen=False):
    """
    approximates the eigenvalues using a uniform sampling

    expr: sympy.Expression
        a sympy expression or a text

    space: spl.fem.SplineSpace, spl.fem.TensorSpace
        a Finite elements space from spl. Default: None

    discretization: dict
        a dictionary that contains the used discretization

    mapping: clapp.spl.mapping.Mapping
        a mapping object (geometric transformation)

    is_block: bool
        treat a block prolbem if True. Must be supplied only when using
        discretization. Otherwise, the fem space should be consistent with the
        weak formulation.

    symbolic_eigen: bool
        in the case of a block expression, we can first compute the (symbolic) eigenvalues
        of the symbol then sample it, or doing the sampling then compute the
        numerical eigenvalues.
    """
    # ...
    if not isinstance(expr, Lambda):
        raise TypeError('Expecting a Lambda expression')
    # ...

    # ...
    if not( discretization is None ):
        dim = len(discretization['n_elements'])

    elif not( space is None ):
        dim = space.pdim

        n_elements = space.ncells
        if not( isinstance(n_elements, (list, tuple))): n_elements = [n_elements]

        degrees = space.degree
        if not( isinstance(degrees, (list, tuple))): degrees = [degrees]

        discretization = {'n_elements': n_elements, 'degrees': degrees}

        from spl.fem.vector  import VectorFemSpace
        is_block = isinstance(space, VectorFemSpace)

        if is_block:
            # TODO make sure all degrees are the same?
            #      or remove discretization and use only the space
            discretization['degrees'] = degrees[0]

        # TODO check that the weak form is consistent with the space (both are blocks)

    else:
        raise ValueError('discretization (dict) or fem space must be given')
    # ...

    # ... lambdify the symbol.
    f = glt_lambdify(expr)
    # ...

    # ...
    expr = expr.expr
    # ...

    # ...
    n       = discretization['n_elements']
    degrees = discretization['degrees']

    dim     = len(n)
    # ...

    # ...
    if dim == 1:
        # TODO boundary condition
        nx = n[0] + degrees[0] #- 2

        t1 = np.linspace(-np.pi,np.pi, nx)

        u = np.linspace(0.,1.,nx)
        if mapping is not None:
            x = mapping.evaluate(u)[0,:]
        else:
            x = u

        if is_block:
            if symbolic_eigen:
                eigen = expr.eigenvals()

                eigs = []
                for ek, mult in list(eigen.items()):
                    f = glt_lambdify(ek)
                    t = f(x,t1)
                    eigs += mult * list(t)

                return np.asarray(eigs) + 0.j

            else:
                # sample the lambdified matrix symbol
                F = f(x,t1)

                # TODO must be converted to Fortran (using pyccel?)
                n,m = expr.shape
                W = []
                for i in range(0, nx):
                    for j in range(0,ny):

                        w, v = eig(F[:,i,j])
                        wr = w.real

                        # TODO treat the case of complex eigenvalues

                        W += list(wr)

                W = np.asarray(W)

                return W

        else:
            return f(x,t1)
    elif dim == 2:
        # TODO boundary condition
        nx = n[0] + degrees[0] #- 2
        ny = n[1] + degrees[1] #- 2

        t1 = np.linspace(-np.pi,np.pi, nx)
        t2 = np.linspace(-np.pi,np.pi, ny)

        u = np.linspace(0.,1.,nx)
        v = np.linspace(0.,1.,ny)
        if mapping is not None:
            x = mapping.evaluate(u,v)[0,:,:]
            y = mapping.evaluate(u,v)[1,:,:]
        else:
            x,y   = np.meshgrid(u,v)

        t1,t2 = np.meshgrid(t1,t2)

        if is_block:
            if symbolic_eigen:
                eigen = expr.eigenvals()

                eigs = []
                for ek, mult in list(eigen.items()):
                    f = glt_lambdify(ek)
                    t = f(x,y,t1,t2).ravel()
                    eigs += mult * list(t)

                return np.asarray(eigs) + 0.j

            else:
                # sample the lambdified matrix symbol
                F = f(x,y,t1,t2)

                # TODO must be converted to Fortran (using pyccel?)
                n,m = expr.shape
                W = []
                for i in range(0, nx):
                    for j in range(0,ny):

                        w, v = eig(F[:,:,i,j])
                        wr = w.real

                        # TODO treat the case of complex eigenvalues

                        W += list(wr)

                W = np.asarray(W)

                return W

        else:
            rr = f(x,y,t1,t2)
            return f(x,y,t1,t2).ravel()

    elif dim == 3:
        # TODO boundary condition
        nx = n[0] + degrees[0] #- 2
        ny = n[1] + degrees[1] #- 2
        nz = n[2] + degrees[2] #- 2

        t1 = np.linspace(-np.pi,np.pi, nx)
        t2 = np.linspace(-np.pi,np.pi, ny)
        t3 = np.linspace(-np.pi,np.pi, nz)

        u = np.linspace(0.,1.,nx)
        v = np.linspace(0.,1.,ny)
        w = np.linspace(0.,1.,nz)
        if mapping is not None:
            x = mapping.evaluate(t1,t2,t3)[0,:,:,:]
            y = mapping.evaluate(t1,t2,t3)[1,:,:,:]
            z = mapping.evaluate(t1,t2,t3)[2,:,:,:]
        else:
            # 1 and 0  are inverted to get the right shape
            x,y,z = np.meshgrid(t2,t1,t3)

        # 1 and 0  are inverted to get the right shape
        t1,t2,t3 = np.meshgrid(t2,t1,t3)

        if is_block:
            if symbolic_eigen:
                eigen = expr.eigenvals()

                eigs = []
                for ek, mult in list(eigen.items()):
                    f = glt_lambdify(ek)
                    t = f(x,y,z,t1,t2,t3).ravel()
                    eigs += mult * list(t)

                return np.asarray(eigs) + 0.j

            else:
                # sample the lambdified matrix symbol
                F = f(x,y,z,t1,t2,t3)

                # TODO must be converted to Fortran (using pyccel?)
                n,m = expr.shape
                W = []
                for i in range(0, nx):
                    for j in range(0,ny):
                        for k in range(0,nz):

                            w, v = eig(F[:,:,i,j,k])
                            wr = w.real

                            # TODO treat the case of complex eigenvalues

                            W += list(wr)

                W = np.asarray(W)

                return W

        else:
            return f(x,y,z,t1,t2,t3).ravel()
    # ...
# ...

# ... TODO to be removed, once we have notebooks with complex symbols
def glt_plot_eigenvalues(expr, discretization, \
                         mapping=None, \
                         matrix=None, \
                         tolerance=1.e-8, **settings):
    """
    plots the approximations of the eigenvalues by means of a uniform sampling
    of the glt symbol.

    expr: sympy.Expression
        a sympy expression or a text

    discretization: dict
        a dictionary that contains the used discretization

    mapping: clapp.spl.mapping.Mapping
        a mapping object (geometric transformation)

    matrix: clapp.plaf.matrix.Matrix
        a matrix object after assembling the weak formulation.

    tolerance: float
        a tolerance to check if the values are pure real numbers.

    settings: dict
        dictionary for different settings
    """
    import matplotlib.pyplot as plt

    # ...
    M = None
    if matrix is not None:
        from scipy.linalg import eig

        # ... PLAF matrix or scipy sparse
        from clapp.plaf.matrix import Matrix
        if type(matrix) == Matrix:
            M = matrix.get().todense()
        elif type(matrix) == dict:
            raise ValueError("NOT YET IMPLEMENTED")
        else:
            M = matrix.todense()
        # ...
    # ...

    # ...
    try:
        label = settings["label"]
    except:
        label = "glt symbol"
    # ...

    # ...
    try:
        properties = settings["properties"]
    except:
        properties = "+b"
    # ...

    # ... uniform sampling of the glt symbol
    t  = glt_approximate_eigenvalues(expr, discretization, mapping=mapping)

    tr = t.real.ravel()
    ti = t.imag.ravel()
    # ...

    # ... real case
    if (np.linalg.norm(ti) < tolerance):
        # ...
        tr.sort()

        plt.plot(tr, properties, label=label)
        # ...

        # ...
        if M is not None:
            # ...
            w, v = eig(M)
            wr = w.real
            wr.sort()
            plt.plot(wr, "xr", label="eigenvalues")
            # ...
        # ...
    else:
        # ...
        plt.plot(tr, ti, properties, label=label)
        # ...

        # ...
        if M is not None:
            # ...
            w, v = eig(M)
            wr = w.real
            wi = w.imag
            plt.plot(wr, wi, "xr", label="eigenvalues")
            # ...
        # ...
    # ...
# ...

# ...
class glt_function(Function):
    """

    Examples
    ========

    """

    nargs = None

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

    @classmethod
    def eval(cls, *_args):
        """."""

        if not _args:
            return

        f = _args[0]
        n = _args[1]
        p = _args[2]

        if isinstance(n, (Tuple, list, tuple)):
            dim = len(n)
        else:
            dim = 1
            n = [n]
            p = [p]
        discretization = {"n_elements": n, "degrees": p}

        F = glt_symbol(f, dim=dim,
                       discretization=discretization,
                       evaluate=True,
                       verbose=False)

        return F
# ...

# ...
class glt_symbol_m(Function):
    """
    A class for the mass symbol
    """
    nargs = 3

    @classmethod
    def eval(cls, n, p, t):
        # ...
        if not 0 <= p:
            raise ValueError("must have 0 <= p")
        if not 0 <= n:
            raise ValueError("must have 0 <= n")
        # ...

        # ...
        r  = Symbol('r')

        pp = 2*p + 1
        N = pp + 1
        L = list(range(0, N + pp + 1))

        b0 = bspline_basis(pp, L, 0, r)
        bsp = lambdify(r, b0)
        # ...

        # ... we use nsimplify to get the rational number
        phi = []
        for i in range(0, p+1):
            y = bsp(p+1-i)
            y = nsimplify(y, tolerance=TOLERANCE, rational=True)
            phi.append(y)
        # ...

        # ...
        m = phi[0] * cos(S.Zero)
        for i in range(1, p+1):
            m += 2 * phi[i] * cos(i * t)
        # ...

        # ... scaling
        m *= Rational(1,n)
        # ...

        return m
# ...

# ...
class glt_symbol_s(Function):
    """
    A class for the stiffness symbol
    """
    nargs = 3

    @classmethod
    def eval(cls, n, p, t):
        # ...
        if not 0 <= p:
            raise ValueError("must have 0 <= p")
        if not 0 <= n:
            raise ValueError("must have 0 <= n")
        # ...

        # ...
        r  = Symbol('r')

        pp = 2*p + 1
        N = pp + 1
        L = list(range(0, N + pp + 1))

        b0    = bspline_basis(pp, L, 0, r)
        b0_r  = diff(b0, r)
        b0_rr = diff(b0_r, r)
        bsp   = lambdify(r, b0_rr)
        # ...

        # ... we use nsimplify to get the rational number
        phi = []
        for i in range(0, p+1):
            y = bsp(p+1-i)
            y = nsimplify(y, tolerance=TOLERANCE, rational=True)
            phi.append(y)
        # ...

        # ...
        m = -phi[0] * cos(S.Zero)
        for i in range(1, p+1):
            m += -2 * phi[i] * cos(i * t)
        # ...

        # ... scaling
        m *= n
        # ...

        return m
# ...

# ...
class glt_symbol_a(Function):
    """
    A class for the advection symbol
    """
    nargs = 3

    @classmethod
    def eval(cls, n, p, t):
        # ...
        if not 0 <= p:
            raise ValueError("must have 0 <= p")
        if not 0 <= n:
            raise ValueError("must have 0 <= n")
        # ...

        # ...
        r  = Symbol('r')

        pp = 2*p + 1
        N = pp + 1
        L = list(range(0, N + pp + 1))

        b0   = bspline_basis(pp, L, 0, r)
        b0_r = diff(b0, r)
        bsp  = lambdify(r, b0_r)
        # ...

        # ... we use nsimplify to get the rational number
        phi = []
        for i in range(0, p+1):
            y = bsp(p+1-i)
            y = nsimplify(y, tolerance=TOLERANCE, rational=True)
            phi.append(y)
        # ...

        # ...
        m = -phi[0] * cos(S.Zero)
        for i in range(1, p+1):
            m += -2 * phi[i] * sin(i * t)
        # ...

        # ... make it pure imaginary
        m *= sympy_I
        # ...

        return m
# ...

# ...
def glt_symbol_laplace(discretization, \
                       verbose=False, evaluate=True, \
                       instructions=[], \
                       **settings):
    """
    Returns the Laplace symbol for a given discretization.

    discretization: dict
        a dictionary that contains the used discretization

    verbose: bool
        talk more

    evaluate: bool
        causes the evaluation of the atomic symbols, if true

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings
    """
    raise NotImplementedError('')
# ...

# ...
def glt_integrate(expr, domain="Omega"):
    """
    Adds the integral to the expression. needed for printing.

    domain: str
        domain over which we integrate the expression.
    """
    return Integral(expr, domain)
# ...

# ...
def glt_formatting(expr, **settings):
    """
    Formatting the glt symbol, prior to calling a printer

    expr: sympy.Expression
        a sympy expression

    settings: dict
        dictionary for different settings
    """

    # ...
    try:
        domain = settings["glt_integrate"]
        domain = sympify(str(domain))

        expr = glt_integrate(expr, domain)
    except:
        pass
    # ...

    # ...
    try:
        fmt = settings["glt_formatting_atoms"]
        if fmt:
            expr = glt_formatting_atoms(expr, **settings)
    except:
        pass
    # ...

    return expr
# ...

# ...
def glt_formatting_atoms(expr, **settings):
    """
    Formatting the glt symbol atoms, prior to calling a printer

    expr: sympy.Expression
        a sympy expression

    settings: dict
        dictionary for different settings
    """
    # TODO do we still need it?

    # ...
    dim    = 3
    prefix = "\mathfrak{"
    suffix = "}"
    # ...

    # ...
    for k in range(0, dim):
        # ...
        t = Symbol('t'+str(k+1))

        for s in ["m", "s", "a"]:
            sk = s + str(k+1)
            s_old = Symbol(sk)
            s_new = Symbol(prefix + sk + suffix)

            expr = expr.subs({s_old: s_new})
        # ...
    # ...

    return expr
# ...



# ...
def latex_title_as_paragraph(title):
    """
    Returns the title as a paragraph.

    title: str
        a string for the paragraph title
    """
    return "\paragraph{" + str(title) + "}"
# ...

# ...
def glt_latex_definitions():
    """
    Returns the definitions of the atomic symbols for the GLT.
    """
    # ...
    t = Symbol('t')
    m = Symbol('m')
    s = Symbol('s')
    a = Symbol('a')
    # ...

    # ...
    def formula(symbol):
        """
        returns the latex formula for the mass symbol.
        """
        txt_m = r"\phi_{2p+1}(p+1) + 2 \sum_{k=1}^p \phi_{2p+1}(p+1-k) \cos(k \theta)"
        txt_s = r"- {\phi}''_{2p+1}(p+1) - 2 \sum_{k=1}^p {\phi}''_{2p+1}(p+1-k) \cos(k \theta)"
        txt_a = r"\phi_{2p+1}(p+1) + 2 \sum_{k=1}^p \phi_{2p+1}(p+1-k) \cos(k \theta)"

        if str(symbol) == "m":
            return txt_m
        elif str(symbol) == "s":
            return txt_s
        elif str(symbol) == "a":
            return txt_a
        else:
            print ("not yet available.")
    # ...

    # ...
    definitions = {r"m(\theta)": formula(m), \
                   r"s(\theta)": formula(s), \
                   r"a(\theta)": formula(a)}
    # ...

    return definitions
# ...

# ...
def glt_latex_names():
    """
    returns latex names for basis and atoms
    """
    # ...
    dim = 3

    symbol_names = {}
    # ...

    # ... rename basis
    B = "N"
    for i in ["i","j"]:
        Bi = B + i
        symbol_names[Symbol(Bi)] = B + "_" + i
    # ...

    # ... rename basis derivatives in the logical domain
    args_x = ARGS_x[:dim]
    args_u = ARGS_u[:dim]
    B = "N"
    for i in ["i","j"]:
        Bi = B + i
        for u in args_u + args_x:
            Bi_u = Bi + "_" + u
            partial = "\partial_" + u
            symbol_names[Symbol(Bi_u)] = partial + B + "_" + i
    # ...

    # ... rename the tensor basis derivatives
    B = "N"
    for i in ["i","j"]:
        Bi = B + i
        for k in range(0, dim):
            for s in ["", "s", "ss"]:
                Bk  = Bi + str(k+1)
                _Bk = B + "_{" + i + "_" + str(k+1) + "}"

                if len(s) > 0:
                    prime = len(s) * "\prime"

                    Bk += "_" + s
                    _Bk = B + "^{" + prime + "}" \
                            + "_{" + i + "_" + str(k+1) + "}"

                symbol_names[Symbol(Bk)] = _Bk
    # ...

    # ... TODO add flag to choose which kind of printing:
#    for k in range(0, dim):
#        # ...
#        symbol_names[Symbol('m'+str(k+1))] = "\mathfrak{m}_" + str(k+1)
#        symbol_names[Symbol('s'+str(k+1))] = "\mathfrak{s}_" + str(k+1)
#        symbol_names[Symbol('a'+str(k+1))] = "\mathfrak{a}_" + str(k+1)
#        # ...

    degree = "p"
    for k in range(0, dim):
        # ...
        for s in ["m", "s", "a"]:
            symbol_names[Symbol(s+str(k+1))] = r"\mathfrak{" + s + "}_" \
                                             + degree \
                                             + r"(\theta_" \
                                             + str(k+1) + ")"
        # ...
    # ...

    # ...
    for k in range(0, dim):
        symbol_names[Symbol("t"+str(k+1))] = r"\theta_" + str(k+1)
    # ...

    return symbol_names
# ...

# ...
def get_sympy_printer_settings(settings):
    """
    constructs the dictionary for sympy settings needed for the printer.

    settings: dict
        dictionary for different settings
    """
    sets = {}
    for key, value in list(settings.items()):
        if key not in SETTINGS:
            sets[key] = value
    return sets
# ...

# ...
def glt_latex(expr, **settings):
    """
    returns the latex expression of expr.

    expr: sympy.Expression
        a sympy expression

    settings: dict
        dictionary for different settings
    """
    # ...
    if type(expr) == dict:
        d_expr = {}
        try:
            mode = settings["mode"]
        except:
            mode = "plain"

        sets = settings.copy()
        sets["mode"] = "plain"
        for key, txt in list(expr.items()):
            d_expr[key] = glt_latex(txt, **sets)

        return d_expr
    # ...

    # ...
    try:
        from gelato.expression import glt_formatting
        fmt = settings["glt_formatting"]
        if fmt:
            expr = glt_formatting(expr, **settings)
    except:
        pass
    # ...

    # ...
    try:
        smp = settings["glt_simplify"]
        if smp:
            expr = simplify(expr)
    except:
        pass
    # ...

    # ...
    sets = get_sympy_printer_settings(settings)
    # ...

    return latex(expr, symbol_names=glt_latex_names(), **sets)
# ...

# ...
def print_glt_latex(expr, **settings):
    """
    Prints the latex expression of expr.

    settings: dict
        dictionary for different settings
    """
    print((glt_latex(expr, **settings)))
# ...
