# -*- coding: utf-8 -*-
"""This module contains the tracked object classes.

TrackedObject forms the basis for both the TrackedDict and the TrackedList.

A function for automatic conversion of dicts and lists to their tracked
counterparts is also included.
"""

# Standard modules
import itertools
import logging
import sqlalchemy
import json
from six import iteritems
from collections import OrderedDict
from sqlalchemy.ext.mutable import Mutable, MutableDict
from sqlalchemy_utils.types.json import JSONType
import sqlalchemy.types as types

__all__ = 'MutableJson', 'NestedMutableJson', 'LowerCaseText'


class LowerCaseText(types.TypeDecorator):
    """Converts strings to lower case on the way in."""
    impl = types.String

    def process_bind_param(self, value, dialect):
        value = value if value is not None else ''
        return value.lower().strip()


class TrackedObject(object):
    """A base class for delegated change-tracking."""
    _type_mapping = {}

    def __init__(self, *args, **kwds):
        self.logger = logging.getLogger(type(self).__name__)
        self.parent = None
        self.logger.debug('%s: __init__', self._repr())
        super(TrackedObject, self).__init__(*args, **kwds)

    def changed(self, message=None, *args):
        """Marks the object as changed.

        If a `parent` attribute is set, the `changed()` method on the parent
        will be called, propagating the change notification up the chain.

        The message (if provided) will be debug logged.
        """
        if message is not None:
            self.logger.debug('%s: %s', self._repr(), message % args)
        self.logger.debug('%s: changed', self._repr())
        if self.parent is not None:
            self.parent.changed()
        elif isinstance(self, Mutable):
            super(TrackedObject, self).changed()

    @classmethod
    def register(cls, origin_type):
        """Decorator for mutation tracker registration.

        The provided `origin_type` is mapped to the decorated class such that
        future calls to `convert()` will convert the object of `origin_type`
        to an instance of the decorated class.
        """
        def decorator(tracked_type):
            """Adds the decorated class to the `_type_mapping` dictionary."""
            cls._type_mapping[origin_type] = tracked_type
            return tracked_type
        return decorator

    @classmethod
    def convert(cls, obj, parent):
        """Converts objects to registered tracked types

        This checks the type of the given object against the registered tracked
        types. When a match is found, the given object will be converted to the
        tracked type, its parent set to the provided parent, and returned.

        If its type does not occur in the registered types mapping, the object
        is returned unchanged.
        """
        replacement_type = cls._type_mapping.get(type(obj))
        if replacement_type is not None:
            new = replacement_type(obj)
            new.parent = parent
            return new
        return obj

    def convert_iterable(self, iterable):
        """Generator to `convert` every member of the given iterable."""
        return (self.convert(item, self) for item in iterable)

    def convert_items(self, items):
        """Generator like `convert_iterable`, but for 2-tuple iterators."""
        return ((key, self.convert(value, self)) for key, value in items)

    def convert_mapping(self, mapping):
        """Convenience method to track either a dict or a 2-tuple iterator."""
        if isinstance(mapping, dict):
            return self.convert_items(iteritems(mapping))
        return self.convert_items(mapping)

    def _repr(self):
        """Simple object representation."""
        return '<%(namespace)s.%(type)s object at 0x%(address)0xd>' % {
            'namespace': __name__,
            'type': type(self).__name__,
            'address': id(self)}


@TrackedObject.register(dict)
class TrackedDict(TrackedObject, dict):
    """A TrackedObject implementation of the basic dictionary."""
    def __init__(self, source=(), **kwds):
        super(TrackedDict, self).__init__(itertools.chain(
            self.convert_mapping(source),
            self.convert_mapping(kwds)))

    def __setitem__(self, key, value):
        self.changed('__setitem__: %r=%r', key, value)
        super(TrackedDict, self).__setitem__(key, self.convert(value, self))

    def __delitem__(self, key):
        self.changed('__delitem__: %r', key)
        super(TrackedDict, self).__delitem__(key)

    def clear(self):
        self.changed('clear')
        super(TrackedDict, self).clear()

    def pop(self, *key_and_default):
        self.changed('pop: %r', key_and_default)
        return super(TrackedDict, self).pop(*key_and_default)

    def popitem(self):
        self.changed('popitem')
        return super(TrackedDict, self).popitem()

    def update(self, source=(), **kwds):
        self.changed('update(%r, %r)', source, kwds)
        super(TrackedDict, self).update(itertools.chain(
            self.convert_mapping(source),
            self.convert_mapping(kwds)))


@TrackedObject.register(list)
class TrackedList(TrackedObject, list):
    """A TrackedObject implementation of the basic list."""
    def __init__(self, iterable=()):
        super(TrackedList, self).__init__(self.convert_iterable(iterable))

    def __setitem__(self, key, value):
        self.changed('__setitem__: %r=%r', key, value)
        super(TrackedList, self).__setitem__(key, self.convert(value, self))

    def __delitem__(self, key):
        self.changed('__delitem__: %r', key)
        super(TrackedList, self).__delitem__(key)

    def append(self, item):
        self.changed('append: %r', item)
        super(TrackedList, self).append(self.convert(item, self))

    def extend(self, iterable):
        self.changed('extend: %r', iterable)
        super(TrackedList, self).extend(self.convert_iterable(iterable))

    def remove(self, value):
        self.changed('remove: %r', value)
        return super(TrackedList, self).remove(value)

    def pop(self, index):
        self.changed('pop: %d', index)
        return super(TrackedList, self).pop(index)

    def sort(self, cmp=None, key=None, reverse=False):
        self.changed('sort')
        super(TrackedList, self).sort(cmp=cmp, key=key, reverse=reverse)


class MutationObj(Mutable):
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, OrderedDict) and \
                not isinstance(value, MutationDict):
            return MutationDict.coerce(key, value)
        return value

    @classmethod
    def _listen_on_attribute(cls, attribute, coerce, parent_cls):
        key = attribute.key
        if parent_cls is not attribute.class_:
            return

        # rely on "propagate" here
        parent_cls = attribute.class_

        def load(state, *args):
            val = state.dict.get(key, None)
            if coerce:
                val = cls.coerce(key, val)
                state.dict[key] = val
            if isinstance(val, cls):
                val._parents[state.obj()] = key

        def set(target, value, oldvalue, initiator):
            if not isinstance(value, cls):
                value = cls.coerce(key, value)
            if isinstance(value, cls):
                value._parents[target.obj()] = key
            if isinstance(oldvalue, cls):
                oldvalue._parents.pop(target.obj(), None)
            return value

        def pickle(state, state_dict):
            val = state.dict.get(key, None)
            if isinstance(val, cls):
                if 'ext.mutable.values' not in state_dict:
                    state_dict['ext.mutable.values'] = []
                state_dict['ext.mutable.values'].append(val)

        def unpickle(state, state_dict):
            if 'ext.mutable.values' in state_dict:
                for val in state_dict['ext.mutable.values']:
                    val._parents[state.obj()] = key

        sqlalchemy.event.listen(parent_cls, 'load', load,
                                raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'refresh',
                                load, raw=True, propagate=True)
        sqlalchemy.event.listen(attribute, 'set', set,
                                raw=True, retval=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'pickle',
                                pickle, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'unpickle',
                                unpickle, raw=True, propagate=True)


class MutationDict(MutationObj, OrderedDict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to MutationDict"""
        self = MutationDict((k, MutationObj.coerce(key, v))
                            for (k, v) in value.items())
        self._key = key
        return self

    def __setitem__(self, key, value):
        # Due to the way OrderedDict works, this is called during __init__.
        # At this time we don't have a key set, but what is more, the value
        # being set has already been coerced. So special case this and skip.
        if hasattr(self, '_key'):
            value = MutationObj.coerce(self._key, value)
        OrderedDict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        OrderedDict.__delitem__(self, key)
        self.changed()


class NestedMutableDict(TrackedDict, Mutable):
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, dict):
            return cls(value)
        return super(cls).coerce(key, value)


class NestedMutableList(TrackedList, Mutable):
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, list):
            return cls(value)
        return super(cls).coerce(key, value)


class NestedMutable(Mutable):
    """SQLAlchemy `mutable` extension with nested change tracking."""
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to NestedMutable."""
        if value is None:
            return value
        if isinstance(value, cls):
            return value
        if isinstance(value, OrderedDict):
            return MutationDict.coerce(key, value)
        if isinstance(value, dict):
            return NestedMutableDict.coerce(key, value)
        if isinstance(value, list):
            return NestedMutableList.coerce(key, value)
        return super(cls).coerce(key, value)


class MutableJson(JSONType):
    """JSON type for SQLAlchemy with change tracking at top level."""


class NestedMutableJson(JSONType):
    """JSON type for SQLAlchemy with nested change tracking."""

    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        if value is not None:
            value = json.loads(value, object_pairs_hook=OrderedDict)
        return value


MutableDict.associate_with(MutableJson)
NestedMutable.associate_with(NestedMutableJson)
