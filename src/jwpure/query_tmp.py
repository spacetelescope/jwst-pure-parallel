# Define a domain specific language that simplifies constraint specification.


def where_clause(constraints):
    sql = generate_sql(constraints)
    print(sql)
    exit()
 
    return f'WHERE {sql}' if sql else ''


def generate_sql(constraint):
    '''Generate SQL for an parsed expression that constrains database columns.

    Args:
        constraint (_LogicalOperator | _UnaryOperator | _BinaryOperator |
                    _TernaryOperator): hierarchical tree of operators
    '''
    if constraint is None:
        return ''
    if isinstance(constraint, _BinaryOperator):
        if constraint.operator == 'IN':
            vstr = '(' + ', '.join(repr(v) for v in constraint.value) + ')'
        else:
            vstr = repr(constraint.value)
        return f'{constraint.colname} {constraint.operator} {vstr}'
    elif isinstance(constraint, _TernaryOperator):
        return (
            f'{constraint.colname} BETWEEN '
            f'{repr(constraint.low)} AND '
            f'{repr(constraint.high)}'
        )
    elif isinstance(constraint, _UnaryOperator):
        return constraint.raw_sql
    elif isinstance(constraint, _LogicalOperator):
        if constraint.op == 'NOT':
            return f'(NOT {generate_sql(constraint.args[0])})'
        return (
            f'({generate_sql(constraint.args[0])} '
            f'{constraint.op} '
            f'{generate_sql(constraint.args[1])})'
        )
    else:
        raise TypeError(f'Unknown constraint type: {type(constraint)}')
    

class DatabaseTable:
    '''Represent a database table. Contain DatabaseColumn objects.

    Args:
        tablename (str): name of table that contains the specified columns
        *colnames (str): tuple of column names in the specified table
    '''
    def __init__(self, tablename, *colnames):
        self.tablename = tablename
        for colname in colnames:
            setattr(self, colname, DatabaseColumn(colname, tablename))


class DatabaseColumn:
    '''Represent a column in a database table. Support expression operators.

    Args:
        tablename (str): name of table that contains the specified column
        colname (str): name of column in the specified table
    '''
    def __init__(self, colname, tablename=''):
        self.tablename = tablename
        self.colname = colname
        if tablename:
            self.name = f'{tablename}.{colname}'
        else:
            self.name = colname

    def __eq__(self, other):
        return _BinaryOperator(self.name, '=', other)

    def __ne__(self, other):
        return _BinaryOperator(self.name, '!=', other)

    def __lt__(self, other):
        return _BinaryOperator(self.name, '<', other)

    def __le__(self, other):
        return _BinaryOperator(self.name, '<=', other)

    def __gt__(self, other):
        return _BinaryOperator(self.name, '>', other)

    def __ge__(self, other):
        return _BinaryOperator(self.name, '>=', other)

    def isin(self, values):
        return _BinaryOperator(self.name, 'IN', values)

    def between(self, low, high):
        return _TernaryOperator(self.name, low, high)

    def is_null(self):
        return _UnaryOperator(f'{self.name} IS NULL')

    def is_not_null(self):
        return _UnaryOperator(f'{self.name} IS NOT NULL')


class _LogicalOperator:
    '''Handle AND, OR, and NOT operators in expressions.'''
    def __init__(self, op, *args):
        self.op = op
        self.args = args

    def __and__(self, other):
        return _LogicalOperator('AND', self, other)

    def __or__(self, other):
        return _LogicalOperator('OR', self, other)

    def __invert__(self):
        return _LogicalOperator('NOT', self)


class _UnaryOperator:
    def __init__(self, raw_sql):
        self.raw_sql = raw_sql

    def __and__(self, other):
        return _LogicalOperator('AND', self, other)

    def __or__(self, other):
        return _LogicalOperator('OR', self, other)

    def __invert__(self):
        return _LogicalOperator('NOT', self)


class _BinaryOperator:
    def __init__(self, colname, operator, value):
        self.colname = colname
        self.operator = operator
        self.value = value

    def __and__(self, other):
        return _LogicalOperator('AND', self, other)

    def __or__(self, other):
        return _LogicalOperator('OR', self, other)

    def __invert__(self):
        return _LogicalOperator('NOT', self)


class _TernaryOperator:
    def __init__(self, colname, low, high):
        self.colname = colname
        self.low = low
        self.high = high

    def __and__(self, other):
        return _LogicalOperator('AND', self, other)

    def __or__(self, other):
        return _LogicalOperator('OR', self, other)

    def __invert__(self):
        return _LogicalOperator('NOT', self)
