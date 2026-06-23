"""
All usefull function
"""
# To update style.
# pylint: disable=bad-indentation, invalid-name

def list_differ(d1:list, d2:list):
    """
    recursiv comparaison function for list
    """
    if len(d1) != len(d2):
        return True
    for a, b in zip(d1, d2):
        if obj_differ(a, b):
            return True
    return False

def dict_differ(d1:dict, d2:dict):
    """
    recursiv comparaison function for dict
    """
    if set(d1.keys()) != set(d2.keys()):
        return True
    for key in d1:
        if obj_differ(d1[key], d2[key]):
            return True
    return False

def obj_differ(d1, d2):
    """
    recursiv comparaison function for obj of nearly anything
    Return True if d1 and d2 differ, False if they are equal (recursive).
    """
    differ = False
    if type(d1) is not type(d2):
        differ = True
    elif isinstance(d1, dict):
        differ = dict_differ(d1, d2)
    elif isinstance(d1, list):
        differ = list_differ(d1, d2)
    elif isinstance(d1, set):
        # Compare sorted lists (order‑independent)
        differ = obj_differ(sorted(d1, key=str), sorted(d2, key=str))
    else:
        differ = d1 != d2
    return differ
