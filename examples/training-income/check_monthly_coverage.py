"""Count JTPA participants with twelve monthly earnings records after service ends."""

import argparse
import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd


ARCHIVE_URL = "https://www.upjohn.org/sites/default/files/2019-02/jtpa_national_evaluation.zip"
MONTHS = [f"totern{month:02}" for month in range(33)]


def read_table(bundle, group, table, columns):
    member = f"Data/{group}/{group}_stata.zip"
    with ZipFile(BytesIO(bundle.read(member))) as tables:
        return pd.read_stata(
            BytesIO(tables.read(f"{table}.dta")),
            columns=columns,
            convert_categoricals=False,
        )


def summarize(archive):
    with ZipFile(archive) as bundle:
        baseline = read_table(bundle, "expbif", "expbif", ["recid", "ra_dt", "treatmt"])
        services = read_table(bundle, "replacement_files", "ppd_dat", ["recid", "end"])
        income = read_table(bundle, "replacement_files", "toterns", ["recid", *MONTHS])

    for table in (baseline, services, income):
        table["recid"] = pd.to_numeric(table["recid"])

    baseline["assigned"] = pd.to_datetime(baseline["ra_dt"], format="%y%m%d", errors="coerce")
    services["ended"] = pd.to_datetime(services["end"], format="%y%m%d", errors="coerce")
    last_service = services.groupby("recid", as_index=False)["ended"].max()
    panel = baseline.merge(last_service, on="recid", validate="one_to_one").merge(
        income, on="recid", validate="one_to_one"
    )
    assigned = panel["assigned"].dt
    ended = panel["ended"].dt
    end_month = (ended.year - assigned.year) * 12 + ended.month - assigned.month

    valid_months = pd.Series(0, index=panel.index)
    for month, column in enumerate(MONTHS):
        after_service = (month - end_month).between(1, 12)
        # The TOTERN codebook reserves values above 89,999 for special codes.
        valid_income = panel[column].between(0, 89999)
        valid_months += (after_service & valid_income).astype(int)

    complete = panel["ended"].ge(panel["assigned"]) & valid_months.eq(12)
    treated = pd.to_numeric(panel["treatmt"]).eq(1)
    print(f"Baseline assignment records: {len(baseline):,}")
    print(f"Participants with income records: {len(income):,}")
    print(f"Participants with service records: {len(last_service):,}")
    print(f"Participants present in all three sources: {len(panel):,}")
    print(f"Twelve complete calendar months of earnings after final service: {complete.sum():,}")
    print(f"Of these, assigned to treatment: {(complete & treated).sum():,}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, help="An existing JTPA distribution ZIP.")
    args = parser.parse_args()
    if args.archive is not None:
        summarize(args.archive)
        return

    with urlopen(ARCHIVE_URL, timeout=120) as source, tempfile.TemporaryFile() as archive:
        shutil.copyfileobj(source, archive)
        archive.seek(0)
        summarize(archive)


if __name__ == "__main__":
    main()
