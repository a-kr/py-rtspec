# coding: utf-8
import sys
import inspect
from types import MethodType
import ast
from ast import If, NodeTransformer, Assign, Name, Store, Module, Expression, Pass, Num
from copy import deepcopy


def unindent(code):
    """ Уменьшает до упора уровень отступа в строке, содержащей код на питоне.

        >>> unindent('        def f(x):\n            return Zz')
        'def f(x):\n    return Zz'

        Результат можно передавать в compile() или exec,
        не опасаясь ошибок Unexpected indent.
    """
    lines = code.split('\n')

    # выясним текущий уровень вложенности (по первой непустой строке)
    indent_len = 0
    for line in lines:
        stripped = line.strip()
        if stripped:
            indent_len = line.index(stripped[0])
            break
    if indent_len == 0:
        return code
    indent_pad = ' ' * indent_len

    new_lines = []
    # сдвинем все строки влево на найденную ширину отступа
    for line in lines:
        if line.strip():
            # строк с меньшим отступом быть не должно.
            # Если они есть - в переданном коде явный баг.
            assert line.startswith(indent_pad)
            line = line[indent_len:]
        new_lines.append(line)
    return u'\n'.join(new_lines)


def _specialize_ast(tree, _globals, _locals):
    """ Специализация AST путем анализа условий if'ов и отбрасывания ветвей,
        которые гарантированно не будут выполнены при заданных _globals и _locals.

        Предполагается, что все проверки в if не имеют побочных эффектов.
    """
    class Trn(NodeTransformer):
        def visit_If(self, node):
            self.generic_visit(node)

            cond = node.test

            # попробуем вычислить условие в нашем контексте
            wrap = Expression(body=cond)

            code = compile(wrap, '<string>', 'eval')
            try:
                r = eval(code, _globals, deepcopy(_locals))
            except Exception as e:
                # Исключение => нельзя понять, чему будет эквивалентно условие на практике
                branch_taken = 'unknown'
            else:
                # определяем значение условного выражения
                branch_taken = bool(r)

            if branch_taken is True:
                # Выполняется ветка "if". Значит ветку "else" можно отбросить.
                node.orelse = []
                # Условие заменяем на if 1, компилятор в байткод просто отбросит if
                # (if True он бы не отбросил, кстати, так как булевых констант нет в грамматике языка).
                # Увы, нельзя просто заменить узел If на его тело (список узлов), мы должны вернуть ровно один узел AST.
                node.test = Num(n=1, lineno=node.lineno, col_offset=node.col_offset)
                return node
            elif branch_taken is False:
                # Попадаем в ветвь "else".
                if not node.orelse:
                    # Ветвь else пуста. Возвращаем конструкцию if 1: pass
                    node.test = Num(n=1, lineno=node.lineno, col_offset=node.col_offset)
                    node.body = [Pass(lineno=node.lineno, col_offset=node.col_offset)]
                    return node
                # переставляем ветвь else в тело "if 1:"
                node.body = node.orelse
                node.orelse = []
                node.test = Num(n=1, lineno=node.lineno, col_offset=node.col_offset)
                return node
            else:
                # Не ясно, в какую ветвь мы попадем. Возвращаем исходный if без изменений
                return node

    return Trn().visit(tree)


def specialize_function(fun, _locals):
    """
        Специализация функции с заданным словарем локальных переменных _locals
    """
    tree = ast.parse(unindent(inspect.getsource(fun)))
    module = sys.modules[fun.__module__]
    _globals = module.__dict__
    new_tree = _specialize_ast(tree, _globals, _locals)
    #import meta; meta.asttools.python_source(new_tree)
    code = compile(new_tree, module.__file__, 'exec')
    namespace = {}
    exec code in namespace
    new_fun = namespace[fun.__name__]
    return new_fun


def specialize_instance_method(obj, methodname, _locals=None):
    """ Специализация метода объекта.
        Аналогично specialize_function(obj.methodname, {'self': obj}),
        но возвращает не функцию, а bound method.
    """
    method = getattr(obj, methodname)
    new_locals = {'self': obj}
    if _locals:
        new_locals.update(_locals)
    function = specialize_function(method, new_locals)
    new_method = MethodType(function, obj, obj.__class__)
    return new_method
