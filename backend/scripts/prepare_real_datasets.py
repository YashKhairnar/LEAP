"""Build LEAP runtime CSVs from downloaded authoritative source datasets."""

from __future__ import annotations

import csv
from pathlib import Path
import zipfile


SOURCE_ROOT = Path("/tmp/leap-real-datasets")
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "datasets"


def sentiment() -> None:
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(SOURCE_ROOT / "sentiment.zip") as archive:
        for source, filename in (
            ("amazon", "sentiment labelled sentences/amazon_cells_labelled.txt"),
            ("imdb", "sentiment labelled sentences/imdb_labelled.txt"),
            ("yelp", "sentiment labelled sentences/yelp_labelled.txt"),
        ):
            text = archive.read(filename).decode("utf-8")
            for line in text.splitlines():
                if "\t" not in line:
                    continue
                review, label = line.rsplit("\t", 1)
                rows.append({"review": review, "source": source, "sentiment": "positive" if label == "1" else "negative"})
    write_csv(OUTPUT_ROOT / "sentiment_labelled_sentences_uci_v2.csv", rows, ["review", "source", "sentiment"])


def housing() -> None:
    rows: list[dict[str, object]] = []
    with (SOURCE_ROOT / "AmesHousing.txt").open(newline="", encoding="utf-8") as file:
        for source in csv.DictReader(file, delimiter="\t"):
            full_baths = float(source["Full Bath"] or 0) + float(source["Bsmt Full Bath"] or 0)
            half_baths = float(source["Half Bath"] or 0) + float(source["Bsmt Half Bath"] or 0)
            rows.append({
                "bedrooms": int(source["Bedroom AbvGr"]),
                "bathrooms": full_baths + 0.5 * half_baths,
                "square_feet": int(source["Gr Liv Area"]),
                "age_years": max(0, int(source["Yr Sold"]) - int(source["Year Built"])),
                "price": int(source["SalePrice"]),
            })
    write_csv(OUTPUT_ROOT / "ames_housing_v2.csv", rows, ["bedrooms", "bathrooms", "square_feet", "age_years", "price"])


def optical_digits() -> None:
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(SOURCE_ROOT / "optical.zip") as archive:
        raw_rows: list[list[str]] = []
        for filename in ("optdigits.tra", "optdigits.tes"):
            raw_rows.extend(csv.reader(archive.read(filename).decode("ascii").splitlines()))
    pixel_columns = [f"pixel_{index}" for index in range(64)]
    for index, source in enumerate(raw_rows, start=1):
        row: dict[str, object] = {"image_id": f"digit_{index:05d}"}
        row.update({column: int(value) for column, value in zip(pixel_columns, source[:64])})
        row["label"] = int(source[64])
        rows.append(row)
    write_csv(OUTPUT_ROOT / "optical_digits_uci_v2.csv", rows, ["image_id", *pixel_columns, "label"])


def write_csv(path: Path, rows: list[dict[str, object]], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):,} rows to {path}")


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    sentiment()
    housing()
    optical_digits()
