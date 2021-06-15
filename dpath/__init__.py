from typing import Any, Union

from dpath import segments
from dpath.exceptions import InvalidKeyName


_DEFAULT_SENTINEL = object()


def _split_path(path, separator):
    # type: (str, str) -> Union[list[Union[int, Any]], Union[int, Any]]
    """
    Given a path and separator, return a list of segments. If path is
    already a non-leaf thing, return it. TODO(moo): Why?

    Note that a string path with the separator at index[0] will have the
    separator stripped off. If you pass a list path, the separator is
    ignored, and is assumed to be part of each key glob. It will not be
    stripped.
    """
    if not segments.leaf(path):
        split_segments = path
    else:
        split_segments = path.lstrip(separator).split(separator)

        # TODO(moo): Unnecessary check, adds complexity
        # FIXME: This check was in the old internal library, but I can't see a way it could fail...
        for i, segment in enumerate(split_segments):
            if separator and (separator in segment):
                raise InvalidKeyName("{} at {}[{}] contains the separator '{}'".format(segment, split_segments, i, separator))

        # Attempt to convert integer segments into actual integers.
        final = []
        for segment in split_segments:
            try:
                final.append(int(segment))
            except ValueError:
                final.append(segment)

        split_segments = final

    return split_segments


def get(obj, glob, separator="/", default=_DEFAULT_SENTINEL):
    # type: (dict, str, str, Any) -> dict
    """
    Given an object which contains only one possible match for the given glob,
    return the value for the leaf matching the given glob.
    If the glob is not found and a default is provided,
    the default is returned.

    If more than one leaf matches the glob, ValueError is raised. If the glob is
    not found and a default is not provided, KeyError is raised.
    """
    # TODO(moo): Should be glob == separator?
    if glob == "/":
        return obj

    glob_list = _split_path(glob, separator)

    def walk(_, pair, _results):
        (path_to_curr, curr) = pair

        if segments.match(path_to_curr, glob_list):
            _results.append(curr)

        if len(_results) > 1:
            return False

    results = segments.fold(obj, walk, [])

    if len(results) == 0:
        if default is not _DEFAULT_SENTINEL:
            return default

        raise KeyError(glob)

    elif len(results) > 1:
        raise ValueError("dpath.get() globs must match only one leaf: {}".format(glob))

    return results[0]


def set(obj, glob, value, separator="/", afilter=None):
    '''
    Given a path glob, set all existing elements in the document
    to the given value. Returns the number of elements changed.
    '''
    globlist = __safe_path__(glob, separator)

    def walk(obj, pair, counter):
        (segments, found) = pair

        # Skip segments if they no longer exist in obj.
        if not dpath.segments.has(obj, segments):
            return

        matched = dpath.segments.match(segments, globlist)
        selected = afilter and dpath.segments.leaf(found) and afilter(found)

        if (matched and not afilter) or (matched and selected):
            dpath.segments.set(obj, segments, value, creator=None)
            counter[0] += 1

    [changed] = segments.foldm(obj, walk, [0])
    return changed