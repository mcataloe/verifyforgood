from charity_status.form990 import load_form990_monthly_workflow_binding


def test_form990_monthly_workflow_binding_uses_existing_prefixes_and_generic_contract():
    binding = load_form990_monthly_workflow_binding(
        {
            "BUCKET": "charity-data",
            "FORM990_RAW_SOURCE_PREFIX": "form990/raw-sources/",
            "FORM990_MANIFEST_PREFIX": "form990/normalized/manifests/",
            "APP_ENV": "prod",
            "AWS_REGION": "us-east-1",
        }
    )

    assert binding.validate() == []
    workflow_input = binding.build_downloaded_source_step_function_input(
        source_year="2026",
        source_kind="zip_archive",
        source_archive_key="2026_teos_xml_02a",
        source_signature="etag-123",
        source_filename="2026_TEOS_XML_02A.zip",
        job_id="job-202603",
    )

    assert binding.workflow.workflow_name == "monthly-ingest-prod"
    assert binding.source_download_timeout_seconds == 300
    assert workflow_input.source_bucket == "charity-data"
    assert workflow_input.destination_bucket == "charity-data"
    assert workflow_input.destination_prefix == "form990/normalized/manifests/"
    assert workflow_input.source_key == "form990/raw-sources/2026/zip_archive/2026_teos_xml_02a/etag-123/2026_TEOS_XML_02A.zip"
    assert binding.build_staged_source_key(
        source_year="2026",
        source_kind="zip_archive",
        source_archive_key="2026_teos_xml_02a",
        source_signature="etag-123",
        source_filename="2026_TEOS_XML_02A.zip",
    ) == workflow_input.source_key
    env = binding.build_ecs_environment(workflow_input)
    assert env["MONTHLY_INGEST_SOURCE_KEY"] == workflow_input.source_key
    assert env["MONTHLY_INGEST_DESTINATION_PREFIX"] == "form990/normalized/manifests/"
