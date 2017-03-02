"""
parameters.validators
=====================

A module implementing validation of ParameterSets against ParameterSchema.

Classes
-------

SchemaBase           - The base class of all "active" Schema objects to be placed in a ParameterSchema.
-> Sublass           - Validates the same-path ParameterSet value if it is of the specified type.
-> Eval              - Validates the same-path ParameterSet value if the provided expression
                       evaluates ("eval") to True.

ParameterSchema      - A sub-class of ParameterSet against which other ParameterSets
                       can be validated against.

CongruencyValidator  - A CongruencyValidator validates a ParameterSet against a ParameterSchema
                       via member "validate(parameter_set,parameter_schema)".

ValidationError      - The Exception raised when validation fails

Functions
---------

congruent_dicts      - returns True if two nested dictionaries have the same key heirarchy,
                       otherwise False.


See also: parameters

"""

from __future__ import absolute_import
import yaml
from parameters import ParameterSet
import parameters


class SchemaBase(object):
    """ The base class of all "active" `Schema` objects to be placed in a `ParameterSchema`.

    Schema objects define the "validate" member which accepts the to-be-validated `ParameterSet`
    value from the same path as the `Schema` object in the `ParameterSchema` and returns True if
    the value is valid, otherwise False.

    """

    def __init__(self):
        pass

    def validate(self, leaf):
        return False

    def __repr__(self):
        cls = self.__class__
        return '.'.join([cls.__module__, cls.__name__])+'()'


class Subclass(SchemaBase):
    """
    To be used as a value in a `ParameterSchema`.  Validates the same-path
    `ParameterSet` value if it is of the specified type.

    See also: `SchemaBase`
    """

    def __init__(self, type=None):
        self.type = type

    def validate(self, leaf):
        return isinstance(leaf, self.type)

    def __repr__(self):
        cls = self.__class__
        return '.'.join([cls.__module__, cls.__name__])+'(type=%s)' % (self.type.__name__)

    def __eq__(self, x):
        if isinstance(x, Subclass):
            return self.type == x.type
        else:
            return False


class Eval(SchemaBase):
    """
    To be used as a value in a `ParameterSchema`.  Validates the same-path
    `ParameterSet` value if the provided expression (with `leaf(value)` mapped to var in eval local namespace)
    evaluates to True.

    See also: `SchemaBase`
    """

    def __init__(self, expr, var='leaf'):
        self.var = var
        self.expr = expr

    def validate(self, leaf):
        l = {}
        l[self.var] = leaf
        return eval(self.expr, {}, l)

    def __repr__(self):
        cls = self.__class__
        return '.'.join([cls.__module__, cls.__name__])+'(%s,var=%s)' % (self.expr, self.var)

    def __eq__(self, x):
        if isinstance(x, Eval):
            return self.expr == x.expr and self.var == x.var
        else:
            return False


# add all schema checkers to this list
schema_checkers = [Subclass, Eval]
# create a namespace of schema_checkers
schema_checkers_namespace = {}
for x in schema_checkers:
    schema_checkers_namespace[x.__class__.__name__] = x


class ParameterSchema(ParameterSet):
    """
    A sub-class of `ParameterSet` against which other ParameterSets can be validated.

    Presently, it is more or less a `ParameterSet`, with all leafs(values) which are not explicitly
    a subclass of the `SchemaBase` object replaced by a `Subclass(type=<leaf(value) type>)` instance.

    `ParameterSchema` may contain arbitrary `Schema` objects subclassed from `SchemaBase` which
    validate leafs by the member function `validate(leaf)` returning True or false if the given
    leaf in the `ParameterSet` at the same path should be validated or not, e.g.::

        LambdaSchema('isinstance(x,str)',var='x'),
        *unimplemented* Timedate('%.2d-%.2m-%.2y'), etc.
        *unimplemented* Email()
        *unimplemented* Url()
        *unimplemented* File()
        *unimplemented* FileExists()

    etc.

    Example:

        >>> schema = ParameterSchema({'age': 0, 'height': Subclass(float)})
        >>> # is equivalent to
        >>> schema = ParameterSchema({'age': Subclass(int), 'height': Subclass(float)})

    See also: `SchemaBase`, `Eval`, `Subclass`

    """

    def __init__(self, initializer):
        import types
        ps = initializer

        # try to create a ParameterSet from ps if
        # it is not one already
        if not isinstance(ps, ParameterSet):
            # create ParameterSet, but allowing SchemaBase derived objects
            ps = ParameterSet(ps, update_namespace=schema_checkers_namespace)

        # convert each element
        for x in ps.flat():
            key = x[0]
            value = x[1]
            if isinstance(value, SchemaBase):
                self.flat_add(key, value)
            else:
                self.flat_add(key, Subclass(type=type(value)))


class ValidationError(Exception):
    """ Raised when `ParameterSchema` validation fails, and provides failure information

    See also: `CongruencyValidator`, `ParameterSchema`

    """

    def __init__(self, path='', schema_base=None, parameter=None):
        self.path = path
        self.schema_base = schema_base
        self.parameter = parameter

    def __str__(self):
        return 'validation error @ %s: parameter "%s" failed against schema: %s' % (self.path, self.parameter, self.schema_base)


class CongruencyValidator(object):
    """
    A `CongruencyValidator` validates a `ParameterSet` against a `ParameterSchema`
    either returning `True`, or raising a `ValidationError` with the path, `SchemaBase` subclass
    and parameter value for which the validation failed.

    The `CongruencyValidator` expects all names defined in the schema to be present in the parameter set
    and vice-versa, and will run validation for each item in the namespace tree.

    The validation functionality is available via the "validate" member
    `CongruencyValidator.validate(parameter_set, parameter_schema)`

    Example::

        validator = CongruencyValidator()
        try:
           validator.validate(parameter_set,parameter_schema)
        except ValidationError, e:

    See also: `ParameterSet`, `ParameterSchema`
    """

    def __init__(self):
        pass

    def validate(self, parameter_set, parameter_schema):
        """
        Validates a `ParameterSet` against a `ParameterSchema`
        either returning `True`, or raising a `ValidationError` with the path and `SchemaBase` subclass
        for which validation failed.


        Expects all names defined in the schema to be present in the parameter set
        and vice-versa, and will run validation for each item in the namespace tree.

        See also: `CongruencyValidator`.

        """

        ps = parameter_set
        schema = parameter_schema

        ps_keys = set()
        schema_keys = set()

        for path, sb in schema.flat():
            try:
                val = ps[path]
            except KeyError:
                raise ValidationError(path=path, schema_base=sb,
                                      parameter='<MISSING>')
            if not sb.validate(val):
                raise ValidationError(path=path, schema_base=sb, parameter=val)

        for path, val in ps.flat():
            try:
                sb = schema[path]
            except KeyError:
                raise ValidationError(path=path, schema_base='<MISSING>',
                                      parameter=val)

        return True


def congruent_dicts(template, candidate, subset=False, parent_path=''):
    """Return True if d1 and d2 have same key heirarchy, otherwise False

    if subset=True, the key heirarchy of d2 maybe a subset
    """

    dt = template
    dc = candidate

    # if one is a dict, and the other not, return False

    types = (isinstance(dt, dict), isinstance(dc, dict))

    # both are not dicts, return True (for recursion)
    if all([type == False for type in types]):
        return True

    if all(types):
        # both are dicts

        dt_keys_set = set(dt.keys())
        dc_keys_set = set(dc.keys())

        missing_keys = dt_keys_set-dc_keys_set
        # keys in d2 which are unknown to d1
        unknown_keys = dc_keys_set-dt_keys_set
        keys_intersection = dt_keys_set.intersection(dc_keys_set)

        # candidate has spurious keys
        if unknown_keys:
            return False
        # candidate is missing keys which are expected
        if not subset and missing_keys:
            return False

        # check that all sub dicts are congruent.
        subs_congruent = [congruent_dicts(template[key], candidate[key], subset)
                          for key in keys_intersection]
        return all(subs_congruent)

    else:
        # inhomogeneousisms are underway
        # if subset, then return True if d1 is a dict (then d2 is not a dict)
        if subset and types[0]:
            return True

        # one is a dict, and the other not.
        return False


# Add to parameters on import
parameters.ParameterSchema = ParameterSchema
parameters.Subclass = Subclass
parameters.Eval = Eval
parameters.SchemaBase = SchemaBase
parameters.CongruencyValidator = CongruencyValidator
parameters.ValidationError = ValidationError
