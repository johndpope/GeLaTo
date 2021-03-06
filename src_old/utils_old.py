# coding: utf-8

# TODO: - allow for giving a name for the trial/test basis
#       - Ni/Nj should be Ni_0/Nj_O
#       - define templates as proper python functions
#       - use redbaron to modify the template

from gelato.expression import construct_weak_form
from gelato.expression import is_test_function, is_trial_function
from gelato.expression import BASIS_PREFIX
from gelato.glt import glt_symbol
from gelato.calculus   import (Dot, Cross, Grad, Curl, Rot, Div)
from gelato.calculus   import Constant
from gelato.calculus   import Field
from gelato.fem.templates import template_1d_scalar, template_header_1d_scalar
from gelato.fem.templates import template_2d_scalar, template_header_2d_scalar
from gelato.fem.templates import template_3d_scalar, template_header_3d_scalar

from gelato.fem.templates import template_1d_block, template_header_1d_block
from gelato.fem.templates import template_2d_block, template_header_2d_block
from gelato.fem.templates import template_3d_block, template_header_3d_block

from gelato.fem.templates import symbol_1d_scalar, symbol_header_1d_scalar
from gelato.fem.templates import symbol_2d_scalar, symbol_header_2d_scalar
from gelato.fem.templates import symbol_3d_scalar, symbol_header_3d_scalar

from gelato.fem.templates import symbol_1d_block, symbol_header_1d_block
from gelato.fem.templates import symbol_2d_block, symbol_header_2d_block
from gelato.fem.templates import symbol_3d_block, symbol_header_3d_block

from gelato.fem.templates import eval_field_1d_scalar
from gelato.fem.templates import eval_field_2d_scalar
from gelato.fem.templates import eval_field_3d_scalar


from numbers import Number
from collections import OrderedDict
from sympy import Integer, Float
import os

def _convert_int_to_float(expr):
    sub = zip( expr.atoms(Integer), map(Float, expr.atoms(Integer)) )
    expr = expr.subs(sub)
    return expr

def _count_letter(word, char):
    count = 0
    for c in word:
        if c == char:
            count += 1
    return count

def construct_test_functions(nderiv, dim):
    """constructs test functions and their derivatives for every direction k.
    on return, we get a list of statements, that we need to indent later
    """
    d_basis = OrderedDict()
    for k in range(1, dim+1):
        d_basis[k,0] = 'bs{k}[il_{k}, 0, g{k}]'.format(k=k)
        for d in range(1, nderiv+1):
            d_basis[k,d] = 'bs{k}[il_{k}, {d}, g{k}]'.format(d=d, k=k)

    return d_basis

def construct_trial_functions(nderiv, dim):
    """constructs trial functions and their derivatives for every direction k.
    on return, we get a list of statements, that we need to indent later
    """
    d_basis = OrderedDict()
    for k in range(1, dim+1):
        d_basis[k,0] = 'bs{k}[jl_{k}, 0, g{k}]'.format(k=k)
        for d in range(1, nderiv+1):
            d_basis[k,d] = 'bs{k}[jl_{k}, {d}, g{k}]'.format(d=d, k=k)

    return d_basis


def mkdir_p(dir):
    if os.path.isdir(dir):
        return
    os.makedirs(dir)

def write_code(name, code, ext='py', folder='.pyccel'):
    filename = '{name}.{ext}'.format(name=name, ext=ext)
    if folder:
        mkdir_p(folder)
        filename = os.path.join(folder, filename)

    f = open(filename, 'w')
    for line in code:
        f.write(line)
    f.close()

def compile_kernel(name, expr, V,
                   namespace=globals(),
                   verbose=False,
                   d_constants={},
                   d_args={},
                   context=None,
                   backend='python',
                   export_pyfile=True):
    """returns a kernel from a Lambda expression on a Finite Elements space."""

    from spl.fem.vector  import VectorFemSpace
    from spl.fem.splines import SplineSpace
    from spl.fem.tensor  import TensorFemSpace

    # ... parametric dimension
    dim = V.pdim
    # ...

    # ... number of partial derivatives
    #     TODO must be computed from the weak form then we re-initialize the
    #     space
    if isinstance(V, SplineSpace):
        nderiv = V.nderiv
    elif isinstance(V, TensorFemSpace):
        nderiv = max(W.nderiv for W in V.spaces)
    elif isinstance(V, VectorFemSpace):
        nds = []
        for W in V.spaces:
            if isinstance(W, SplineSpace):
                nderiv = W.nderiv
            elif isinstance(W, TensorFemSpace):
                nderiv = max(X.nderiv for X in W.spaces)
            nds.append(nderiv)
        nderiv = max(nds)
    # ...

    # ...
    if verbose:
        print('> input     := {0}'.format(expr))
    # ...

    # ...
    fields = [i for i in expr.free_symbols if isinstance(i, Field)]
    if verbose:
        print('> Fields = ', fields)
    # ...

    # ...
    expr = construct_weak_form(expr, dim=dim,
                               is_block=isinstance(V, VectorFemSpace))
    if verbose:
        print('> weak form := {0}'.format(expr))
    # ...

    # ... contants
    #     for each argument, we compute its datatype (needed for Pyccel)
    #     case of Numeric Native Python types
    #     this means that a has a given value (1, 1.0 etc)
    if d_constants:
        for k, a in list(d_constants.items()):
            if not isinstance(a, Number):
                raise TypeError('Expecting a Python Numeric object')

        # update the weak formulation using the given arguments
        _d = {}
        for k,v in list(d_constants.items()):
            if isinstance(k, str):
                _d[Constant(k)] = v
            else:
                _d[k] = v

        expr = expr.subs(_d)

    args = ''
    dtypes = ''
    if d_args:
        # ... additional arguments
        #     for each argument, we compute its datatype (needed for Pyccel)
        for k, a in list(d_args.items()):
            # otherwise it can be a string, that specifies its type
            if not isinstance(a, str):
                raise TypeError('Expecting a string')

            if not a in ['int', 'double', 'complex']:
                raise TypeError('Wrong type for {} :: {}'.format(k, a))

        # we convert the dictionaries to OrderedDict, to avoid wrong ordering
        d_args = OrderedDict(sorted(list(d_args.items())))

        names = []
        dtypes = []
        for n,d in list(d_args.items()):
            names.append(n)
            dtypes.append(d)

        args = ', '.join('{}'.format(a) for a in names)
        dtypes = ', '.join('{}'.format(a) for a in dtypes)

        args = ', {}'.format(args)
        dtypes = ', {}'.format(dtypes)

        # TODO check what are the free_symbols of expr,
        #      to make sure the final code will compile
        #      the remaining free symbols must be the trial/test basis functions,
        #      and the coordinates
    # ...

    # ...
    if isinstance(V, VectorFemSpace) and not( V.is_block ):
        raise NotImplementedError('We only treat the case of a block space, for '
                                  'which all components have are identical.')
    # ...

    # ...
    pattern = 'scalar'
    if isinstance(V, VectorFemSpace):
        if V.is_block:
            pattern = 'block'

        else:
            raise NotImplementedError('We only treat the case of a block space, for '
                                      'which all components have are identical.')

    # ...

    # ...
    template_str = 'template_{dim}d_{pattern}'.format(dim=dim, pattern=pattern)
    try:
        template = eval(template_str)
    except:
        raise ValueError('Could not find the corresponding template {}'.format(template_str))
    # ...

    # ... identation (def function body)
    tab = ' '*4
    # ...

    # ... field coeffs
    if fields:
        field_coeffs = OrderedDict()
        for f in fields:
            coeffs = 'coeff_{}'.format(f.name)
            field_coeffs[str(f.name)] = coeffs

        ls = [v for v in list(field_coeffs.values())]
        field_coeffs_str = ', '.join(i for i in ls)

        # add ',' for kernel signature
        field_coeffs_str = ', {}'.format(field_coeffs_str)

        eval_field_str = print_eval_field(expr, V.pdim, fields, verbose=verbose)

        # ...
        if dim == 1:
            e_pattern = '{field}{deriv} = {field}{deriv}_values[g1]'
        elif dim == 2:
            e_pattern = '{field}{deriv} = {field}{deriv}_values[g1,g2]'
        elif dim ==3:
            e_pattern = '{field}{deriv} = {field}{deriv}_values[g1,g2,g3]'
        else:
            raise NotImplementedError('only 1d, 2d and 3d are available')

        field_values = OrderedDict()
        free_names = [str(f.name) for f in expr.free_symbols]
        for f in fields:
            ls = []
            if f.name in free_names:
                ls.append(f.name)
            for deriv in BASIS_PREFIX:
                f_d = '{field}_{deriv}'.format(field=f.name, deriv=deriv)
                if f_d in free_names:
                    ls.append(f_d)

            field_values[f.name] = ls

        tab_base = tab
        # ... update identation to be inside the loop
        for i in range(0, 3*dim):
            tab += ' '*4

        lines = []
        for k, fs in list(field_values.items()):
            coeff = field_coeffs[k]
            for f in fs:
                ls = f.split('_')
                if len(ls) == 1:
                    deriv = ''
                else:
                    deriv = '_{}'.format(ls[-1])
                line = e_pattern.format(field=k, deriv=deriv)
                line = tab + line

                lines.append(line)

        field_value_str = '\n'.join(line for line in lines)
        tab = tab_base
        # ...

        # ...
        field_types = []
        slices = ','.join(':' for i in range(0, dim))
        for v in list(field_coeffs.values()):
            field_types.append('double [{slices}]'.format(slices=slices))

        field_types_str = ', '.join(i for i in field_types)
        field_types_str = ', {}'.format(field_types_str)
        # ...

    else:
        field_coeffs_str = ''
        eval_field_str   = ''
        field_value_str  = ''
        field_types_str  = ''

    # ...

    # ... compute indentation
    tab_base = tab
    for i in range(0, 3*dim):
        tab += ' '*4
    # ...

    # ... print test functions
    d_test_basis = construct_test_functions(nderiv, dim)
    test_names = [i.name for i in expr.free_symbols if is_test_function(i)]
    test_names.sort()

    lines = []
    for a in test_names:
        if a == 'Ni':
            basis = ' * '.join(d_test_basis[k,0] for k in range(1, dim+1))
            line = 'Ni = {basis}'.format(basis=basis)
        else:
            deriv = a.split('_')[-1]
            nx = _count_letter(deriv, 'x')
            ny = _count_letter(deriv, 'y')
            nz = _count_letter(deriv, 'z')
            basis = ' * '.join(d_test_basis[k,d] for k,d in zip(range(1, dim+1), [nx,ny,nz]))
            line = 'Ni_{deriv} = {basis}'.format(deriv=deriv, basis=basis)
        lines.append(tab+line)
    test_function_str = '\n'.join(l for l in lines)
    # ...

    # ... print trial functions
    d_trial_basis = construct_trial_functions(nderiv, dim)
    trial_names = [i.name for i in expr.free_symbols if is_trial_function(i)]
    trial_names.sort()

    lines = []
    for a in trial_names:
        if a == 'Nj':
            basis = ' * '.join(d_trial_basis[k,0] for k in range(1, dim+1))
            line = 'Nj = {basis}'.format(basis=basis)
        else:
            deriv = a.split('_')[-1]
            nx = _count_letter(deriv, 'x')
            ny = _count_letter(deriv, 'y')
            nz = _count_letter(deriv, 'z')
            basis = ' * '.join(d_trial_basis[k,d] for k,d in zip(range(1, dim+1), [nx,ny,nz]))
            line = 'Nj_{deriv} = {basis}'.format(deriv=deriv, basis=basis)
        lines.append(tab+line)
    trial_function_str = '\n'.join(l for l in lines)
    # ...

    # ...
    tab = tab_base
    # ...

    # ...
    if isinstance(V, VectorFemSpace):
        if V.is_block:
            n_components = len(V.spaces)

            # ... - initializing element matrices
            #     - define arguments
            lines = []
            mat_args = []
            slices = ','.join(':' for i in range(0, 2*dim))
            for i in range(0, n_components):
                for j in range(0, n_components):
                    mat = 'mat_{i}{j}'.format(i=i,j=j)
                    mat_args.append(mat)

                    line = '{mat}[{slices}] = 0.0'.format(mat=mat,slices=slices)
                    line = tab + line

                    lines.append(line)

            mat_args_str = ', '.join(mat for mat in mat_args)
            mat_init_str = '\n'.join(line for line in lines)
            # ...

            # ... update identation to be inside the loop
            for i in range(0, 2*dim):
                tab += ' '*4

            tab_base = tab
            # ...

            # ... initializing accumulation variables
            lines = []
            for i in range(0, n_components):
                for j in range(0, n_components):
                    line = 'v_{i}{j} = 0.0'.format(i=i,j=j)
                    line = tab + line

                    lines.append(line)

            accum_init_str = '\n'.join(line for line in lines)
            # ...

            # .. update indentation
            for i in range(0, dim):
                tab += ' '*4
            # ...

            # ... accumulation contributions
            lines = []
            for i in range(0, n_components):
                for j in range(0, n_components):
                    line = 'v_{i}{j} += ({__WEAK_FORM__}) * wvol'
                    e = _convert_int_to_float(expr[i,j].evalf())
                    # we call evalf to avoid having fortran doing the evaluation of rational
                    # division
                    line = line.format(i=i, j=j, __WEAK_FORM__=e)
                    line = tab + line

                    lines.append(line)

            accum_str = '\n'.join(line for line in lines)
            # ...

            # ... assign accumulated values to element matrix
            if dim == 1:
                e_pattern = 'mat_{i}{j}[il_1, p1 + jl_1 - il_1] = v_{i}{j}'
            elif dim == 2:
                e_pattern = 'mat_{i}{j}[il_1, il_2, p1 + jl_1 - il_1, p2 + jl_2 - il_2] = v_{i}{j}'
            elif dim ==3:
                e_pattern = 'mat_{i}{j}[il_1, il_2, il_3, p1 + jl_1 - il_1, p2 + jl_2 - il_2, p3 + jl_3 - il_3] = v_{i}{j}'
            else:
                raise NotImplementedError('only 1d, 2d and 3d are available')

            tab = tab_base
            lines = []
            for i in range(0, n_components):
                for j in range(0, n_components):
                    line = e_pattern.format(i=i,j=j)
                    line = tab + line

                    lines.append(line)

            accum_assign_str = '\n'.join(line for line in lines)
            # ...

            code = template.format(__KERNEL_NAME__=name,
                                   __MAT_ARGS__=mat_args_str,
                                   __FIELD_COEFFS__=field_coeffs_str,
                                   __FIELD_EVALUATION__=eval_field_str,
                                   __MAT_INIT__=mat_init_str,
                                   __ACCUM_INIT__=accum_init_str,
                                   __FIELD_VALUE__=field_value_str,
                                   __TEST_FUNCTION__=test_function_str,
                                   __TRIAL_FUNCTION__=trial_function_str,
                                   __ACCUM__=accum_str,
                                   __ACCUM_ASSIGN__=accum_assign_str,
                                   __ARGS__=args)

        else:
            raise NotImplementedError('We only treat the case of a block space, for '
                                      'which all components have are identical.')

    else:
        e = _convert_int_to_float(expr.evalf())
        # we call evalf to avoid having fortran doing the evaluation of rational
        # division
        code = template.format(__KERNEL_NAME__=name,
                               __FIELD_COEFFS__=field_coeffs_str,
                               __FIELD_EVALUATION__=eval_field_str,
                               __FIELD_VALUE__=field_value_str,
                               __TEST_FUNCTION__=test_function_str,
                               __TRIAL_FUNCTION__=trial_function_str,
                               __WEAK_FORM__=e,
                               __ARGS__=args)

    # ...

#    print('--------------')
#    print(code)
#    print('--------------')

    # ...
    if context:
        from pyccel.epyccel import ContextPyccel

        if isinstance(context, ContextPyccel):
            context = [context]
        elif isinstance(context, (list, tuple)):
            for i in context:
                assert(isinstance(i, ContextPyccel))
        else:
            raise TypeError('Expecting a ContextPyccel or list/tuple of ContextPyccel')

        # append functions to the namespace
        for c in context:
            for k,v in list(c.functions.items()):
                namespace[k] = v[0]
    # ...

    # ...
    exec(code, namespace)
    kernel = namespace[name]
    # ...

    # ... export the python code of the module
    if export_pyfile:
        write_code(name, code, ext='py', folder='.pyccel')
    # ...

    # ...
    if backend == 'fortran':
#        try:
        # import epyccel function
        from pyccel.epyccel import epyccel

        #  ... define a header to specify the arguments types for kernel
        try:
            template = eval('template_header_{dim}d_{pattern}'.format(dim=dim,
                                                                      pattern=pattern))
        except:
            raise ValueError('Could not find the corresponding template')
        # ...

        # ...
        if isinstance(V, VectorFemSpace):
            if V.is_block:
                # ... declare element matrices dtypes
                mat_types = []
                for i in range(0, n_components):
                    for j in range(0, n_components):
                        if dim == 1:
                            mat_types.append('double [:,:]')
                        elif dim == 2:
                            mat_types.append('double [:,:,:,:]')
                        elif dim ==3:
                            mat_types.append('double [:,:,:,:,:,:]')
                        else:
                            raise NotImplementedError('only 1d, 2d and 3d are available')

                mat_types_str = ', '.join(mat for mat in mat_types)
                # ...

                header = template.format(__KERNEL_NAME__=name,
                                         __MAT_TYPES__=mat_types_str,
                                         __FIELD_TYPES__=field_types_str,
                                         __TYPES__=dtypes)

            else:
                raise NotImplementedError('We only treat the case of a block space, for '
                                          'which all components have are identical.')

        else:
            header = template.format(__KERNEL_NAME__=name,
                                     __FIELD_TYPES__=field_types_str,
                                     __TYPES__=dtypes)
        # ...

        # compile the kernel
        kernel = epyccel(code, header, name=name, context=context)
#        except:
#            print('> COULD NOT CONVERT KERNEL TO FORTRAN')
#            print('  THE PYTHON BACKEND WILL BE USED')
    # ...

    return kernel



def compile_symbol(name, expr, V,
                   namespace=globals(),
                   verbose=False,
                   d_constants={},
                   d_args={},
                   context=None,
                   backend='python',
                   export_pyfile=True):
    """returns a lmabdified function for the GLT symbol."""

    from spl.fem.vector  import VectorFemSpace

    # ... parametric dimension
    dim = V.pdim
    # ...

    # ...
    if verbose:
        print('> input     := {0}'.format(expr))
    # ...

    # ...
    fields = [i for i in expr.free_symbols if isinstance(i, Field)]
    if verbose:
        print('> Fields = ', fields)
    # ...

    # ...
    expr = glt_symbol(expr, space=V, evaluate=True)
    if verbose:
        print('> weak form := {0}'.format(expr))
    # ...

    # ... contants
    #     for each argument, we compute its datatype (needed for Pyccel)
    #     case of Numeric Native Python types
    #     this means that a has a given value (1, 1.0 etc)
    if d_constants:
        for k, a in list(d_constants.items()):
            if not isinstance(a, Number):
                raise TypeError('Expecting a Python Numeric object')

        # update the glt symbol using the given arguments
        _d = {}
        for k,v in list(d_constants.items()):
            if isinstance(k, str):
                _d[Constant(k)] = v
            else:
                _d[k] = v

        expr = expr.subs(_d)

#    print(expr)
#    import sys; sys.exit(0)

    args = ''
    dtypes = ''
    if d_args:
        # ... additional arguments
        #     for each argument, we compute its datatype (needed for Pyccel)
        for k, a in list(d_args.items()):
            # otherwise it can be a string, that specifies its type
            if not isinstance(a, str):
                raise TypeError('Expecting a string')

            if not a in ['int', 'double', 'complex']:
                raise TypeError('Wrong type for {} :: {}'.format(k, a))

        # we convert the dictionaries to OrderedDict, to avoid wrong ordering
        d_args = OrderedDict(sorted(list(d_args.items())))

        names = []
        dtypes = []
        for n,d in list(d_args.items()):
            names.append(n)
            dtypes.append(d)

        args = ', '.join('{}'.format(a) for a in names)
        dtypes = ', '.join('{}'.format(a) for a in dtypes)

        args = ', {}'.format(args)
        dtypes = ', {}'.format(dtypes)

        # TODO check what are the free_symbols of expr,
        #      to make sure the final code will compile
        #      the remaining free symbols must be the trial/test basis functions,
        #      and the coordinates
    # ...

    # ...
    if isinstance(V, VectorFemSpace) and not( V.is_block ):
        raise NotImplementedError('We only treat the case of a block space, for '
                                  'which all components have are identical.')
    # ...

    # ...
    pattern = 'scalar'
    if isinstance(V, VectorFemSpace):
        if V.is_block:
            pattern = 'block'

        else:
            raise NotImplementedError('We only treat the case of a block space, for '
                                      'which all components have are identical.')

    # ...

    # ...
    template_str = 'symbol_{dim}d_{pattern}'.format(dim=dim, pattern=pattern)
    try:
        template = eval(template_str)
    except:
        raise ValueError('Could not find the corresponding template {}'.format(template_str))
    # ...

    # ...
    if fields:
        raise NotImplementedError('TODO')
    else:
        field_coeffs_str = ''
        eval_field_str   = ''
        field_value_str  = ''
        field_types_str  = ''
    # ...

    # ...
    if isinstance(V, VectorFemSpace):
        if V.is_block:
            n_components = len(V.spaces)

            # ... identation (def function body)
            tab = ' '*4
            # ...

            # ... update identation to be inside the loop
            for i in range(0, dim):
                tab += ' '*4

            tab_base = tab
            # ...

            # ...
            lines = []
            indices = ','.join('i{}'.format(i) for i in range(1, dim+1))
            for i in range(0, n_components):
                for j in range(0, n_components):
                    s_ij = 'symbol[{i},{j},{indices}]'.format(i=i, j=j, indices=indices)
                    e_ij = _convert_int_to_float(expr.expr[i,j])
                    # we call evalf to avoid having fortran doing the evaluation of rational
                    # division
                    line = '{s_ij} = {e_ij}'.format(s_ij=s_ij, e_ij=e_ij.evalf())
                    line = tab + line

                    lines.append(line)

            symbol_expr = '\n'.join(line for line in lines)
            # ...

            code = template.format(__SYMBOL_NAME__=name,
                                   __SYMBOL_EXPR__=symbol_expr,
                                   __FIELD_COEFFS__=field_coeffs_str,
                                   __FIELD_EVALUATION__=eval_field_str,
                                   __FIELD_VALUE__=field_value_str,
                                   __ARGS__=args)

        else:
            raise NotImplementedError('TODO')

    else:
        # we call evalf to avoid having fortran doing the evaluation of rational
        # division
        e = _convert_int_to_float(expr.expr)
        code = template.format(__SYMBOL_NAME__=name,
                               __SYMBOL_EXPR__=e.evalf(),
                               __FIELD_COEFFS__=field_coeffs_str,
                               __FIELD_EVALUATION__=eval_field_str,
                               __FIELD_VALUE__=field_value_str,
                               __ARGS__=args)
    # ...

    # ... export the python code of the module
    if export_pyfile:
        write_code(name, code, ext='py', folder='.pyccel')
    # ...

    # ...
    if context:
        from pyccel.epyccel import ContextPyccel

        if isinstance(context, ContextPyccel):
            context = [context]
        elif isinstance(context, (list, tuple)):
            for i in context:
                assert(isinstance(i, ContextPyccel))
        else:
            raise TypeError('Expecting a ContextPyccel or list/tuple of ContextPyccel')

        # append functions to the namespace
        for c in context:
            for k,v in list(c.functions.items()):
                namespace[k] = v[0]
    # ...
#    print(code)
#    import sys; sys.exit(0)

    # ...
    exec(code, namespace)
    kernel = namespace[name]
    # ...

    # ...
    if backend == 'fortran':
#        try:
        # import epyccel function
        from pyccel.epyccel import epyccel

        #  ... define a header to specify the arguments types for kernel
        template_str = 'symbol_header_{dim}d_{pattern}'.format(dim=dim, pattern=pattern)
        try:
            template = eval(template_str)
        except:
            raise ValueError('Could not find the corresponding template {}'.format(template_str))
        # ...

        # ...
        header = template.format(__SYMBOL_NAME__=name,
                                 __FIELD_TYPES__=field_types_str,
                                 __TYPES__=dtypes)
        # ...

        # compile the kernel
        kernel = epyccel(code, header, name=name, context=context)
#        except:
#            print('> COULD NOT CONVERT KERNEL TO FORTRAN')
#            print('  THE PYTHON BACKEND WILL BE USED')
    # ...

    return kernel




def print_eval_field(expr, dim, fields, verbose=False):
    """."""

    from spl.fem.vector  import VectorFemSpace

    # ...
    if verbose:
        print('> input     := {0}'.format(expr))
    # ...

    # TODO compute nderiv needed to evaluate fields
    nderiv = 1

    # ... field coeffs
    field_coeffs = OrderedDict()
    for f in fields:
        coeffs = 'coeff_{}'.format(f.name)
        field_coeffs[str(f.name)] = coeffs

    #
    field_values = OrderedDict()
    free_names = [str(f.name) for f in expr.free_symbols]
    for f in fields:
        ls = []
        if f.name in free_names:
            ls.append(f.name)
        for deriv in BASIS_PREFIX:
            f_d = '{field}_{deriv}'.format(field=f.name, deriv=deriv)
            if f_d in free_names:
                ls.append(f_d)

        field_values[f.name] = ls
#    print('>>> field_values = ', field_values)
    # ...

    # ... identation (def function body)
    tab = ' '*4
    # ...

    # ... field values init
    sizes = ','.join('k{}'.format(i) for i in range(1, dim+1))
    if dim > 1:
        sizes = '({})'.format(sizes)

    lines = []
    for k, fs in list(field_values.items()):
        for f in fs:
            line = '{field}_values = zeros({sizes})'.format(field=f, sizes=sizes)
            line = tab + line

            lines.append(line)

    field_init_str = '\n'.join(line for line in lines)
    # ...

    # ... update identation to be inside the loop
    for i in range(0, 2*dim):
        tab += ' '*4

    tab_base = tab
    # ...
#    print('>>>> expr = ', expr)

    # ...
    if dim == 1:
        e_pattern = '{field}{deriv}_values[g1] += {coeff}[jl_1]*Nj{deriv}'
    elif dim == 2:
        e_pattern = '{field}{deriv}_values[g1,g2] += {coeff}[jl_1,jl_2]*Nj{deriv}'
    elif dim ==3:
        e_pattern = '{field}{deriv}_values[g1,g2,g3] += {coeff}[jl_1,jl_2,jl_3]*Nj{deriv}'
    else:
        raise NotImplementedError('only 1d, 2d and 3d are available')

    lines = []
    for k, fs in list(field_values.items()):
        coeff = field_coeffs[k]
        for f in fs:
            ls = f.split('_')
            if len(ls) == 1:
                deriv = ''
            else:
                deriv = '_{}'.format(ls[-1])
            line = e_pattern.format(field=k, deriv=deriv, coeff=coeff)
            line = tab + line

            lines.append(line)

    field_accum_str = '\n'.join(line for line in lines)
    # ...


    # ...
    # TODO
    pattern = 'scalar'
    # ...

    # ...
    template_str = 'eval_field_{dim}d_{pattern}'.format(dim=dim, pattern=pattern)
    try:
        template = eval(template_str)
    except:
        raise ValueError('Could not find the corresponding template {}'.format(template_str))
    # ...

    # ...
    e = _convert_int_to_float(expr)
    # we call evalf to avoid having fortran doing the evaluation of rational
    # division
    field_coeffs_str = ', '.join('{}'.format(c) for c in list(field_coeffs.values()))

    code = template.format(__FIELD_INIT__=field_init_str,
                           __FIELD_ACCUM__=field_accum_str)
    # ...

    return code
