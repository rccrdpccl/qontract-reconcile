from reconcile.change_owners.bundle import (
    BundleFileType,
    FileRef,
)
from reconcile.change_owners.change_types import (
    build_change_type_processor,
    create_bundle_file_change,
)
from reconcile.gql_definitions.change_owners.queries.change_types import ChangeTypeV1
from reconcile.test.change_owners.fixtures import TestFile

pytest_plugins = [
    "reconcile.test.change_owners.fixtures",
]

#
# testcases for context file refs extraction from bundle changes
#


def test_extract_context_file_refs_from_bundle_change(
    saas_file_changetype: ChangeTypeV1, saas_file: TestFile
):
    """
    in this testcase, a changed datafile matches directly the context schema
    of the change type, so the change type is directly relevant for the changed
    datafile
    """
    bundle_change = saas_file.create_bundle_change(
        {"resourceTemplates[0].targets[0].ref": "new-ref"}
    )
    file_refs = bundle_change.extract_context_file_refs(
        build_change_type_processor(saas_file_changetype)
    )
    assert file_refs == [saas_file.file_ref()]


def test_extract_context_file_refs_from_bundle_change_schema_mismatch(
    saas_file_changetype: ChangeTypeV1, saas_file: TestFile
):
    """
    in this testcase, the schema of the bundle change and the schema of the
    change types do not match and hence no file context is extracted.
    """
    saas_file.fileschema = "/some/other/schema.yml"
    bundle_change = saas_file.create_bundle_change(
        {"resourceTemplates[0].targets[0].ref": "new-ref"}
    )
    file_refs = bundle_change.extract_context_file_refs(
        build_change_type_processor(saas_file_changetype)
    )
    assert not file_refs


def test_extract_context_file_refs_selector(
    cluster_owner_change_type: ChangeTypeV1,
):
    """
    this testcase extracts the context file based on the change types context
    selector
    """
    cluster = "/my/cluster.yml"
    namespace_change = create_bundle_file_change(
        path="/my/namespace.yml",
        schema="/openshift/namespace-1.yml",
        file_type=BundleFileType.DATAFILE,
        old_file_content={
            "the_change": "does not matter in this test",
            "cluster": {
                "$ref": cluster,
            },
        },
        new_file_content={
            "cluster": {
                "$ref": cluster,
            },
        },
    )
    assert namespace_change
    file_refs = namespace_change.extract_context_file_refs(
        build_change_type_processor(cluster_owner_change_type)
    )
    assert file_refs == [
        FileRef(
            file_type=BundleFileType.DATAFILE,
            schema="/openshift/cluster-1.yml",
            path=cluster,
        )
    ]


def test_extract_context_file_refs_in_list_added_selector(
    role_member_change_type: ChangeTypeV1,
):
    """
    in this testcase, a changed datafile does not directly belong to the change
    type, because the context schema does not match (change type reacts to roles,
    while the changed datafile is a user). but the change type defines a context
    extraction section that feels responsible for user files and extracts the
    relevant context, the role, from the users role section, looking out for added
    roles.
    """
    new_role = "/role/new.yml"
    user_change = create_bundle_file_change(
        path="/somepath.yml",
        schema="/access/user-1.yml",
        file_type=BundleFileType.DATAFILE,
        old_file_content={
            "roles": [{"$ref": "/role/existing.yml"}],
        },
        new_file_content={
            "roles": [{"$ref": "/role/existing.yml"}, {"$ref": new_role}],
        },
    )
    assert user_change
    file_refs = user_change.extract_context_file_refs(
        build_change_type_processor(role_member_change_type)
    )
    assert file_refs == [
        FileRef(
            file_type=BundleFileType.DATAFILE,
            schema="/access/role-1.yml",
            path=new_role,
        )
    ]


def test_extract_context_file_refs_in_list_removed_selector(
    role_member_change_type: ChangeTypeV1,
):
    """
    this testcase is similar to previous one, but detects removed contexts (e.g
    roles in this example) as the relevant context to extract.
    """
    role_member_change_type.changes[0].context.when = "removed"  # type: ignore
    existing_role = "/role/existing.yml"
    new_role = "/role/new.yml"
    user_change = create_bundle_file_change(
        path="/somepath.yml",
        schema="/access/user-1.yml",
        file_type=BundleFileType.DATAFILE,
        old_file_content={
            "roles": [{"$ref": existing_role}],
        },
        new_file_content={
            "roles": [{"$ref": new_role}],
        },
    )
    assert user_change
    file_refs = user_change.extract_context_file_refs(
        build_change_type_processor(role_member_change_type)
    )
    assert file_refs == [
        FileRef(
            file_type=BundleFileType.DATAFILE,
            schema="/access/role-1.yml",
            path=existing_role,
        )
    ]


def test_extract_context_file_refs_in_list_selector_change_schema_mismatch(
    role_member_change_type: ChangeTypeV1,
):
    """
    in this testcase, the changeSchema section of the change types changes does
    not match the bundle change.
    """
    datafile_change = create_bundle_file_change(
        path="/somepath.yml",
        schema="/some/other/schema.yml",
        file_type=BundleFileType.DATAFILE,
        old_file_content={"field": "old-value"},
        new_file_content={"field": "new-value"},
    )
    assert datafile_change
    file_refs = datafile_change.extract_context_file_refs(
        build_change_type_processor(role_member_change_type)
    )
    assert not file_refs
