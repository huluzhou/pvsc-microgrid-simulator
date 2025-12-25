from domain.common.value_objects.base_value_object import ValueObject

class Position(ValueObject):
    def __init__(self, x: float, y: float, z: float = 0.0):
        self._x = x
        self._y = y
        self._z = z
    
    @property
    def x(self):
        return self._x
    
    @property
    def y(self):
        return self._y
    
    @property
    def z(self):
        return self._z
    
    def _get_eq_values(self):
        return [self._x, self._y, self._z]
