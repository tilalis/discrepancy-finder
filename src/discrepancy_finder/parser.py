import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from loguru import logger

from .models.document import Document, DocumentRow


class DateParser:
    def __init__(self, *formats):
        self.formats = formats

    def parse_date(self, raw_date: str):
        for date_format in self.formats:
            try:
                return datetime.strptime(raw_date, date_format)
            except ValueError:
                pass
        return None


class Parser:
    def __init__(self):
        pass

    @staticmethod
    def parse_document(file: Path) -> Document:
        with open(file, 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')

        table = soup.table
        table_id = table.attrs.get('id')

        if (caption := table.caption) is not None:
            title = caption.text
        else:
            title = None

        header = [th.text.strip() for th in table.thead.tr.find_all('th')[1:]]

        body = [
            DocumentRow(
                header=row.td.text.strip(),
                body=[td.text.strip() for td in row.find_all('td')[1:]]
            )
            for row in table.tbody.find_all('tr')
        ]

        if (tfoot := table.tfoot) is not None:
            footer = tfoot.tr.td.text
            match_result = re.match(
                r'Creation:\s?(?P<date>\d{1,2}[A-Z][a-z]{2}\d{2,4})\s?(?P<country>.*)',
                footer
            )
        else:
            match_result = None

        if match_result is not None:
            raw_date = match_result.group('date')
            country_of_creation = match_result.group('country')
            date_of_creation = DateParser(
                '%d%b%Y',
                '%d%b%y',
                '%d%b'
            ).parse_date(raw_date)

        else:
            country_of_creation, date_of_creation, footer = None, None, None

        return Document(
            document_id=table_id,
            title=title,
            header=header,
            body=body,
            footer=footer,
            country_of_creation=country_of_creation,
            date_of_creation=date_of_creation
        )

    @classmethod
    def parse(cls, directory: Path) -> Iterable[Document]:
        # assuming that the directory does not contain any subdirectories
        for file in directory.glob('*.html'):
            if not file.is_file():
                continue

            try:
                yield cls.parse_document(file)
            except Exception as e:
                logger.warn(f'Failed to parse {file}: {e}', DiscrepancyParserWarning)
