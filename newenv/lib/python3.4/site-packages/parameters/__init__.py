"""
Parameters
==========

A module for dealing with model parameters.

Classes
-------

Parameter
ParameterRange - for specifying a list of possible values for a given parameter.
ParameterReference - specify a parameter in terms of the value of another parameter.
ParameterSet   - for representing/managing hierarchical parameter sets.
ParameterTable - a sub-class of ParameterSet that can represent a table of parameters.
ParameterSpace - a collection of ParameterSets, representing multiple points in
                 parameter space.

**Imported from validators**

ParameterSchema      - A sub-class of ParameterSet against which other ParameterSets can be validated
                       against using a Validator as found in the sub-package validators

CongruencyValidator  - A CongruencyValidator validates a ParameterSet against a ParameterSchema
                       via member "validate(parameter_set,parameter_schema)".

ValidationError      - The Exception raised when validation fails

SchemaBase           - The base class of all "active" Schema objects to be placed in a ParameterSchema.
-> Sublass           - Validates the same-path ParameterSet value if it is of the specified type.
-> Eval              - Validates the same-path ParameterSet value if the provided expression
                       evaluates ("eval") to True.



Functions
---------

nesteddictwalk    - Walk a nested dict structure, using a generator.
nesteddictflatten - Return a flattened version of a nested dict structure.
string_table      - Convert a table written as a multi-line string into a dict of dicts.



Sub-Packages
------------

validators        - A module implementing validation of ParameterSets against ParameterSchema.

"""

from __future__ import absolute_import
import copy
import warnings
import math
import operator
from functools import wraps
try:
    from urllib2 import build_opener, install_opener, urlopen, ProxyHandler  # Python 2
    from urlparse import urlparse
except ImportError:
    from urllib.request import build_opener, install_opener, urlopen, ProxyHandler  # Python 3
    from urllib.parse import urlparse

from os import environ, path
from .random import ParameterDist, GammaDist, UniformDist, NormalDist
import random
from copy import copy

try:
    basestring
except NameError:
    basestring = str

try:
    next                  # Python 3
except NameError:
    def next(obj):        # Python 2
        return obj.next()


__version__ = '0.2.1'

if 'HTTP_PROXY' in environ:
    HTTP_PROXY = environ['HTTP_PROXY']  # user has to define it
    ''' next lines are for communication to urllib of proxy information '''
    proxy_support = ProxyHandler({"https": HTTP_PROXY})
    opener = build_opener(proxy_support, HTTPHandler)
    install_opener(opener)


def isiterable(x):
    return (hasattr(x, '__iter__') and not isinstance(x, basestring))


def contains_instance(collection, cls):
    return any(isinstance(o, cls) for o in collection)


def nesteddictwalk(d, separator='.'):
    """
    Walk a nested dict structure, using a generator.

    Composite keys are created by joining each key to the key of the parent dict
    using `separator`.
    """
    for key1, value1 in d.items():
        if isinstance(value1, dict):
            for key2, value2 in nesteddictwalk(value1, separator):  # recurse into subdict
                    yield "%s%s%s" % (key1, separator, key2), value2
        else:
            yield key1, value1


def nesteddictflatten(d, separator='.'):
    """
    Return a flattened version of a nested dict structure.

    Composite keys are created by joining each key to the key of the parent dict
    using `separator`.
    """
    flatd = {}
    for k, v in nesteddictwalk(d, separator):
        flatd[k] = v
    return flatd


# --- Parameters, and ranges and distributions of them -------------------


class Parameter(object):

    def __init__(self, value, units=None, name=""):
        self.name = name
        self.value = value
        self.units = units
        self.type = type(value)

    def __repr__(self):
        s = "%s = %s" % (self.name, self.value)
        if self.units is not None:
            s += " %s" % self.units
        return s


class ParameterRange(Parameter):
    """
    A class for specifying a list of possible values for a given parameter.

    The value must be an iterable. It acts like a Parameter, but .next() can be
    called to iterate through the values
    """

    def __init__(self, value, units=None, name="", shuffle=False):
        if not isiterable(value):
            raise TypeError("A ParameterRange value must be iterable")
        Parameter.__init__(self, next(value.__iter__()), units, name)
        self._values = copy(value)
        self._iter_values = self._values.__iter__()
        if shuffle:
            random.shuffle(self._values)

    def __repr__(self):
        units_str = ''
        if self.units:
            units_str = ', units="%s"' % self.units
        return 'ParameterRange(%s%s)' % (self._values.__repr__(), units_str)

    def __iter__(self):
        self._iter_values = self._values.__iter__()
        return self._iter_values

    def __next__(self):
        self._value = next(self._iter_values)
        return self._value

    def next(self):
        return self.__next__()

    def __len__(self):
        return len(self._values)

    def __eq__(self, o):
        if (type(self) == type(o) and
            self.name == o.name and
            self._values == o._values and
                self.units == o.units):
            return True
        else:
            return False

# --- ReferenceParameter
def reverse(func):
    """Given a function f(a, b), returns f(b, a)"""
    @wraps(func)
    def reversed_func(a, b):
        return func(b, a)
    reversed_func.__doc__ = "Reversed argument form of %s" % func.__doc__
    reversed_func.__name__ = "reversed %s" % func.__name__
    return reversed_func
    
def lazy_operation(name, reversed=False):
    def op(self, val):
        f = getattr(operator, name)
        if reversed:
           f = reverse(f)
        self.operations.append((f, val))
        return self
    return op

class ParameterReference(object):
    """
    This class provides a place-holder for a reference parameter that will
    later be replaced with the value of the parameter pointed to by the
    reference. This class also allows for lazy application of operations,
    meaning that one can use the reference in simple formulas that will get
    evaluated at the moment the reference is replaced. 
    
    Check below which operations are supported.
    """
    def __init__(self,reference):
        object.__init__(self)  
        self.reference_path = reference
        self.operations = []

    def _apply_operations(self, x):
        for f, arg in self.operations:
            try:
                if arg is None:
                    x = f(x)
                else:
                    x = f(x, arg)
            except TypeError:
                raise TypeError("ParameterReference: error applying operation " + str(f) + " with argument " + str(arg) + " to " + str(x))
        return x
    
    def evaluate(self,parameter_set):
        """
        This function evaluetes the reference, using the ParameterSet in parameter_set as the source.
        """
        ref_value = parameter_set[self.reference_path]
        if isinstance(ref_value,ParameterSet):
           if self.operations == []:
              return ref_value.tree_copy()
           else:
              raise ValueError("ParameterReference: lazy operations cannot be applied to argument of type ParameterSet> %s" % self.reference_path) 
        elif isinstance(ref_value,ParameterReference):
             #lets wait until the refe
             return self
        else:
           return self._apply_operations(ref_value)

    def copy(self):
        pr = ParameterReference(self.reference_path)
        for f, arg in self.operations:
            if isinstance(arg,ParameterReference):
               pr.operations.append((f,arg.copy())) 
            else:
               pr.operations.append((f,arg))      
        return pr
    __add__  = lazy_operation('add')
    __radd__ = __add__
    __sub__  = lazy_operation('sub')
    __rsub__ = lazy_operation('sub', reversed=True)
    __mul__  = lazy_operation('mul')
    __rmul__ = __mul__
    __div__  = lazy_operation('div')
    __rdiv__ = lazy_operation('div', reversed=True)
    __truediv__ = lazy_operation('truediv')
    __rtruediv__ = lazy_operation('truediv', reversed=True)
    __pow__  = lazy_operation('pow')


def load_parameters(parameter_url, modified_parameters):
    """
    This is a function that should be used to load a ParameterSet from a url.
    
    `modified_parameters` should be a dictionary of parameters and their values.
    These will be replaced in the loaded parameter set before the references are
    expanded.
    """
    parameters = ParameterSet(parameter_url)
    parameters.replace_values(**modified_parameters)
    parameters.replace_references()
    return parameters


class ParameterSet(dict):
    """
    A class to manage hierarchical parameter sets.

    Usage example::
    
        >>> sim_params = ParameterSet({'dt': 0.1, 'tstop': 1000.0})
        >>> exc_cell_params = ParameterSet("http://neuralensemble.org/svn/NeuroTools/example.params")
        >>> inh_cell_params = ParameterSet({'tau_m': 15.0, 'cm': 0.5})
        >>> network_params = ParameterSet({'excitatory_cells': exc_cell_params, 'inhibitory_cells': inh_cell_params})
        >>> P = ParameterSet({'sim': sim_params, 'network': network_params})
        >>> P.sim.dt
        0.1
        >>> P.network.inhibitory_cells.tau_m
        15.0
        >>> print P.pretty()

    """

    non_parameter_attributes = ['_url', 'label', 'names', 'parameters', 'flat',
                                'flatten', 'non_parameter_attributes']
    invalid_names = ['parameters', 'names']  # should probably add dir(dict)

    @staticmethod
    def read_from_str(s, update_namespace=None):
        """
        `ParameterSet` definition `s` should be a Python dict definition
        string, containing objects of types `int`, `float`, `str`, `list`,
        `dict` plus the classes defined in this module, `Parameter`,
        `ParameterRange`, etc.  No other object types are allowed,
        except the function `url('some_url')` or `ref('point.delimited.path')`,
        e.g.::
        
            { 'a' : {'A': 3, 'B': 4},
              'b' : [1,2,3],
              'c' : 'hello world',
              'd' : url('http://example.com/my_cool_parameter_set')
              'e' : ref('level1_param_name.level2_param_name.level3_param_name') }

        This is largely the JSON (www.json.org) format, but with
        extra keywords in the namespace such as `ParameterRange`, `GammaDist`, etc.
        """
        global_dict = dict(ref=ParameterReference,
                           url=ParameterSet,
                           ParameterSet=ParameterSet,
                           ParameterRange=ParameterRange,
                           ParameterTable=ParameterTable,
                           GammaDist=GammaDist,
                           UniformDist=UniformDist,
                           NormalDist=NormalDist,
                           pi=math.pi,
                           true=True,    # these are for reading JSON
                           false=False,  # files
                        )
        if update_namespace:
            global_dict.update(update_namespace)

        D = None
        try:
            if 'file://' in s:
                path = s.split('file://')[1]
                ifile = open(path, 'r')
                content = ifile.read()
                ifile.close()
                D = eval(content, global_dict)
            else:
                D = eval(s, global_dict)
        except SyntaxError as e:
            raise SyntaxError(
                "Invalid string for ParameterSet definition: %s\n%s" % (s, e))
        except TypeError as e:
            raise SyntaxError(
                "Invalid string for ParameterSet definition: %s" % e)
        return D or {}

    @staticmethod
    def check_validity(k):
        """docstring missing"""
        if k in ParameterSet.invalid_names:
            raise Exception("'%s' is not allowed as a parameter name." % k)

    def __init__(self, initialiser, label=None, update_namespace=None):

        def walk(d, label):
            # Iterate through the dictionary `d`, replacing `dict`s by
            # `ParameterSet` objects.
            for k, v in d.items():
                ParameterSet.check_validity(k)
                if isinstance(v, ParameterSet):
                    d[k] = v
                elif isinstance(v, dict):
                    d[k] = walk(v, k)
                else:
                    d[k] = v
            return ParameterSet(d, label)

        self._url = None
        if isinstance(initialiser, basestring):  # url or str
            if path.exists(initialiser):
                f = open(initialiser, 'r')
                pstr = f.read()
                self._url = initialiser
                f.close()
            else:
                try:
                    f = urlopen(initialiser)
                    pstr = f.read().decode()
                    self._url = initialiser
                except IOError as e:
                    pstr = initialiser
                    self._url = None
                else:
                    f.close()

            # is it a yaml url?
            if self._url:
                o = urlparse(self._url)
                base, ext = path.splitext(o.path)
                if ext in ['.yaml', '.yml']:
                    import yaml
                    initialiser = yaml.load(pstr)
                else:
                    initialiser = ParameterSet.read_from_str(pstr,
                                                             update_namespace)
            else:
                initialiser = ParameterSet.read_from_str(pstr,
                                                         update_namespace)

        # By this stage, `initialiser` should be a dict. Iterate through it,
        # copying its contents into the current instance, and replacing dicts by
        # ParameterSet objects.
        if isinstance(initialiser, dict):
            for k, v in initialiser.items():
                ParameterSet.check_validity(k)
                if isinstance(v, ParameterSet):
                    self[k] = v
                elif isinstance(v, dict):
                    self[k] = walk(v, k)
                else:
                    self[k] = v
        else:
            raise TypeError(
                "`initialiser` must be a `dict`, a `ParameterSet` object, a string, or a valid URL")

        # Set the label
        if hasattr(initialiser, 'label'):
            self.label = label or initialiser.label  # if initialiser was a ParameterSet, keep the existing label if the label arg is None
        else:
            self.label = label

        # Define some aliases, allowing, e.g.:
        # for name, value in P.parameters():
        # for name in P.names():
        self.names = self.keys
        self.parameters = self.items

    def flat(self):
        __doc__ = nesteddictwalk.__doc__
        return nesteddictwalk(self)

    def flatten(self):
        __doc__ = nesteddictflatten.__doc__
        return nesteddictflatten(self)

    def __getattr__(self, name):
        """Allow accessing parameters using dot notation."""
        try:
            return self[name]
        except KeyError:
            return self.__getattribute__(name)

    def __setattr__(self, name, value):
        """Allow setting parameters using dot notation."""
        if name in self.non_parameter_attributes:
            object.__setattr__(self, name, value)
        else:
            # should we check the parameter type hasn't changed?
            self[name] = value

    def __getitem__(self, name):
        """ Modified get that detects dots '.' in the names and goes down the
        nested tree to find it"""
        split = name.split('.', 1)
        if len(split) == 1:
            return dict.__getitem__(self, name)
        # nested get
        return dict.__getitem__(self, split[0])[split[1]]

    def flat_add(self, name, value):
        """ Like `__setitem__`, but it will add `ParameterSet({})` objects
        into the namespace tree if needed. """

        split = name.split('.', 1)
        if len(split) == 1:
            dict.__setitem__(self, name, value)
        else:
            # nested set
            try:
                ps = dict.__getitem__(self, split[0])
            except KeyError:
                # setting nested name without parent existing
                # create parent
                ps = ParameterSet({})
                dict.__setitem__(self, split[0], ps)
                # and try again
            ps.flat_add(split[1], value)

    def __setitem__(self, name, value):
        """ Modified set that detects dots '.' in the names and goes down the
        nested tree to set it """
        split = name.split('.', 1)
        if len(split) == 1:
            dict.__setitem__(self, name, value)
        else:
            # nested set
            dict.__getitem__(self, split[0])[split[1]] = value

    def update(self, E, **F):
        """docstring missing"""
        if hasattr(E, "has_key"):
            for k in E:
                self[k] = E[k]
        else:
            for (k, v) in E:
                self[k] = v
        for k in F:
            self[k] = F[k]

    # should __len__() be the usual dict length, or the flattened length? Probably the former for consistency with dicts
    # can always use len(ps.flatten())

    # what about __contains__()? Should we drill down to lower levels in the
    # hierarchy? I think so.

    def __getstate__(self):
        """For pickling."""
        return self

    def save(self, url=None, expand_urls=False):
        """
        Write the parameter set to a text file.

        The text file syntax is open to discussion. My idea is that it should be
        valid Python code, preferably importable as a module.

        If `url` is `None`, try to save to `self._url` (if it is not `None`),
        otherwise save to `url`.
        """
        # possible solution for HTTP PUT: http://inamidst.com/proj/put/put.py
        if not url:
            url = self._url
        assert url != ''
        if not self._url:
            self._url = url
        scheme, netloc, path, parameters, query, fragment = urlparse(url)
        if scheme == 'file' or (scheme == '' and netloc == ''):
            f = open(path, 'w')
            f.write(self.pretty(expand_urls=expand_urls))
            f.close()
        else:
            if scheme:
                raise Exception(
                    "Saving using the %s protocol is not implemented" % scheme)
            else:
                raise Exception("No protocol (http, ftp, etc) specified.")

    def pretty(self, indent='  ', expand_urls=False):
        """
        Return a unicode string representing the structure of the `ParameterSet`.
        evaluating the string should recreate the object.
        """
        def walk(d, indent, ind_incr):
            s = []
            for k, v in d.items():
                if hasattr(v, 'items'):
                    if expand_urls is False and hasattr(v, '_url') and v._url:
                        s.append('%s"%s": url("%s"),' % (indent, k, v._url))
                    else:
                        s.append('%s"%s": {' % (indent, k))
                        s.append(walk(v, indent+ind_incr,  ind_incr))
                        s.append('%s},' % indent)
                elif isinstance(v, basestring):
                    s.append('%s"%s": "%s",' % (indent, k, v))
                else:  # what if we have a dict or ParameterSet inside a list? currently they are not expanded. Should they be?
                    s.append('%s"%s": %s,' % (indent, k, v))
            return '\n'.join(s)
        return '{\n' + walk(self, indent, indent) + '\n}'

    def tree_copy(self):
        """Return a copy of the `ParameterSet` tree structure.
        Nodes are not copied, but re-referenced."""

        tmp = ParameterSet({})
        for key in self:
            value = self[key]
            if isinstance(value, ParameterSet):
                tmp[key] = value.tree_copy()
            elif isinstance(value,ParameterReference):                
                tmp[key] = value.copy()
            else:
                tmp[key] = value
        if tmp._is_space():
            tmp = ParameterSpace(tmp)
        return tmp

    def as_dict(self):
        """Return a copy of the `ParameterSet` tree structure
        as a nested dictionary"""

        tmp = {}

        for key in self:
            value = self[key]
            if isinstance(value, ParameterSet):
                # recurse
                tmp[key] = value.as_dict()
            else:
                tmp[key] = value
        return tmp

    def __sub__(self, other):
        """
        Return the difference between this `ParameterSet` and another.
        Not yet properly implemented.
        """
        self_keys = set(self)
        other_keys = set(other)
        intersection = self_keys.intersection(other_keys)
        difference1 = self_keys.difference(other_keys)
        difference2 = other_keys.difference(self_keys)
        result1 = dict([(key, self[key]) for key in difference1])
        result2 = dict([(key, other[key]) for key in difference2])
        # Now need to check values for intersection....
        for item in intersection:
            if isinstance(self[item], ParameterSet):
                d1, d2 = self[item] - other[item]
                if d1:
                    result1[item] = d1
                if d2:
                    result2[item] = d2
            elif self[item] != other[item]:
                result1[item] = self[item]
                result2[item] = other[item]
        if len(result1) + len(result2) == 0:
            assert self == other, "Error in ParameterSet.diff()"
        return result1, result2

    def _is_space(self):
        """
        Check for the presence of `ParameterRanges` or `ParameterDists` to
        determine if this is a `ParameterSet` or a `ParameterSpace`.
        """
        for k, v in self.flat():
            if isinstance(v, ParameterRange) or isinstance(v, ParameterDist):
                return True
        return False

    def export(self, filename, format='latex', **kwargs):
        """
        docstring missing
        """
        if format == 'latex':
            from .export import parameters_to_latex
            parameters_to_latex(filename, self, **kwargs)
    
    def replace_references(self):
        while True:
            refs = self.find_references()
            if len(refs) == 0:
                break
            for s, k, v in refs:
                s[k] = v.evaluate(self)
                    
                    
    def find_references(self):
        l = []
        for k, v in self.items():
            if isinstance(v, ParameterReference):
               l += [(self, k, v)]
            elif isinstance(v, ParameterSet):   
               l += v.find_references()
        return l    
    
    def replace_values(self,**args):
        """
        This expects its arguments to be in the form path=value, where path is a
        . (dot) delimited path to a parameter in the  parameter tree rooted in
        this ParameterSet instance. 
        
        This function replaces the values of each parameter in the args with the
        corresponding values supplied in the arguments.
        """
        for k in args.keys():
            self[k] = args[k]


class ParameterSpace(ParameterSet):
    """
    A collection of `ParameterSets`, representing multiple points in
    parameter space. Created by putting `ParameterRange` and/or `ParameterDist`
    objects within a `ParameterSet`.
    """

    def iter_range_key(self, range_key):
        """ An iterator of the `ParameterSpace` which yields the
        `ParameterSet` with the `ParameterRange` given by `range_key` replaced with
        each of its values"""

        tmp = self.tree_copy()
        for val in self[range_key]:
            tmp[range_key] = val
            yield tmp

    def iter_inner_range_keys(self, keys, copy=False):
        """ An iterator of the `ParameterSpace` which yields
        `ParameterSets` with all combinations of `ParameterRange` elements
        which are given by the `keys` list.

        Note: each newly yielded value is one and the same object
        so storing the returned values results in a collection
        of many of the lastly yielded object.

        `copy=True` causes each yielded object to be a newly
        created object, but be careful because this is
        spawning many dictionaries!

        """
        if len(keys) == 0:
            # return an iterator over 1 copy for modifying
            yield self.tree_copy()
            return

        if not copy:
            # recursively iterate over remaining keys
            for tmp in self.iter_inner_range_keys(keys[1:]):
                # iterator over range of our present attention
                for val in self[keys[0]]:
                    tmp[keys[0]] = val
                    if not tmp._is_space():
                        tmp = ParameterSet(tmp)
                    yield tmp
        else:
            # Each yielded ParameterSet is a tree_copy of self

            # recursively iterate over remaining keys
            for tmp in self.iter_inner_range_keys(keys[1:]):
                # iterator over range of our present attention
                for val in self[keys[0]]:
                    tmp_copy = tmp.tree_copy()
                    tmp_copy[keys[0]] = val
                    if not tmp_copy._is_space():
                        tmp = ParameterSet(tmp)
                    yield tmp_copy

    def range_keys(self):
        """Return the list of keys for those elements which are `ParameterRanges`."""
        return [key for key, value in self.flat() if isinstance(value, ParameterRange)]

    def iter_inner(self, copy=False):
        """An iterator of the `ParameterSpace` which yields
        `ParameterSets` with all combinations of `ParameterRange` elements"""
        return self.iter_inner_range_keys(self.range_keys(), copy)

    def num_conditions(self):
        """Return the number of `ParameterSets` that will be returned by the
        `iter_inner()` method."""
        # Not properly tested
        n = 1
        for key in self.range_keys():
            n *= len(self[key])
        return n

    def dist_keys(self):
        """Return the list of keys for those elements which are `ParameterDists`."""
        def is_or_contains_dist(value):
            return isinstance(value, ParameterDist) or (
                isiterable(value) and contains_instance(value, ParameterDist))
        return [key for key, value in self.flat() if is_or_contains_dist(value)]

    def realize_dists(self, n=1, copy=False):
        """For each `ParameterDist`, realize the distribution and yield the result.

        If `copy==True`, causes each yielded object to be a newly
        created object, but be careful because this is
        spawning many dictionaries!"""
        def next(item, n):
            if isinstance(item, ParameterDist):
                return item.next(n)
            else:
                return [item]*n
        # pre-generate random numbers
        rngs = {}
        for key in self.dist_keys():
            if isiterable(self[key]):
                rngs[key] = [next(item, n) for item in self[key]]
            else:
                rngs[key] = self[key].next(n)
        # get a copy to fill in the rngs
        if copy:
            tmp = self.tree_copy()
            for i in range(n):
                for key in rngs:
                    if isiterable(self[key]):
                        tmp[key] = [rngs[key][j][i]
                                    for j in range(len(rngs[key]))]
                    else:
                        tmp[key] = rngs[key][i]
                yield tmp.tree_copy()
        else:
            tmp = self.tree_copy()
            for i in range(n):
                for key in rngs:
                    if isiterable(self[key]):
                        tmp[key] = [rngs[key][j][i]
                                    for j in range(len(rngs[key]))]
                    else:
                        tmp[key] = rngs[key][i]
                yield tmp

    def parameter_space_dimension_labels(self):
        """
        Return the dimensions and labels of the keys for those elements which are `ParameterRanges`.
        `range_keys` are sorted to ensure the same ordering each time.
        """
        range_keys = self.range_keys()
        range_keys.sort()

        dim = []
        label = []
        for key in range_keys:
            label.append(key)
            dim.append(len(eval('self.'+key)))

        return dim, label

    def parameter_space_index(self, current_experiment):
        """
        Return the index of the current experiment in the dimension of the parameter space
        i.e. parameter space dimension: [2,3]
        i.e. index: (1,0)

        Example::

            p = ParameterSet({})
            p.b = ParameterRange([1,2,3])
            p.a = ParameterRange(['p','y','t','h','o','n'])

            results_dim, results_label = p.parameter_space_dimension_labels()

            results = numpy.empty(results_dim)
            for experiment in p.iter_inner():
                index = p.parameter_space_index(experiment)
                results[index] = 2.

        """
        index = []
        range_keys = self.range_keys()
        range_keys.sort()
        for key in range_keys:
            value = eval('current_experiment.'+key)
            try:
                value_index = list(eval('self.'+key)._values).index(value)
            except ValueError:
                raise ValueError(
                    "The ParameterSet provided is not within the ParameterSpace")
            index.append(value_index)
        return tuple(index)

    def get_ranges_values(self):
        """
        Return a dict with the keys and values of the parameters with `ParameterRanges`

        Example::

            >>> p = ParameterSpace({})
            >>> p.b = ParameterRange([1,2,3])
            >>> p.a = ParameterRange(['p','y','t','h','o','n'])
            >>> data = p.get_ranges_values()
            >>> data
            {'a': ['p', 'y', 't', 'h', 'o', 'n'], 'b': [1, 2, 3]}

        """
        data = {}
        range_keys = self.range_keys()
        range_keys.sort()
        for key in range_keys:
            data[key] = eval('self.'+key)._values
        return data


def string_table(tablestring):
    """Convert a table written as a multi-line string into a dict of dicts."""
    tabledict = {}
    rows = tablestring.strip().split('\n')
    column_headers = rows[0].split()
    for row in rows[1:]:
        row = row.split()
        row_header = row[0]
        tabledict[row_header] = {}
        for col_header, item in zip(column_headers[1:], row[1:]):
            tabledict[row_header][col_header] = float(item)
    return tabledict


class ParameterTable(ParameterSet):
    """
    A sub-class of `ParameterSet` that can represent a table of parameters.

    i.e., it is limited to one-level of nesting, and each sub-dict must have
    the same keys. In addition to the possible initialisers for ParameterSet,
    a ParameterTable can be initialised from a multi-line string, e.g.::

        >>> pt = ParameterTable('''
        ...     #       col1    col2    col3
        ...     row1     1       2       3
        ...     row2     4       5       6
        ...     row3     7       8       9
        ... ''')
        >>> pt.row2.col3
        6.0
        >>> pt.column('col1')
        {'row1': 1.0, 'row2': 4.0, 'row3': 7.0}
        >>> pt.transpose().col3.row2
        6.0

    """

    non_parameter_attributes = ParameterSet.non_parameter_attributes + \
        ['row', 'rows', 'row_labels',
         'column', 'columns', 'column_labels']

    def __init__(self, initialiser, label=None):
        if isinstance(initialiser, basestring):  # url or table string
            tabledict = string_table(initialiser)
            # if initialiser is a URL, string_table() should return an empty dict
            # since URLs do not contain spaces.
            if tabledict:  # string table
                initialiser = tabledict
        ParameterSet.__init__(self, initialiser, label)
        # Now need to check that the contents actually define a table, i.e.
        # two levels of nesting and each sub-dict has the same keys
        self._check_is_table()

        self.rows = self.items
        # self.rows.__doc__ = "Return a list of (row_label, row) pairs, as 2-tuples."""
        self.row_labels = self.keys
        # self.row_labels.__doc__ = "Return a list of row labels."

    def _check_is_table(self):
        """
        Checks that the contents actually define a table, i.e.
        one level of nesting and each sub-dict has the same keys.
        Raises an `Exception` if these requirements are violated.
        """
        # to be implemented
        pass

    def row(self, row_label):
        """Return a `ParameterSet` object containing the requested row."""
        return self[row_label]

    def column(self, column_label):
        """Return a `ParameterSet` object containing the requested column."""
        col = {}
        for row_label, row in self.rows():
            col[row_label] = row[column_label]
        return ParameterSet(col)

    def columns(self):
        """Return a list of `(column_label, column)` pairs, as 2-tuples."""
        return [(column_label, self.column(column_label)) for column_label in self.column_labels()]

    def column_labels(self):
        """Return a list of column labels."""
        sample_row = self[list(self.row_labels())[0]]
        return sample_row.keys()

    def transpose(self):
        """
        Return a new `ParameterTable` object with the same data as the current
        one but with rows and columns swapped.
        """
        new_table = ParameterTable({})
        for column_label, column in self.columns():
            new_table[column_label] = column
        return new_table

    def table_string(self):
        """
        Returns the table as a string, suitable for being used as the
        initialiser for a new `ParameterTable`.
        """
        # formatting could definitely be improved
        column_labels = self.column_labels()
        lines = ["#\t " + "\t".join(column_labels)]
        for row_label, row in self.rows():
            lines.append(
                row_label + "\t" + "\t".join(["%s" % row[col]
                                              for col in column_labels]))
        return "\n".join(lines)
