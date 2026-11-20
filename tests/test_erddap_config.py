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
