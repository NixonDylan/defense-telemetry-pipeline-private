from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

DATASETS_XML_PATH = Path("datasets.xml")
INIT_SQL_PATH = Path("init.sql")


def _get_dataset_global_attributes(dataset: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    add_attrs = dataset.find("addAttributes")
    if add_attrs is None:
        return attrs

    for att in add_attrs.findall("att"):
        name = att.attrib.get("name")
        if name and att.text is not None:
            attrs[name] = att.text.strip()
    return attrs


def _get_variable_units(var: ET.Element) -> str | None:
    add_attrs = var.find("addAttributes")
    if add_attrs is None:
        return None

    for att in add_attrs.findall("att"):
        if att.attrib.get("name") == "units" and att.text is not None:
            return att.text.strip()
    return None


def _strip_sql_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


@pytest.fixture(scope="module")
def datasets_root() -> ET.Element:
    assert DATASETS_XML_PATH.is_file(), f"datasets.xml not found at {DATASETS_XML_PATH}"
    try:
        tree = ET.parse(DATASETS_XML_PATH)
    except ET.ParseError as exc:
        pytest.fail(f"Malformed XML syntax in datasets.xml: {exc}")

    root = tree.getroot()
    assert root.tag == "erddapDatasets", (
        f"Expected root tag 'erddapDatasets', got '{root.tag}'."
    )
    return root


def test_verify_dataset_database_parameters(datasets_root: ET.Element) -> None:
    """Verify database connection fields and ordering for EDDTableFromDatabase datasets."""
    datasets = datasets_root.findall("dataset")
    assert datasets, "No <dataset> entries found in datasets.xml."

    for dataset in datasets:
        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        if dataset.attrib.get("type") != "EDDTableFromDatabase":
            continue

        driver = dataset.find("driverName")
        url = dataset.find("connectionURL")
        user = dataset.find("userName")
        password = dataset.find("password")
        select_str = dataset.find("sqlStatement")
        order_by = dataset.find("orderBy")

        assert driver is not None and driver.text and driver.text.strip(), (
            f"Dataset '{dataset_id}' missing driverName."
        )
        assert url is not None and url.text and url.text.strip(), (
            f"Dataset '{dataset_id}' missing connectionURL."
        )
        assert url.text.strip().startswith("jdbc:postgresql://"), (
            f"Dataset '{dataset_id}' connectionURL must start with 'jdbc:postgresql://'."
        )
        assert user is not None and user.text and user.text.strip(), (
            f"Dataset '{dataset_id}' missing userName."
        )
        assert password is not None and password.text is not None, (
            f"Dataset '{dataset_id}' missing password."
        )
        assert select_str is not None and select_str.text and select_str.text.strip(), (
            f"Dataset '{dataset_id}' missing sqlStatement."
        )
        assert order_by is not None and order_by.text and order_by.text.strip(), (
            f"Dataset '{dataset_id}' missing orderBy."
        )

        global_attrs = _get_dataset_global_attributes(dataset)
        assert global_attrs.get("sourceUrl", "").strip(), (
            f"Dataset '{dataset_id}' missing sourceUrl attribute."
        )


def test_verify_cf_1_6_metadata_compliance(datasets_root: ET.Element) -> None:
    """Verify mandatory coordinate variables, units, data types, and CF-1.6 conventions."""
    required_coordinates: dict[str, tuple[str, str]] = {
        "time": ("String", "yyyy-MM-dd'T'HH:mm:ss'Z'"),
        "latitude": ("double", "degrees_north"),
        "longitude": ("double", "degrees_east"),
    }

    for dataset in datasets_root.findall("dataset"):
        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        global_attrs = _get_dataset_global_attributes(dataset)
        conventions = global_attrs.get("Conventions", "")
        assert "CF-1.6" in conventions, (
            f"Dataset '{dataset_id}' Conventions '{conventions}' does not declare CF-1.6."
        )

        found_coords: set[str] = set()
        for var in dataset.findall("dataVariable"):
            dest_el = var.find("destinationName")
            dtype_el = var.find("dataType")
            dest_name = dest_el.text.strip() if dest_el is not None and dest_el.text else None
            data_type = dtype_el.text.strip() if dtype_el is not None and dtype_el.text else None
            units = _get_variable_units(var)

            if dest_name in required_coordinates:
                found_coords.add(dest_name)
                expected_type, expected_units = required_coordinates[dest_name]
                assert data_type == expected_type, (
                    f"Dataset '{dataset_id}' variable '{dest_name}' expected type "
                    f"'{expected_type}', got '{data_type}'."
                )
                assert units == expected_units, (
                    f"Dataset '{dataset_id}' variable '{dest_name}' expected units "
                    f"'{expected_units}', got '{units}'."
                )

        missing_coords = set(required_coordinates) - found_coords
        assert not missing_coords, (
            f"Dataset '{dataset_id}' missing required coordinate variables: {sorted(missing_coords)}."
        )


def test_datasets_align_with_init_sql_schema(datasets_root: ET.Element) -> None:
    """Ensure SQL queries in datasets.xml reference telemetry_ingest and expected columns."""
    assert INIT_SQL_PATH.is_file(), f"init.sql not found at {INIT_SQL_PATH}"
    sql_text = _strip_sql_comments(INIT_SQL_PATH.read_text(encoding="utf-8"))

    assert re.search(r"CREATE\s+TABLE\s+telemetry_ingest\b", sql_text, re.IGNORECASE), (
        "init.sql is missing CREATE TABLE telemetry_ingest."
    )

    for dataset in datasets_root.findall("dataset"):
        if dataset.attrib.get("type") != "EDDTableFromDatabase":
            continue

        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        select_el = dataset.find("sqlStatement")
        assert select_el is not None and select_el.text and select_el.text.strip(), (
            f"Dataset '{dataset_id}' missing sqlStatement."
        )

        query = select_el.text
        assert re.search(r"\bFROM\s+telemetry_ingest\b", query, re.IGNORECASE), (
            f"Dataset '{dataset_id}' sqlStatement must query FROM telemetry_ingest."
        )
        assert "telemetry_table" not in query, (
            f"Dataset '{dataset_id}' sqlStatement still references dropped telemetry_table."
        )

        for var in dataset.findall("dataVariable"):
            source_el = var.find("sourceName")
            if source_el is not None and source_el.text:
                source_name = source_el.text.strip()
                assert re.search(rf"\b{re.escape(source_name)}\b", query), (
                    f"Dataset '{dataset_id}' sourceName '{source_name}' not found in sqlStatement."
                )
