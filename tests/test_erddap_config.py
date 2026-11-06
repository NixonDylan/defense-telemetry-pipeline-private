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
    """Scan the file to check that any declared database datasets contain vital connection properties."""
    if not os.path.exists(DATASETS_XML_PATH):
        return

    tree = ET.parse(DATASETS_XML_PATH)
    root = tree.getroot()
    
    datasets = root.findall("dataset")
    
    for dataset in datasets:
        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        dataset_type = dataset.attrib.get("type", "unknown_type")
        
        # Correctly evaluate database connection parameters according to ERDDAP specifications
        if dataset_type == "EDDTableFromDatabase":
            connection_url = dataset.find(".//connectionURL")
            assert connection_url is not None, f"Dataset '{dataset_id}' is missing a connectionURL configuration tag!"
            assert "postgresql" in connection_url.text.lower(), f"Dataset '{dataset_id}' connectionURL does not point to a PostgreSQL bridge."
def test_verify_cf_1_6_metadata_compliance():
    """Audit the datasets.xml attributes to guarantee strict CF-1.6 metadata compatibility."""
    if not os.path.exists(DATASETS_XML_PATH):
        return

    tree = ET.parse(DATASETS_XML_PATH)
    root = tree.getroot()
    
    datasets = root.findall("dataset")
    
    # CF-1.6 mandates specific standard coordinate identification metrics
    required_coordinates = {
        "time": {"units": "yyyy-MM-dd'T'HH:mm:ss'Z'", "data_type": "String"},
        "latitude": {"units": "degrees_north", "data_type": "double"},
        "longitude": {"units": "degrees_east", "data_type": "double"}
    }

    for dataset in datasets:
        dataset_id = dataset.attrib.get("datasetID", "unknown_id")
        data_variables = dataset.findall("dataVariable")
        
        found_coords = []
        
        for var in data_variables:
            dest_name = var.find("destinationName").text if var.find("destinationName") is not None else None
            data_type = var.find("dataType").text if var.find("dataType") is not None else None
            units = var.find("units").text if var.find("units") is not None else None
            
            # Check coordinate dimensions for structural alignment
            if dest_name in required_coordinates:
                found_coords.append(dest_name)
                expected = required_coordinates[dest_name]
                
                # Assertions to prevent compliance failure
                assert data_type == expected["data_type"], \
                    f"CF Failure: Dataset '{dataset_id}' variable '{dest_name}' must be type '{expected['data_type']}'"
                assert units == expected["units"], \
                    f"CF Failure: Dataset '{dataset_id}' variable '{dest_name}' must use units '{expected['units']}'"

        # CF-1.6 requires all spatial-temporal trajectories to contain full coordinate records
        for coord in required_coordinates.keys():
            assert coord in found_coords, \
                f"CF Failure: Dataset '{dataset_id}' is missing the mandatory '{coord}' coordinate mapping block!"
