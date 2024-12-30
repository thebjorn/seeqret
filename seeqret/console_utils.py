from rich.console import Console
from rich.table import Table
import logging
logger = logging.getLogger(__name__)


def dochelp(cls) -> str:
    doc = cls.__doc__
    if not doc:
        return ""
    return doc.splitlines()[0].strip()


def as_table(headers: str | list, rows, numbered=True):
    """Output ``rows`` as a table with ``headers``.
    """
    if isinstance(headers, str):
        headers = [h.strip() for h in headers.split(',')]
    table = Table()
    if numbered:
        table.add_column('#', justify='right')
    for header in headers:
        table.add_column(header)
    for i, data in enumerate(rows):
        logger.debug('row %d: %s', i, data)
        row = getattr(data, 'row', data)
        if numbered:
            table.add_row(str(i+1), *row)
        else:
            table.add_row(*row)

    console = Console()
    console.print(table)
