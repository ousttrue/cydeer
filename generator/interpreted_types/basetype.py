from typing import Iterable, NamedTuple, Optional
import dataclasses


@dataclasses.dataclass
class BaseType:
    name: str
    base: Optional['BaseType'] = None
    is_const: bool = False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}'

    @property
    def ctypes_type(self) -> str:
        '''
        ctypes.Structure fields
        '''
        if not self.base:
            raise NotImplementedError()

        current = self
        while current.base:
            current = current.base
        return current.ctypes_type

    def ctypes_field(self, indent: str, name: str) -> str:
        return f'{indent}("{name}", {self.ctypes_type}), # {self}\n'

    def param(self, name: str, default_value: str) -> str:
        '''
        function param
        '''
        raise NotImplementedError()

    @property
    def result_typing(self) -> str:
        '''
        return
        '''
        raise NotImplementedError()

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        '''
        extract params
        '''
        raise NotImplementedError()

    def cdef_result(self, indent: str, call: str) -> str:
        '''
        extract result
        '''
        raise NotImplementedError()
