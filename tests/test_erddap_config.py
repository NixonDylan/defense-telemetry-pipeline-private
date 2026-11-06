import os
import xml.etree.ElementTree as ET
import pytest

# Target the exact configuration file sitting in your root directory
DATASETS_XML_PATH = os.path.join(os.path.dirname(__file__), "..", "datasets.xml")

def test_datasets_xml_exists():
    """Verify that the datasets.xml manifest file is present in the repository."""
    assert os.path.exists(DATASETS_XML_PATH), "datasets.xml is missing from the repository root!"

def test_datasets_xml_well_formed():
    """Parse the XML document to ensure there are no syntax or structural markup errors."""
    try:
        tree = ET.parse(DATASETS_XML_PATH)
        root = tree.getroot()
        assert root is not None, "The XML document root element is empty."
        assert root.tag == "erddapDatasets", f"Expected root tag 'erddapDatasets', but found '{root.tag}'."
    except ET.ParseError as error:
        pytest.fail(f"Malformed XML syntax detected in datasets.xml: {str(error)}")

def test_verify_dataset_database_parameters():
    """Scan the file to check that any declared datasets contain vital connection properties."""
    if not os.path.exists(DATASETS_XML_PATH):
        return

    tree = ET.parse(DATASETS_XML_PATH)
    root = tree.getroot()
    
    # Locate all individual dataset blocks defined inside the manifest
    datasets = root.findall("dataset")
    
    for dataset in datasets:
        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        dataset_type = dataset.attrib.get("type", "unknown_type")
        
        # If your dataset interfaces with your PostgreSQL container layout
        if dataset_type == "EDDTableFromDatabase":
            source_url = dataset.find(".//sourceUrl")
            assert source_url is not None, f"Dataset '{dataset_id}' is missing a sourceUrl configuration tag!"
            assert "postgresql" in source_url.text.lower(), f"Dataset '{dataset_id}' sourceUrl does not point to a PostgreSQL bridge."
