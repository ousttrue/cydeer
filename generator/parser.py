from typing import NamedTuple, Tuple, List, Union
import io
import pathlib
import logging
from clang import cindex
from . typedef import TypedefDecl
from . struct import StructDecl
from .enum import EnumDecl
logger = logging.getLogger(__name__)


class Parser:
    def __init__(self, headers: List[pathlib.Path]) -> None:
        sio = io.StringIO()
        for header in headers:
            sio.write(f'#include "{header.name}"\n')
        import pycindex

        self.headers = headers

        include_dirs = [str(header.parent)for header in headers]
        unsaved = pycindex.Unsaved('tmp.h', sio.getvalue())
        self.tu = pycindex.get_tu(
            'tmp.h', include_dirs=include_dirs, unsaved=[unsaved], flags=['-DNOMINMAX'])
        self.functions: List[Tuple[cindex.Cursor, ...]] = []
        self.enums: List[EnumDecl] = []
        self.typedef_struct_list: List[Union[TypedefDecl, StructDecl]] = []

        self.used = []
        self.skip = []

    def callback(self, *cursor_path: cindex.Cursor) -> bool:
        cursor = cursor_path[-1]
        location: cindex.SourceLocation = cursor.location
        if not location:
            return False
        if not location.file:
            return False

        if pathlib.Path(location.file.name) in self.headers:
            if location.file.name not in self.used:
                logger.debug(f'header: {location.file.name}')
                self.used.append(location.file.name)
            match cursor.kind:
                case cindex.CursorKind.NAMESPACE:
                    # enter namespace
                    logger.info(f'namespace: {cursor.spelling}')
                    return True
                case (
                    cindex.CursorKind.MACRO_DEFINITION
                    | cindex.CursorKind.MACRO_INSTANTIATION
                    | cindex.CursorKind.INCLUSION_DIRECTIVE
                    | cindex.CursorKind.FUNCTION_TEMPLATE
                ):
                    pass

                case cindex.CursorKind.FUNCTION_DECL:
                    if(cursor.spelling.startswith('operator ')):
                        pass
                    else:
                        self.functions.append(cursor_path)
                case cindex.CursorKind.ENUM_DECL:
                    self.enums.append(EnumDecl(cursor_path))
                case cindex.CursorKind.TYPEDEF_DECL:
                    self.typedef_struct_list.append(TypedefDecl(cursor_path))
                case cindex.CursorKind.STRUCT_DECL:
                    self.typedef_struct_list.append(StructDecl(cursor_path))
                case cindex.CursorKind.CLASS_TEMPLATE:
                    self.typedef_struct_list.append(StructDecl(cursor_path))
                case cindex.CursorKind.CLASS_DECL:
                    self.typedef_struct_list.append(StructDecl(cursor_path))
                case _:
                    logger.debug(cursor.kind)
        else:
            if not location.file.name.startswith('C:'):
                if location.file.name not in self.skip:
                    logger.debug(f'unknown header: {location.file.name}')
                    self.skip.append(location.file.name)

        return False

    def traverse(self):
        import pycindex
        pycindex.traverse(self.tu, self.callback)
