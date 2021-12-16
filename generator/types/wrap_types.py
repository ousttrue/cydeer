from typing import Optional, Callable, NamedTuple, Union, Tuple
import re
from .basetype import BaseType
from .const import const


class WrapFlags(NamedTuple):
    name: str
    fields: bool = False
    methods: Union[bool, Tuple[str, ...]] = False
    custom_methods: Tuple[str, ...] = ()


WRAP_TYPES = [
    WrapFlags('ImVec2', fields=True, custom_methods=(
        '''def __iter__(self):
    yield self.x
    yield self.y
''',
    )),
    WrapFlags('ImVec4', fields=True, custom_methods=(
        '''def __iter__(self):
    yield self.x
    yield self.y
    yield self.w
    yield self.h
''',
    )),
    WrapFlags('ImFont'),
    WrapFlags('ImFontConfig', fields=True),
    WrapFlags('ImFontAtlasCustomRect', fields=True),
    WrapFlags('ImFontAtlas', fields=True, methods=True),
    WrapFlags('ImGuiIO', fields=True),
    WrapFlags('ImGuiContext'),
    WrapFlags('ImDrawCmd', fields=True),
    WrapFlags('ImDrawData', fields=True),
    WrapFlags('ImDrawListSplitter', fields=True),
    WrapFlags('ImDrawCmdHeader', fields=True),
    WrapFlags('ImDrawList', fields=True),
    WrapFlags('ImGuiStyle'),
    WrapFlags('ImGuiViewport', fields=True),
    WrapFlags('ImGuiWindowClass'),
]


class WrapPointerType(BaseType):
    '''
    by pointer
    '''

    def __init__(self, name: str):
        super().__init__(name + ' *')
        self._name = name

    def match(self, spelling: str) -> bool:
        m = re.match(r'^(?:const )?(\w+)(?: \*)?$', spelling)
        if m and m.group(1) == self._name:
            return True
        return False

    @property
    def py_type(self) -> str:
        return self._name

    @property
    def field_ctypes_type(self) -> str:
        return f'ctypes.c_void_p'

    def to_c(self, name: str, is_const: bool) -> str:
        return f'<{const(is_const)}cpp_imgui.{self._name}*><uintptr_t>ctypes.addressof({name}) if {name} else NULL'

    def to_cdef(self, is_const: bool) -> str:
        return f'cdef {const(is_const)}cpp_imgui.{self._name} *'

    def to_py(self, name: str) -> str:
        return f'ctypes.cast(ctypes.c_void_p(<uintptr_t>{name}), ctypes.POINTER({self._name}))[0]'


class WrapReferenceType(BaseType):
    '''
    by reference
    '''

    def __init__(self, name: str):
        super().__init__(name + ' &')
        self._name = name

    def match(self, spelling: str) -> bool:
        m = re.match(r'^(?:const )?(\w+)(?: &)?$', spelling)
        if m and m.group(1) == self._name:
            return True
        return False

    @property
    def py_type(self) -> str:
        return self._name

    @property
    def field_ctypes_type(self) -> str:
        return self._name

    def to_c(self, name: str, is_const: bool) -> str:
        return f'<{const(is_const)}cpp_imgui.{self._name}*><uintptr_t>ctypes.addressof({name}) if {name} else NULL'

    def to_cdef(self, is_const: bool) -> str:
        return f'cdef {const(is_const)}cpp_imgui.{self._name} *'

    def to_py(self, name: str) -> str:
        return f'ctypes.cast(ctypes.c_void_p(<uintptr_t>{name}), ctypes.POINTER({self._name}))[0]'


class WrapType(BaseType):
    '''
    by value
    '''

    def __init__(self, name: str,
                 to_c: Optional[Callable[[str, bool], str]] = None,
                 to_py: Optional[Callable[[str], str]] = None):
        super().__init__(name)
        self._to_c = to_c
        self._to_py = to_py

    def to_c(self, name: str, is_const: bool) -> str:
        if self._to_c:
            return self._to_c(name, is_const)
        else:
            return name

    def to_cdef(self, is_const: bool) -> str:
        return f'cdef cpp_imgui.{self.c_type}'

    def to_py(self, name: str) -> str:
        if self._to_py:
            return self._to_py(name)
        else:
            return name


class ImVec2WrapType(WrapType):
    def __init__(self):
        super().__init__('ImVec2')

    @property
    def py_type(self) -> str:
        return 'Any'

    @property
    def field_ctypes_type(self) -> str:
        return f'{self.c_type}'

    def to_c(self, name: str, is_const: bool) -> str:
        return f'cpp_imgui.ImVec2({name}[0], {name}[1]) if isinstance({name}, tuple) else cpp_imgui.ImVec2({name}.x, {name}.y)'

    def to_py(self, name: str) -> str:
        '''
        return as tuple
        '''
        return f'({name}.x, {name}.y)'


class ImVec4WrapType(WrapType):
    def __init__(self):
        super().__init__('ImVec4')

    @property
    def py_type(self) -> str:
        return 'Any'

    @property
    def field_ctypes_type(self) -> str:
        return f'{self.c_type}'

    def to_c(self, name: str, is_const: bool) -> str:
        return f'cpp_imgui.ImVec4({name}[0], {name}[1], {name}[2], {name}[3]) if isinstance({name}, tuple) else cpp_imgui.ImVec4({name}.x, {name}.y, {name}.z, {name}.w)'

    def to_py(self, name: str) -> str:
        '''
        return as tuple
        '''
        return f'({name}.x, {name}.y, {name}.z, {name}.w)'
