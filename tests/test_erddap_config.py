from pathlib import Path
import re
import xml.etree.ElementTree as ET
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS_XML_PATH = REPO_ROOT / "datasets.xml"
INIT_SQL_PATH = REPO_ROOT / "init.sql"


def _get_variable_units(var: ET.Element) -> str | None:
    """Return units from either a direct <units> child or <addAttributes><att name='units'>."""
    direct_units = var.find("units")
    if direct_units is not None and direct_units.text:
        return direct_units.text.strip()

    for att in var.findall("./addAttributes/att"):
        if att.attrib.get("name") == "units" and att.text:
            return att.text.strip()

    return None


def _get_dataset_global_attributes(dataset: ET.Element) -> dict[str, str]:
    """Extract dataset-level <addAttributes><att name='...'> values."""
    attrs: dict[str, str] = {}
    for att in dataset.findall("./addAttributes/att"):
        name = att.attrib.get("name")
        if name and att.text is not None:
            attrs[name] = att.text.strip()
    return attrs


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
    """Verify database connection fields for EDDTableFromDatabase datasets."""
    datasets = datasets_root.findall("dataset")
    assert datasets, "No <dataset> entries found in datasets.xml."

    for dataset in datasets:
        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        if dataset.attrib.get("type") != "EDDTableFromDatabase":
            continue

        driver = dataset.find("driverClassName")
        url = dataset.find("connectionURL")
        user = dataset.find("dbUser")
        password = dataset.find("dbPassword")
        select_str = dataset.find("selectString")

        assert driver is not None and driver.text and driver.text.strip(), (
            f"Dataset '{dataset_id}' missing driverClassName."
        )
        assert url is not None and url.text and url.text.strip(), (
            f"Dataset '{dataset_id}' missing connectionURL."
        )
        assert url.text.strip().startswith("jdbc:postgresql://"), (
            f"Dataset '{dataset_id}' connectionURL must start with 'jdbc:postgresql://'."
        )
        assert user is not None and user.text and user.text.strip(), (
            f"Dataset '{dataset_id}' missing dbUser."
        )
        assert password is not None and password.text is not None, (
            f"Dataset '{dataset_id}' missing dbPassword."
        )
        assert select_str is not None and select_str.text and select_str.text.strip(), (
            f"Dataset '{dataset_id}' missing selectString."
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
            f"Dataset '{dataset_id}' missing required coordinates: {sorted(missing_coords)}."
        )


def test_datasets_align_with_init_sql_schema(datasets_root: ET.Element) -> None:
    """Ensure SQL queries in datasets.xml reference telemetry_ingest and expected columns."""
    assert INIT_SQL_PATH.is_file(), f"init.sql not found at {INIT_SQL_PATH}"
    sql_text = INIT_SQL_PATH.read_text(encoding="utf-8")

    assert re.search(r"CREATE\s+TABLE\s+telemetry_ingest\b", sql_text, re.IGNORECASE), (
        "init.sql is missing CREATE TABLE telemetry_ingest."
    )

    for dataset in datasets_root.findall("dataset"):
        if dataset.attrib.get("type") != "EDDTableFromDatabase":
            continue

        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        select_el = dataset.find("selectString")
        assert select_el is not None and select_el.text

        query = select_el.text
        assert re.search(r"\bFROM\s+telemetry_ingest\b", query, re.IGNORECASE), (
            f"Dataset '{dataset_id}' selectString must query FROM telemetry_ingest."
        )
        assert not re.search(r"\bFROM\s+telemetry_table\b", query, re.IGNORECASE), (
            f"Dataset '{dataset_id}' selectString still references dropped telemetry_table."
        )

        # Verify top-level columns referenced in query exist in telemetry_ingest
        for col in ("device_id", "timestamp", "metrics"):
            if re.search(rf"\b{col}\b", query, re.IGNORECASE):
                assert re.search(rf"\b{col}\b", sql_text, re.IGNORECASE), (
                    f"Dataset '{dataset_id}' references column '{col}' not found in init.sql."
                )

        # Ensure every dataVariable sourceName is present in selectString
        for var in dataset.findall("dataVariable"):
            src_el = var.find("sourceName")
            assert src_el is not None and src_el.text and src_el.text.strip(), (
                f"Dataset '{dataset_id}' has a dataVariable missing sourceName."
            )
            source_name = src_el.text.strip()
            assert re.search(rf"\b{re.escape(source_name)}\b", query), (
                f"Dataset '{dataset_id}' sourceName '{source_name}' not found in selectString."
            )
