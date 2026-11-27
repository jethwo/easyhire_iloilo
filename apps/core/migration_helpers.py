"""Vendor-neutral helpers for the hand-written schema migrations.

A handful of early migrations add columns with raw SQL. They use
``SeparateDatabaseAndState`` because those columns already existed in an
older deployment's database, so Django only needed to be told about them —
but on a *fresh* database the raw SQL is what actually creates them.

That SQL was PostgreSQL-only (``ADD COLUMN IF NOT EXISTS``, and a
``DEFAULT`` on a ``TEXT`` column), which stopped the project from building
its schema on MySQL / MariaDB. These helpers issue the equivalent
statements for whichever backend is connected.

Treat what is here as frozen. Migrations are a historical record, so
changing how an existing helper behaves rewrites the past for every
database that has already run it. If different behaviour is needed, add a
new function rather than editing one of these.
"""


def _information_schema_predicate(connection):
    """Return the SQL that scopes information_schema to the live database.

    ``information_schema.columns`` exists on PostgreSQL, MySQL and MariaDB
    alike, so one query shape covers every backend — only the "current
    database" function differs. Scoping matters: without it, a same-named
    table in another schema would give a false positive and we would skip
    a column that really is missing.
    """
    if connection.vendor == 'mysql':
        return 'table_schema = DATABASE()'
    return 'table_schema = CURRENT_SCHEMA()'


def column_exists(schema_editor, table, column):
    """True when ``table.column`` is already present in the database."""
    connection = schema_editor.connection
    sql = (
        'SELECT 1 FROM information_schema.columns '
        f'WHERE {_information_schema_predicate(connection)} '
        'AND table_name = %s AND column_name = %s'
    )
    with connection.cursor() as cursor:
        cursor.execute(sql, [table, column])
        return cursor.fetchone() is not None


def add_column(schema_editor, table, column, column_type, default=''):
    """Add ``column`` to ``table`` when missing, then backfill NULL rows.

    ``column_type`` is SQL both backends understand as-is (``VARCHAR(n)``,
    ``TEXT``). ``default`` is the value NULL rows are backfilled with, and
    is also installed as the column's SQL default where the backend allows
    it. Pass ``default=None`` for a plain nullable column with no backfill.

    No-ops when the column is already there, which keeps the migration
    replayable against the legacy databases these operations were written
    for in the first place.
    """
    connection = schema_editor.connection
    if column_exists(schema_editor, table, column):
        return

    quote = schema_editor.quote_name
    qualified = f'{quote(table)}.{quote(column)}'  # noqa: F841 - readability in tracebacks

    with connection.cursor() as cursor:
        cursor.execute(
            f'ALTER TABLE {quote(table)} ADD COLUMN {quote(column)} {column_type}'
        )
        if default is None:
            return

        cursor.execute(
            f'UPDATE {quote(table)} SET {quote(column)} = %s '
            f'WHERE {quote(column)} IS NULL',
            [default],
        )

        # MySQL rejects a DEFAULT on TEXT/BLOB columns outright ("BLOB,
        # TEXT, GEOMETRY or JSON column can't have a default value").
        # PostgreSQL and MariaDB both allow it. Django never relies on a
        # database-level default — it always sends an explicit value — so
        # skipping it on MySQL costs nothing.
        is_text = 'TEXT' in column_type.upper()
        if connection.vendor == 'mysql' and is_text:
            return

        # DDL cannot take bound parameters, so the literal is inlined.
        # Every caller passes a constant from the migration itself, and the
        # quote-doubling keeps that safe regardless.
        literal = "'" + str(default).replace("'", "''") + "'"
        cursor.execute(
            f'ALTER TABLE {quote(table)} '
            f'ALTER COLUMN {quote(column)} SET DEFAULT {literal}'
        )
