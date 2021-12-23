from typing import Optional, NamedTuple
#
from clang import cindex
from .basetype import BaseType
from . import primitive_types
from .pointer_types import PointerType, ReferenceType, ArrayType, PointerToStructType


class TypedefType(BaseType):
    @property
    def result_typing(self) -> str:
        return self.name

    def param(self, name: str) -> str:
        return name

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef p{i} = {name}
'''

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}return {call}
'''


class StructType(BaseType):
    cursor: cindex.Cursor

    def __init__(self, name: str, cursor: cindex.Cursor, is_const=False):
        super().__init__(name, is_const)
        self.cursor = cursor

    @property
    def ctypes_type(self) -> str:
        return self.cursor.spelling

    @property
    def result_typing(self) -> str:
        return self.cursor.spelling

    def param(self, name: str) -> str:
        return name

    def cdef_param(self, indent: str, i: int, name: str) -> str:
        return f'''{indent}# {self}
{indent}cdef p{i} = {name}
'''

    def cdef_result(self, indent: str, call: str) -> str:
        return f'''{indent}# {self}
{indent}cdef void* value = <void*>{call}
{indent}return ctypes.c_void_p(value)
'''


class ImVector(BaseType):
    def __init__(self):
        super().__init__('ImVector')

    @property
    def ctypes_type(self) -> str:
        return 'ImVector'


IMVECTOR = ImVector()


class TypeWithCursor(NamedTuple):
    type: cindex.Type
    cursor: cindex.Cursor

    def __str__(self) -> str:
        return f'{self.type.spelling}'

    @property
    def spelling(self) -> str:
        return self.type.spelling

    def ref_from_children(self) -> Optional[cindex.Cursor]:
        try:
            return next(iter(
                c for c in self.cursor.get_children() if c.kind == cindex.CursorKind.TYPE_REF))
        except:
            pass

    @property
    def underlying(self) -> Optional['TypeWithCursor']:
        if self.type.kind != cindex.TypeKind.TYPEDEF:
            return

        ref = self.ref_from_children()
        assert ref.referenced.kind == cindex.CursorKind.TYPEDEF_DECL
        underlying_type = ref.referenced.underlying_typedef_type

        return TypeWithCursor(underlying_type, ref.referenced)


def is_primitive(base: BaseType) -> bool:
    match base:
        case (
            primitive_types.BoolType()
            | primitive_types.Int8Type()
            | primitive_types.Int16Type()
            | primitive_types.Int32Type()
            | primitive_types.Int64Type()
            | primitive_types.UInt8Type()
            | primitive_types.UInt16Type()
            | primitive_types.UInt32Type()
            | primitive_types.UInt64Type()
            | primitive_types.FloatType()
            | primitive_types.DoubleType()
        ):
            return True

    return False


def is_void_p(base: BaseType) -> bool:
    if not isinstance(base, pointer_types.PointerType):
        return False
    if not isinstance(base.base, primitive_types.VoidType):
        return False
    return True


def get(c: TypeWithCursor) -> BaseType:
    if c.spelling.startswith('ImVector<'):
        return IMVECTOR

    match c.type.kind:
        case cindex.TypeKind.VOID:
            return primitive_types.VoidType(c.type.is_const_qualified())

        case cindex.TypeKind.BOOL:
            return primitive_types.BoolType(c.type.is_const_qualified())

        case cindex.TypeKind.CHAR_S:
            return primitive_types.Int8Type(c.type.is_const_qualified())
        case cindex.TypeKind.SHORT:
            return primitive_types.Int16Type(c.type.is_const_qualified())
        case cindex.TypeKind.INT:
            return primitive_types.Int32Type(c.type.is_const_qualified())
        case cindex.TypeKind.LONGLONG:
            return primitive_types.Int64Type(c.type.is_const_qualified())

        case cindex.TypeKind.UCHAR:
            return primitive_types.UInt8Type(c.type.is_const_qualified())
        case cindex.TypeKind.USHORT:
            return primitive_types.UInt16Type(c.type.is_const_qualified())
        case cindex.TypeKind.UINT:
            return primitive_types.UInt32Type(c.type.is_const_qualified())
        case cindex.TypeKind.ULONGLONG:
            return primitive_types.UInt64Type(c.type.is_const_qualified())

        case cindex.TypeKind.FLOAT:
            return primitive_types.FloatType(c.type.is_const_qualified())
        case cindex.TypeKind.DOUBLE:
            return primitive_types.DoubleType(c.type.is_const_qualified())

        case cindex.TypeKind.POINTER:
            pointee = c.type.get_pointee()
            base = get(TypeWithCursor(pointee, c.cursor))
            match base:
                case StructType():
                    return PointerToStructType(base, is_const=c.type.is_const_qualified())
                case _:
                    if base.name.startswith('Im'):
                        pass
                    return PointerType(base, is_const=c.type.is_const_qualified())

        case cindex.TypeKind.LVALUEREFERENCE:
            pointee = c.type.get_pointee()
            base = get(TypeWithCursor(pointee, c.cursor))
            return ReferenceType(base, is_const=c.type.is_const_qualified())

        case cindex.TypeKind.CONSTANTARRAY:
            element = c.type.get_array_element_type()
            base = get(TypeWithCursor(element, c.cursor))
            return ArrayType(base, c.type.get_array_size(), is_const=c.type.is_const_qualified())

        case cindex.TypeKind.TYPEDEF:
            current = c
            while True:
                underlying = current.underlying
                if not underlying:
                    break
                current = underlying

            base = get(current)
            if is_primitive(base):
                return base
            elif is_void_p(base):
                return base
            else:
                return TypedefType(c.spelling, base, is_const=c.type.is_const_qualified())

        case cindex.TypeKind.RECORD:
            deref = c.ref_from_children()
            assert deref.referenced.kind == cindex.CursorKind.STRUCT_DECL
            return StructType(deref.referenced.spelling, deref.referenced, is_const=c.type.is_const_qualified())

        case cindex.TypeKind.FUNCTIONPROTO:
            return PointerType(primitive_types.VoidType(), is_const=c.type.is_const_qualified())

    raise RuntimeError(f"unknown type: {c.type.kind}")


def from_cursor(cursor_type: cindex.Type, cursor: cindex.Cursor) -> BaseType:
    return get(TypeWithCursor(cursor_type, cursor))
