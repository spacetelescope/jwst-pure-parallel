# Define a domain specific language that helps users specify constraints.


def where_clause(constraint, only_table=None):
    '''Return a full WHERE clause (or empty string) for the filtered table.'''
    sql = sql_from_constraint(constraint, only_table=only_table)
    return f'WHERE {sql}' if sql else ''


def sql_from_constraint(constraint, only_table=None):
    '''Generate SQL for an parsed expression that constrains database columns.

    Args:
        constraint (_LogicalPredicate | _UnaryPredicate | _BinaryPredicate |
                    _TernaryPredicate): hierarchical tree of predicates
        only_table (str): optional, include only predicates for specified table
    '''
    if constraint is None:
        return ''
    if isinstance(constraint, _BinaryPredicate):
        if only_table and not constraint.colname.startswith(f'{only_table}.'):
            return ''
        if constraint.operator == 'IN':
            vstr = '(' + ', '.join(repr(v) for v in constraint.value) + ')'
        else:
            vstr = repr(constraint.value)
        return f'{constraint.colname} {constraint.operator} {vstr}'
    elif isinstance(constraint, _TernaryPredicate):
        if only_table and not constraint.colname.startswith(f'{only_table}.'):
            return ''
        return (
            f'{constraint.colname} BETWEEN '
            f'{repr(constraint.low)} AND '
            f'{repr(constraint.high)}'
        )
    elif isinstance(constraint, _UnaryPredicate):
        if only_table and not constraint.raw_sql.startswith(f'{only_table}.'):
            return ''
        return constraint.raw_sql
    elif isinstance(constraint, _LogicalPredicate):
        if constraint.op == 'NOT':
            sql = sql_from_constraint(constraint.args[0], only_table)
            return f'(NOT {sql})' if sql else ''
        left = sql_from_constraint(constraint.args[0], only_table)
        right = sql_from_constraint(constraint.args[1], only_table)
        if left and right:
            return f'({left} {constraint.op} {right})'
        return left or right
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
        self.parameters = colnames
        for colname in colnames:
            setattr(self, colname, DatabaseColumn(colname, tablename))

    def __str__(self):
        return '\n'.join([
            f'{self.tablename}.{p}' for p in self.parameters
            if p not in ['pure_subset']
        ])

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
        return _BinaryPredicate(self.name, '=', other)

    def __ne__(self, other):
        return _BinaryPredicate(self.name, '!=', other)

    def __lt__(self, other):
        return _BinaryPredicate(self.name, '<', other)

    def __le__(self, other):
        return _BinaryPredicate(self.name, '<=', other)

    def __gt__(self, other):
        return _BinaryPredicate(self.name, '>', other)

    def __ge__(self, other):
        return _BinaryPredicate(self.name, '>=', other)

    def isin(self, values):
        return _BinaryPredicate(self.name, 'IN', values)

    def between(self, low, high):
        return _TernaryPredicate(self.name, low, high)

    def is_null(self):
        return _UnaryPredicate(f'{self.name} IS NULL')

    def is_not_null(self):
        return _UnaryPredicate(f'{self.name} IS NOT NULL')


class _Expression:
    '''Base class for predicates that support logical composition.'''
    def __and__(self, other):
        return _LogicalPredicate('AND', self, other)

    def __or__(self, other):
        return _LogicalPredicate('OR', self, other)

    def __invert__(self):
        return _LogicalPredicate('NOT', self)


class _BinaryPredicate(_Expression):
    '''Represent a binary comparison predicate (e.g., col = value).'''
    def __init__(self, colname, operator, value):
        self.colname = colname
        self.operator = operator
        self.value = value


class _TernaryPredicate(_Expression):
    '''Represent a range predicate (e.g., col BETWEEN low AND high).'''
    def __init__(self, colname, low, high):
        self.colname = colname
        self.low = low
        self.high = high


class _UnaryPredicate(_Expression):
    '''Represents a unary SQL predicate (e.g., IS NULL, IS NOT NULL).'''
    def __init__(self, raw_sql):
        self.raw_sql = raw_sql


class _LogicalPredicate(_Expression):
    '''Represents a logical combination of predicates (AND, OR, NOT).'''
    def __init__(self, op, *args):
        self.op = op
        self.args = args
