import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, Tag
from loguru import logger

from .models.document import Document, DocumentId, DocumentRow


class DateParser:
    def __init__(self, *formats):
        self.formats = formats

    def parse_date(self, raw_date: str | None) -> datetime | None:
        if raw_date is None:
            return None

        for date_format in self.formats:
            try:
                return datetime.strptime(raw_date, date_format)
            except ValueError:
                pass
        return None


class DiscrepancyParserWarning(UserWarning):
    pass


_raw_date_and_country_regex = re.compile(
    r'Creation:\s?(?P<date>\d{1,2}[A-Z][a-z]{2}\d{2,4})\s?(?P<country>.*)'
)


class Parser:
    def __init__(self):
        pass

    @staticmethod
    def _parse_row_data(data: str):
        data = data.strip()
        if data.endswith('%'):
            return float(data[:-1]) / 100
        return float(data)

    @staticmethod
    def _parse_title(table: Tag) -> str | None:
        caption = table.caption
        if caption is not None:
            return caption.text
        return None

    @staticmethod
    def _parse_footer(table: Tag) -> str | None:
        tfoot = table.tfoot
        if tfoot is not None:
            return tfoot.tr.td.text
        return None

    @staticmethod
    def _parse_date(raw_date: str) -> datetime | None:
        date_parser = DateParser(
            '%d%b%Y',
            '%d%b%y',
            '%d%b'
        )
        return date_parser.parse_date(raw_date)

    @classmethod
    def parse_file(cls, file: Path) -> Document:
        with open(file, 'r') as f:
            soup = BeautifulSoup(f, 'html.parser')

        table = soup.table

        footer = cls._parse_footer(table)
        date_and_country_regex_match = _raw_date_and_country_regex.match(footer if footer else '')
        raw_date_of_creation, country_of_creation = (
            date_and_country_regex_match.groups() if date_and_country_regex_match else (
                None, None
            )
        )
        date_of_creation = cls._parse_date(raw_date_of_creation)

        return Document(
            document_id=DocumentId(table.attrs.get('id')),
            title=cls._parse_title(table),
            header=[th.text.strip() for th in table.thead.tr.find_all('th')[1:]],
            body=[
                DocumentRow(
                    header=row.td.text.strip(),
                    body=[cls._parse_row_data(td.text) for td in row.find_all('td')[1:]]
                )
                for row in table.tbody.find_all('tr')
            ],
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
                yield cls.parse_file(file)
            except Exception as e:
                logger.warning(f'Failed to parse {file}: {e}', DiscrepancyParserWarning)
