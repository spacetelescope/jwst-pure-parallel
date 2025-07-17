from importlib import resources
from numpy import issubdtype
from sqlite3 import connect

from astropy.io.ascii import read as ascii_read
from astropy.table import Table

from .query import DatabaseTable, where_clause

DEFAULT_SLOT_DATA_PATH = resources.files('jwpure.data') / 'pure_slots.csv'


class Scenario:
    '''Assess a JWST pure parallel observing scenario.

    Creates a database in memory. Loads slot data. Facilitates queries.'''
    def __init__(self, slot_data_path=DEFAULT_SLOT_DATA_PATH):
        self.slot_data_path = slot_data_path
        self.db = connect(':memory:')
        self.cursor = self.db.cursor()
        slotdata = ascii_read(slot_data_path)
        slotdata['visit_id'] = [f'{v:011}' for v in slotdata['visit_id']]
        colnames = ['pure_subset', 'pure_visit', 'pure_config', 'pure_slot']
        for colname in colnames:
            slotdata[colname] = 0
        self.create_database_table('slot', slotdata)
        self.where_joint = 'No query'
        self.pure_subset = 0

    @staticmethod
    def constraint_parameters():
        '''Return objects representing parameters used to express constraints.

        Returns:
            slot (jwpure.query.DatabaseTable): slot table params
            config (jwpure.query.DatabaseTable): config table params
            visit (jwpure.query.DatabaseTable): visit table params
        '''
        slot = DatabaseTable(
            'slot', 'inst', 'slotdur', 'ra', 'dec', 'elat', 'glat',
            'pure_subset'
        )
        config = DatabaseTable('config', 'nslot', 'configdur')
        visit = DatabaseTable('visit', 'nconfig')
        return slot, config, visit


    def allocate_slots(
            self, constraint, maxslot=999, maxconfig=999, trace_id=None):
        '''Allocate pure parallel slots that obey the specifed constraints.

        Algorithm:
            1. Apply constraints on slot table to create config table.
            2. Apply constraints on config table to create visit table.
            3. Apply constraints on visit table to create final list of slots.

        Args:
            constraint (expression): expression that constrains slots
            maxslot (int, default=999): max slots to keep in a config
            maxconfig (int, default=999): max configs to keep in a visit
            trace_id (str, default=None): identifier for visit to trace
        '''
        # Increment subset number.
        self.pure_subset += 1
        self._trace(trace_id, 'slot', f'Subset {self.pure_subset}, slot table')

        # Identify "available" slots (not part of a previous subset).
        slot, config, visit = self.constraint_parameters()
        available = (slot.pure_subset == 0)

        # Create new `config` table. Apply slot constraint to available slots.
        where_slot = where_clause(constraint & available, only_table='slot')
        self.cursor.execute('DROP TABLE IF EXISTS config')
        self.cursor.execute(f'''
            CREATE TABLE config AS
            SELECT visit_id, config_id, COUNT(*) nslot, SUM(slotdur) configdur
            FROM slot
            {where_slot}
            GROUP BY visit_id, config_id
        ''')
        self._trace(
           trace_id, 'config', f'Subset {self.pure_subset}, config table'
        )

        # Make new `visit` table. Apply config constraint to selected slots.
        where_config = where_clause(constraint, only_table='config')
        self.cursor.execute('DROP TABLE IF EXISTS visit')
        self.cursor.execute(f'''
            CREATE TABLE visit AS
            SELECT visit_id, COUNT(*) nconfig
            FROM config
            {where_config}
            GROUP BY visit_id
        ''')
        self._trace(
            trace_id, 'visit', f'Subset {self.pure_subset}, visit table'
        )

        # Make new `subset` table. Jointly apply all constraints.
        where_joint = where_clause(constraint)
        self.where_joint = where_joint
        self.cursor.execute('DROP TABLE IF EXISTS subset')
        self.cursor.execute(f'''
            CREATE TABLE subset AS
            SELECT visit.visit_id, config.config_id, slot.slot_id
            FROM slot
            JOIN config ON config.config_id = slot.config_id
            JOIN visit ON visit.visit_id = slot.visit_id
            {where_joint}
        ''')
        self._trace(
            trace_id, 'subset', f'Subset {self.pure_subset}, subset table'
        )

        # Assign sequence numbers to visits, configs, and slots.
        self.cursor.execute('''
            SELECT visit_id, config_id, slot_id
            FROM subset
            ORDER BY slot_id
        ''')
        rows = self.cursor.fetchall()
        sequence_numbers = self._sequence_numbers(rows, maxslot, maxconfig)
        self.cursor.execute('DROP TABLE IF EXISTS sequence_numbers')
        self.cursor.execute('''
            CREATE TABLE sequence_numbers (
                visit_id TEXT, config_id TEXT, slot_id TEXT,
                pure_subset INTEGER, pure_visit INTEGER,
                pure_config INTEGER, pure_slot INTEGER)
        ''')
        self.cursor.executemany('''
            INSERT INTO sequence_numbers (
                visit_id, config_id, slot_id,
                pure_subset, pure_visit, pure_config, pure_slot)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sequence_numbers)
        self._trace(
            trace_id, 'sequence_numbers',
            f'Subset {self.pure_subset}, subset table'
        )

        # Update `slot.pure_subset` to indicate slots used in this subset.
        self.cursor.execute(f'''
            UPDATE slot
            SET pure_subset = (
                    SELECT pure_subset FROM sequence_numbers sn
                    WHERE sn.slot_id = slot.slot_id
                ),
                pure_visit = (
                    SELECT pure_visit FROM sequence_numbers sn
                    WHERE sn.slot_id = slot.slot_id
                ),
                pure_config = (
                    SELECT pure_config FROM sequence_numbers sn
                    WHERE sn.slot_id = slot.slot_id
                ),
                pure_slot = (
                    SELECT pure_slot FROM sequence_numbers sn
                    WHERE sn.slot_id = slot.slot_id
                )
            WHERE slot_id IN (SELECT slot_id FROM subset)
        ''')

    def summarize(self, path=None, table='slot'):
        '''Summarize slot information in a table.'''
        query = (
            f'SELECT'
            f'  cycle, '
            f'  pure_subset, '
            f'  COUNT(DISTINCT slot_id) nslot, '
            f'  COUNT(DISTINCT config_id) nconfig, '
            f'  COUNT(DISTINCT visit_id) nvisit, '
            f'  SUM(slotdur) / 3600 hours '
            f'FROM {table} '
            f'GROUP BY cycle, pure_subset '
            f'ORDER BY cycle, pure_subset '
        )
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        colnames = [desc[0] for desc in self.cursor.description]
        table = Table(rows=rows, names=colnames)
        if path:
            with open(path, 'w') as fobj:
                for line in table.pformat(max_width=None):
                    fobj.write(f'{line}\n')
                fobj.write(f'{self.where_joint}\n')
            print(f'wrote {path}')
        table.pprint()
        return table

    def save(self, path):
        '''Save information about pure parallel slots to a file.'''
        query = 'SELECT * FROM slot WHERE pure_subset > 0 ORDER BY slot_id'
        self.raw_query(query, path=path)

    def raw_query(self, query, path=None):
        '''Return result of an arbitrary query. Write to file, if specified.'''
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        if not rows:
            return
        colnames = [desc[0] for desc in self.cursor.description]
        table = Table(rows=rows, names=colnames)
        if path:
            table.write(path, format='ascii.csv', overwrite=True)
            print(f'wrote {path}')
        return table

    def create_database_table(self, tablename, table):
        '''Create and load database table with contents of an astropy table.

        Args:
            tablename (str): Name of database table to create.
            table (astropy.table.Table): Column names, types, and values.
        '''
        coldefs = []
        for colname, column in table.columns.items():
            coldefs.append(f'{colname} {sqltype(column.dtype)}')
        create_statement = f"CREATE TABLE {tablename} ({', '.join(coldefs)});"
        self.cursor.execute(create_statement)
        placeholders = ', '.join(['?'] * len(coldefs))
        insert_statement = f"INSERT INTO {tablename} VALUES ({placeholders})"
        self.cursor.executemany(insert_statement, table.as_array().tolist())

    def _trace(self, trace_id, table, title):
        '''Print rows in the specified table for the specified visit.'''
        if not trace_id:
            return
        query = f'SELECT * FROM {table} WHERE visit_id = "{trace_id}"'
        table = self.raw_query(query)
        print(f'\n{title}')
        print(table)

    def _sequence_numbers(self, rows, maxslot=999, maxconfig=999):
        '''Assign sequence numbers to visits, configs, and slots.

        Sequence numbers begin at 1 and increment.
        Config sequence number resets to 1 with each new visit. 
        Slot sequence number resets to 1 with each new config.

        Args:
            rows (list of tuple): visit_id, config_id, and slot_id for slot
            maxslot (int, default=999): max slots to keep in a config
            maxconfig (int, default=999): max configs to keep in a visit
        '''
        sequence_numbers = []
        prev_visit_id = None
        prev_config_id = None
        pure_visit = 0
        pure_config = 0
        pure_slot = 0
        for visit_id, config_id, slot_id in rows:
            if visit_id != prev_visit_id:
                pure_visit += 1
                pure_config = 1
                pure_slot = 1
            elif config_id != prev_config_id:
                pure_config += 1
                pure_slot = 1
            else:
                pure_slot += 1
            if pure_config > maxconfig or pure_slot > maxslot:
                sequence_numbers.append(
                    (visit_id, config_id, slot_id, 0, 0, 0, 0)
                )
            else:
                sequence_numbers.append(
                    (visit_id, config_id, slot_id,
                    self.pure_subset, pure_visit, pure_config, pure_slot)
                )
            prev_visit_id = visit_id
            prev_config_id = config_id
        return sequence_numbers


def sqltype(dtype):
    '''Return sqlite3 type corresponding to the specified astropy dtype.

    Args:
         dtype (numpy.dtype): data type (subclasses of int, float, str)
    '''
    if issubdtype(dtype, int):
        return 'INTEGER'
    elif issubdtype(dtype, float):
        return 'REAL'
    elif issubdtype(dtype, str):
        return 'TEXT'
    else:
        raise ValueError(f'No logic to handle dtype {dtype}')
