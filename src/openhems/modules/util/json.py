"""
Utility to overpass that json.dumps do not use __json__() by default.
"""

# import JSONEncoder

# pylint: disable=invalid-name, bad-indentation # Until full migration to snake_case

# Patch for jsonEncoder
# pylint: disable=unused-argument
def wrapped_default(self, obj):
    """
    Patch for jsonEncoder
    """
    return getattr(obj.__class__, "__json__", wrapped_default.default)(obj) #pylint: disable=no-member

# wrapped_default.default = JSONEncoder().default
# # apply the patch
# JSONEncoder.original_default = JSONEncoder.default
# JSONEncoder.default = wrapped_default

def json_default(obj):
    """
    Override JSON serializer for objects to use __json__ method.
    """
    if hasattr(obj, "__json__"):
        return obj.__json__()
    # Optionnel : gérer d'autres types non sérialisables
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
