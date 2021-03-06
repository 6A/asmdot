from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import Any, Callable, Dict, IO, no_type_check

from .ast import * # pylint: disable=W0614
from .options import Options


class Emitter(ABC, Options):
    """An AST to source code emitter."""
    functions : List[Function] = []
    declarations : List[Declaration] = []

    @property
    @abstractmethod
    def language(self) -> str:
        """Returns the identifier of the target language."""
        pass
    
    @property
    @abstractmethod
    def filename(self) -> str:
        """Returns the name of the generated file for the current architecture."""
        pass

    @property
    def test_filename(self) -> Optional[str]:
        """Returns the name of the generated file that tests the current architecture.
           If it is `None`, no tests will be generated."""
        return None


    @staticmethod
    def register(parser: ArgumentParser) -> None:
        """Registers the emitter, allowing it to add command-line parameters."""
        pass
    

    def get_type_name(self, ty: IrType) -> str:
        """Returns the name of the given type."""
        return ty.id
    
    def get_operator(self, op: Operator) -> str:
        """Returns the string representation of the given operator."""
        return op.op
    
    def get_builtin_name(self, builtin: Builtin) -> str:
        """Returns the name of the given builtin."""
        return builtin.name

    def get_function_name(self, function: Function) -> str:
        """Returns the name of the given function."""
        return function.initname


    def __init__(self, args: Namespace, arch: str) -> None:
        """Initializes the emitter for the given architecture. This constructor shall not be overriden."""
        self.arch = arch
        self.indent = Indent()
        self.initialize_options(args, arch)

        self.output : Optional[IO[str]] = None


    def write_header(self) -> None:
        """Emits the header of the file to a stream."""
        pass
    
    def write_footer(self) -> None:
        """Emits the footer of the file to a stream."""
        pass
    
    def write_separator(self) -> None:
        """Emits the separator between the declarations (written previously) and the functions (that are about to be written)."""
        pass


    @abstractmethod
    def write_expr(self, expr: Expression) -> None:
        """Emits an expression to a stream.
           Additionally, the `str` function will be modified to use this method for every `Expression` class."""
        raise NotImplementedError

    @abstractmethod
    def write_stmt(self, stmt: Statement) -> None:
        """Emits a statement to a stream.
           Additionally, the `str` function will be modified to use this method for every `Statement` class."""
        raise NotImplementedError
    
    @abstractmethod
    def write_function(self, fun: Function) -> None:
        """Emits a function to a stream."""
        raise NotImplementedError


    @abstractmethod
    def write_decl(self, decl: Declaration) -> None:
        """Emits a declaration to a stream."""
        raise NotImplementedError


    def write_test_header(self) -> None:
        """Emits the header of the test file."""
        pass

    def write_test_footer(self) -> None:
        """Emits the footer of the test file."""
        pass

    def write_test(self, test: TestCase) -> None:
        """Emits a test to a stream."""
        raise NotImplementedError


    def write(self, *args, indent: bool = False) -> None:
        """Writes the given arguments to the underlying stream."""
        assert self.output is not None
        
        out = self.output

        if indent:
            out.write(str(self.indent))

        for arg in args:
            if isinstance(arg, str):
                out.write(arg)
            elif any([ isinstance(arg, k) for k in expressionClasses ]):
                self.write_expr(arg)
            elif any([ isinstance(arg, k) for k in statementClasses ]):
                self.write_stmt(arg)
            else:
                out.write(str(arg))

    def writeline(self, *args, indent: bool = False) -> None:
        """Writes the given arguments to the underlying stream followed by a new-line
           character."""
        self.write(*args, indent=indent)
        self.output.write('\n')  # type: ignore
    
    def writei(self, *args) -> None:
        """Writes the given arguments to the underlying stream after inserting indentation."""
        self.write(*args, indent=True)
 
    def writelinei(self, *args) -> None:
        """Writes the given arguments to the underlying stream followed by a new-line
           character after inserting indentation."""
        self.writeline(*args, indent=True)

@no_type_check
def replace_pattern(patterns: Dict[str, str], string: str) -> str:
    """Replaces the string by the first template matching the corresponding key."""
    import re

    if not hasattr(replace_pattern, 'memoized'):
        replace_pattern.memoized = {}

    for pattern in patterns:
        if pattern in replace_pattern.memoized:
            pat = replace_pattern.memoized[pattern]
        else:
            pat = re.compile(f'^{pattern}$')
            replace_pattern.memoized[pattern] = pat

        newstring, n = pat.subn(patterns[pattern], string, count=1)

        if n == 1:
            return newstring
    
    return string

def join_any(sep: str, args: Sequence[Any]) -> str:
    """Joins multiple values together in a string using their `str` operator."""
    return sep.join([ str(arg) for arg in args ])


class Indent:
    """Helper class that manages the indentation when writing a string."""

    def __init__(self, indent_str: str = '  ', lvl: int = 0) -> None:
        self._str = indent_str
        self._lvl = lvl
    
    def __iadd__(self, i: int) -> 'Indent':
        """Adds the given level of indentation to the current one."""
        self._lvl += i

        return self
    
    def __isub__(self, i: int) -> 'Indent':
        """Removes the given level of indentation from the current one."""
        self._lvl -= i

        return self
    
    def __add__(self, i: int):
        """Returns a new indentation object with a greater indentation level."""
        return Indent(self._str, self._lvl + i)

    def __sub__(self, i: int):
        """Returns a new indentation object with a lower indentation level."""
        return Indent(self._str, self._lvl - i)
    
    def further(self, i: int = 1):
        """Returns an object that can be __enter__'d and __exit__'d with the `with` syntax.
           Inside the created block, the indentation level is increased by the given integer."""
        class FurtherWrapper:
            @classmethod
            def __enter__(s, *_):
                self._lvl += i
            @classmethod
            def __exit__(s, *_):
                self._lvl -= i

        return FurtherWrapper()

    def write(self, io: IO[str], *args) -> None:
        """Writes the indent to a text stream."""
        io.write(self._str * self._lvl)

        for arg in args:
            io.write(str(arg))

    def __call__(self, fmt: str, *args) -> str:
        """Returns the given string, indented and terminated with a line feed. Additionally, other arguments can be given in order to format the string."""
        return str(self) + (fmt.format(*args) if len(args) else fmt) + '\n'

    def __str__(self) -> str:
        """Returns the string representation of the indentation level, which is `'  ' * indent_level`."""
        return self._str * self._lvl

class UnsupportedArchitecture(Exception):
    arch: str

    def __str__(self):
        return f'Architecture {self.arch} is not supported.'

class UnsupportedDeclaration(Exception):
    decl: Declaration

    def __str__(self):
        return f'Declaration of type {self.decl.__class__.__name__} is not supported.'

class UnsupportedExpression(Exception):
    expr: Expression

    def __str__(self):
        return f'Expression of type {self.expr.__class__.__name__} is not supported.'

class UnsupportedStatement(Exception):
    stmt: Statement

    def __str__(self):
        return f'Statement of type {self.stmt.__class__.__name__} is not supported.'

class UnsupportedTestArgument(Exception):
    arg: TestCaseArgument

    def __str__(self):
        return f'Test case argument of type {self.arg.__class__.__name__} is not supported.'

class UnsupportedOption(Exception):
    option: str
    explain: str

    def __str__(self):
        return f'Option "{self.option}" is not supported: {self.explain}'
