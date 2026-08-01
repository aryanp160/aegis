RULE_DOCUMENTATION: dict[str, dict[str, str]] = {
    "allow_drop_table": {
        "description": "Prohibits dropping tables to prevent accidental data loss.",
        "severity": "error",
        "why_it_matters": (
            "Dropping a table completely destroys the table and all of its data.\n"
            "In production environments, this operation is highly destructive and\n"
            "should generally be avoided or done with extreme caution via manual "
            "scripts."
        ),
        "remediation": (
            "Instead of dropping the table, consider archiving the data or keeping\n"
            "the table active but unused until it can be safely decommissioned."
        ),
    },
    "allow_drop_column": {
        "description": "Prohibits dropping columns to prevent accidental data loss.",
        "severity": "error",
        "why_it_matters": (
            "Dropping a column immediately deletes the column definition and all\n"
            "associated data from the table. This is a non-retroactive operation\n"
            "that can break active application queries currently expecting the column."
        ),
        "remediation": (
            "Deprecate the column in the application code first. Mark it as nullable\n"
            "or unused, and perform the actual column drop only after all application\n"
            "code has been updated and deployed."
        ),
    },
    "allow_rename_table": {
        "description": "Prohibits renaming tables to avoid application downtime.",
        "severity": "warning",
        "why_it_matters": (
            "Renaming a table will immediately break any active queries or views\n"
            "referencing the old table name, causing service downtime during "
            "deployments."
        ),
        "remediation": (
            "Create a new table (or a view pointing to the new table) with the new "
            "name,\n"
            "migrate data, update application queries, and then drop the old "
            "table/view."
        ),
    },
}
