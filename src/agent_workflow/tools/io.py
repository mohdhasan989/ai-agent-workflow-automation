import csv
from pathlib import Path


def read_csv(path, encoding: str = "utf-8-sig", delimiter: str = ",") -> list:
    with Path(path).open("r", encoding=encoding, newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))