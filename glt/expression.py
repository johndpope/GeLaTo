# -*- coding: utf-8 -*-
"""This module contains different functions to create and treate the GLT symbols."""
#
#
# TODO use to_assign and post processing as expression and not latex => helpful
#      for Fortran and Lua (code gen).

__all__ = ["glt_formatting", "glt_formatting_atoms"]

from sympy.core.sympify import sympify
from sympy import Symbol
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
from sympy.core.singleton import S
from sympy.simplify.simplify import nsimplify
from sympy.utilities.lambdify import implemented_function
from sympy.matrices.dense import MutableDenseMatrix
from itertools import product
import numpy as np
import matplotlib.pyplot as plt
from glt.printing.latex import latex_title_as_paragraph
from glt.printing.latex import glt_latex_definitions
from glt.printing.latex import glt_latex_names
from glt.printing.latex import glt_latex
from glt.printing.latex import print_glt_latex

# TODO find a better solution.
#      this code is duplicated in printing.latex
ARGS_x       = ["x", "y", "z"]
ARGS_u       = ["u", "v", "w"]
ARGS_s       = ["s", "ss"]
BASIS_TEST   = "Ni"
BASIS_TRIAL  = "Nj"
BASIS_PREFIX = ["x", "y", "z", "xx", "yy", "zz", "xy", "yz", "xz"]
TOLERANCE    = 1.e-10
SETTINGS     = ["glt_integrate", "glt_formatting", "glt_formatting_atoms"]



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
        for key, value in settings.items():
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
        for key, value in settings.items():
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
        for key, value in settings.items():
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

    return expr
# ...

# ...
def glt_update_user_functions(expr, user_functions):
    """
    updates the glt symbol with user defined functions

    expr:
        a sympy expression

    user_functions: dict
        a dictionary containing the user defined functions
    """
    from clapp.vale.expressions.function import Function as CLAPP_Function
    for f_name, f in user_functions.items():
        # ...
        if type(f) == CLAPP_Function:
            sympy_f = f.to_sympy()
        else:
            sympy_f = implemented_function(Function(f_name), f)
        # ...

        # ...
        expr = expr.subs({Symbol(f_name): sympy_f})
        # ...

    return expr
# ...

# ...
def glt_update_user_constants(expr, user_constants):
    """
    updates the glt symbol with user defined constants

    expr:
        a sympy expression

    user_constants: dict
        a dictionary containing the user defined constants
    """
    for f_name, f in user_constants.items():
        # ...
        if type(f) in [int, float, complex]:
            expr = expr.subs({Symbol(f_name): f})
        # ...

    return expr
# ...

# ...
def glt_symbol(expr, dim, n_deriv=1, \
               verbose=False, evaluate=True, \
               discretization=None, \
               user_functions=None, \
               user_constants=None, \
               instructions=[], \
               **settings):
    """
    computes the glt symbol of a weak formulation given as a sympy expression.

    expr: sympy.Expression
        a sympy expression or a text

    dim: int
        dimension of the logical/physical domain.

    n_deriv: int
        maximum derivatives that appear in the weak formulation.

    verbose: bool
        talk more

    evaluate: bool
        causes the evaluation of the atomic symbols, if true

    discretization: dict
        a dictionary that contains the used discretization

    user_functions: dict
        a dictionary containing the user defined functions

    user_constants: dict
        a dictionary containing the user defined constants

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings

    """
    # ...
    if verbose:
        print "*** Input expression : ", expr
    # ...

    # ...
    if type(expr) == dict:
        d_expr = {}
        for key, txt in expr.items():
            # ... when using vale, we may get also a coefficient.
            if type(txt) == list:
                txt = str(txt[0]) + " * (" + txt[1] + ")"
            # ...

            # ...
            title  = "Computing the GLT symbol for the block " + str(key)
            instructions.append(latex_title_as_paragraph(title))
            # ...

            # ...
            d_expr[key] = glt_symbol(txt, dim, \
                                     n_deriv=n_deriv, \
                                     verbose=verbose, \
                                     evaluate=evaluate, \
                                     discretization=discretization, \
                                     user_functions=user_functions, \
                                     user_constants=user_constants, \
                                     instructions=instructions, \
                                     **settings)
            # ...

        return dict_to_matrix(d_expr, instructions=instructions, **settings)
    else:
        # ...
        ns = {}
        # ...

        # ...
        if user_constants is not None:
            for c_name, c in user_constants.items():
                ns[c_name] = Symbol(c_name)
        # ...

        # ...
        d = basis_symbols(dim,n_deriv)
        for key, item in d.items():
            ns[key] = item
        # ...

        # ...
        expr = sympify(str(expr), locals=ns)
        # ...

        # ... remove _0 for a nice printing
        expr = expr.subs({Symbol("Ni_0"): Symbol("Ni")})
        expr = expr.subs({Symbol("Nj_0"): Symbol("Nj")})
        # ...
    # ...

    # ...
    if verbose:
        # ...
        instruction = "We consider the following weak formulation:"
        instructions.append(instruction)
        instructions.append(glt_latex(expr, **settings))
        # ...

        print ">>> weak formulation: ", expr
    # ...

    # ...
    expr = apply_mapping(expr, dim=dim, \
                         instructions=instructions, \
                         **settings)
    if verbose:
        print expr
    # ...

    # ...
    expr = apply_tensor(expr, dim=dim, \
                         instructions=instructions, \
                         **settings)
    if verbose:
        print expr
    # ...

    # ...
    expr = apply_factor(expr, dim, \
                         instructions=instructions, \
                         **settings)
    if verbose:
        print expr
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

    # ...
    if (not user_functions) and (not user_constants):
        return expr
    # ...

    # ...
    if user_constants:
        expr = glt_update_user_constants(expr, user_constants)
    # ...

    # ...
    if user_functions:
        expr = glt_update_user_functions(expr, user_functions)
    # ...

    return expr
# ...

# ...
def glt_symbol_from_weak_formulation(form, discretization, \
                                     user_constants=None, \
                                     verbose=False, evaluate=True, \
                                     instructions=[], \
                                     **settings):
    """
    creates a glt symbol from a weak formulation.

    form: clapp.vale.ast.BilinearForm
        a weak formulation.

    discretization: dict
        a dictionary that contains the used discretization

    user_constants: dict
        a dictionary containing the user defined constants

    verbose: bool
        talk more

    evaluate: bool
        causes the evaluation of the atomic symbols, if true

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings
    """
    # ... TODO sets n_deriv from bilinear form
    n_deriv = 2
    # ...

    # ... gets the dimension
    dim = form.assembler.trial_space.context.p_dim
    # ...

    # ... TODO user constants from form
    # we consider form to be sympy expression for the moment
    expr = glt_symbol(form.glt_expr, dim, n_deriv=n_deriv, \
                      verbose=verbose, evaluate=evaluate, \
                      discretization=discretization, \
                      user_functions=form.functions, \
                      user_constants=user_constants, \
                      instructions=instructions, \
                      **settings)
    # ...

    return expr
# ...

# ...
def glt_lambdify(expr, dim=None, discretization=None):
    """
    it is supposed that glt_symbol has been called before.

    expr: sympy.Expression
        a sympy expression or a text

    dim: int
        dimension of the logical/physical domain.

    discretization: dict
        a dictionary that contains the used discretization
    """
    _dim = dim
    if dim is None:
        if discretization is not None:
            _dim = len(discretization["n_elements"])
        else:
            print("> either dim or discretization must be provided.")
            raise()

    args_x = ["x","y","z"]
    args_t = ["t1","t2","t3"]
    args_xt = args_x[:_dim] + args_t[:_dim]
    args = [Symbol(x) for x in args_xt]
    return lambdify(args, expr, "numpy")
# ...

# ...
def glt_approximate_eigenvalues(expr, discretization, mapping=None):
    """
    approximates the eigenvalues using a uniform sampling

    expr: sympy.Expression
        a sympy expression or a text

    discretization: dict
        a dictionary that contains the used discretization

    mapping: clapp.spl.mapping.Mapping
        a mapping object (geometric transformation)
    """
    # ...
    is_block = False
    # ...

    # ... lambdify the symbol.
    #     The block case will be done later.
    if type(expr) == MutableDenseMatrix:
        is_block = True
    else:
        f = glt_lambdify(expr, discretization=discretization)
    # ...

    # ...
    n       = discretization['n_elements']
    degrees = discretization['degrees']

    dim     = len(n)
    # ...

    # ...
    if dim == 1:
        # TODO boundary condition
        nx = n[0] + degrees[0] - 2

        t1 = np.linspace(-np.pi,np.pi, nx)

        u = np.linspace(0.,1.,nx)
        if mapping is not None:
            x = mapping.evaluate(u)[0,:]
        else:
            x = u

        if is_block:
            eigen = expr.eigenvals()

            eigs = []
            for ek, mult in eigen.items():
                f = glt_lambdify(ek, discretization=discretization)
                t = f(x,t1)
                eigs += mult * list(t)

            return np.asarray(eigs) + 0.j
        else:
            return f(x,t1)
    elif dim == 2:
        # TODO boundary condition
        nx = n[0] + degrees[0] - 2
        ny = n[1] + degrees[1] - 2

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
            eigen = expr.eigenvals()

            eigs = []
            for ek, mult in eigen.items():
                f = glt_lambdify(ek, discretization=discretization)
                t = f(x,y,t1,t2).ravel()
                eigs += mult * list(t)

            return np.asarray(eigs) + 0.j
        else:
            rr = f(x,y,t1,t2)
            return f(x,y,t1,t2).ravel()
    elif dim == 3:
        # TODO boundary condition
        nx = n[0] + degrees[0] - 2
        ny = n[1] + degrees[1] - 2
        nz = n[2] + degrees[2] - 2

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
            eigen = expr.eigenvals()

            eigs = []
            for ek, mult in eigen.items():
                f = glt_lambdify(ek, discretization=discretization)
                t = f(x,y,z,t1,t2,t3).ravel()
                eigs += mult * list(t)

            return np.asarray(eigs) + 0.j
        else:
            return f(x,y,z,t1,t2,t3).ravel()
    # ...
# ...

# ...
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
    # ...
    M = None
    if matrix is not None:
        from scipy.linalg import eig

        # ... PLAF matrix or scipy sparse
        from clapp.plaf.matrix import Matrix
        if type(matrix) == Matrix:
            M = matrix.get().todense()
        elif type(matrix) == dict:
            print ("NOT YET IMPLEMENTED")
            raise()
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
        L = range(0, N + pp + 1)

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
        L = range(0, N + pp + 1)

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
        L = range(0, N + pp + 1)

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
def dict_to_matrix(d, instructions=None, **settings):
    """
    converts a dictionary of expressions to a matrix

    d: dict
        dictionary of expressions

    instructions: list
        a list to keep track of the applied instructions.

    settings: dict
        dictionary for different settings
    """
    # ...
    assert(type(d) == dict)
    # ...

    # ...
    n_rows = 1
    n_cols = 1
    for key, values in d.items():
        if key[0]+1 > n_rows:
            n_rows = key[0] + 1
        if key[1]+1 > n_cols:
            n_cols = key[1] + 1
    # ...

    # ...
    expressions = []
    for i_row in range(0, n_rows):
        row_expr = []
        for i_col in range(0, n_cols):
            _expr = None
            try:
                _expr = d[i_row,i_col]
            except:
                _expr = S.Zero
            row_expr.append(_expr)
        expressions.append(row_expr)
    # ...

    # ...
    expr = Matrix(expressions)
    # ...

    # ... updates the latex expression
    if instructions is not None:
        # ...
        title  = "GLT symbol"
        instructions.append(latex_title_as_paragraph(title))
        # ...

        # ...
        sets = {}
        for key, value in settings.items():
            if not(key == "glt_integrate"):
                sets[key] = value

        instructions.append(glt_latex(expr, **sets))
        # ...
    # ...

    return expr
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
    # ...
    dim = len(discretization["n_elements"])
    # ...

    # ...
    if dim == 1:
        txt = "Ni_x * Nj_x"
    elif dim == 2:
        txt = "Ni_x * Nj_x + Ni_y * Nj_y"
    elif dim == 3:
        txt = "Ni_x * Nj_x + Ni_y * Nj_y + Ni_z * Nj_z"
    # ...

    # ...
    expr = glt_symbol(txt, dim, \
                      verbose=verbose, evaluate=evaluate, \
                      discretization=discretization, \
                      instructions=instructions, \
                      **settings)
    # ...

    return expr
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
