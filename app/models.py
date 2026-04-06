from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SpaceOut(BaseModel):
    id: UUID = Field(description="Space UUID")
    name: Optional[str] = Field(None, description="Display name of the space")
    description: Optional[str] = Field(None, description="Optional space description")
    slug: str = Field(description="URL-friendly identifier")
    visibility: str = Field(description="Visibility setting (e.g. public, private)")
    default_role: str = Field(description="Default member role for this space")
    creator_id: Optional[UUID] = Field(None, description="UUID of the user who created the space")
    workspace_id: UUID = Field(description="UUID of the parent workspace")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageOut(BaseModel):
    id: UUID = Field(description="Page UUID")
    slug_id: str = Field(description="Short URL-friendly identifier")
    title: Optional[str] = Field(None, description="Page title")
    icon: Optional[str] = Field(None, description="Emoji or icon identifier")
    position: Optional[str] = Field(None, description="Sort position within the parent")
    parent_page_id: Optional[UUID] = Field(None, description="UUID of the parent page, or null for root pages")
    creator_id: Optional[UUID] = Field(None, description="UUID of the user who created the page")
    last_updated_by_id: Optional[UUID] = Field(None, description="UUID of the user who last updated the page")
    space_id: UUID = Field(description="UUID of the space this page belongs to")
    workspace_id: UUID = Field(description="UUID of the parent workspace")
    is_locked: bool = Field(description="Whether the page is locked for editing")
    text_content: Optional[str] = Field(
        None,
        description=(
            "Normalized plain-text content of the page. "
            "Repeated newline runs and repeated '+' storage noise are collapsed before this is returned."
        ),
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SpaceSummaryOut(BaseModel):
    id: UUID = Field(description="Space UUID")
    name: Optional[str] = Field(None, description="Display name of the space")
    slug: str = Field(description="URL-friendly identifier")

    model_config = {"from_attributes": True}


class PageTreeNode(BaseModel):
    id: UUID = Field(description="Page UUID")
    title: Optional[str] = Field(None, description="Page title")
    slug_id: str = Field(description="Short URL-friendly identifier")
    icon: Optional[str] = Field(None, description="Emoji or icon identifier")
    parent_page_id: Optional[UUID] = Field(None, description="UUID of the parent page, or null for root pages")
    position: Optional[str] = Field(None, description="Sort position within the parent")
    has_children: bool = Field(description="Whether this page has child pages in the resolved tree")
    children: list["PageTreeNode"] = Field(default_factory=list, description="Nested child pages")

    model_config = {"from_attributes": True}


class SpaceTreeOut(BaseModel):
    space: SpaceSummaryOut
    root_pages: list[PageTreeNode] = Field(
        default_factory=list,
        description="Top-level pages in the space, each with fully nested descendants.",
    )
    orphan_pages: list[PageTreeNode] = Field(
        default_factory=list,
        description="Pages that could not be attached to a normal root because their parent is missing or unreachable.",
    )

    model_config = {"from_attributes": True}


PageTreeNode.model_rebuild()


class ReplicaStandardsOut(BaseModel):
    replica_root_suffix: str = Field(description="Suffix appended to the space name to form the replica root directory.")
    replica_root_example: str = Field(description="Example replica root directory path.")
    page_directory_base_rule: str = Field(description="Base directory naming rule for a page.")
    sibling_collision_rule: str = Field(description="How same-level directory name collisions are resolved.")
    final_collision_fallback_rule: str = Field(description="Fallback naming rule if the primary collision strategy still collides.")
    page_content_file_name: str = Field(description="File name that stores the page's markdown/text content.")
    page_meta_file_name: str = Field(description="File name that stores per-page metadata.")
    replica_meta_file_name: str = Field(description="File name that stores replica-level metadata.")
    tree_cache_file_name: str = Field(description="File name that stores the resolved tree snapshot.")
    initial_replica_source_rule: str = Field(description="How to build or refresh the initial local replica for existing remote content.")
    local_addition_source_rule: str = Field(description="How to create local-only documentation that does not yet exist on remote.")
    local_replica_requirement: str = Field(description="Whether a local replica is expected for normal client use.")
    read_source_policy: str = Field(description="How the remote Docmost source should be used for reads.")
    local_edit_policy: str = Field(description="How the local replica should be used for edits.")
    local_truth_policy: str = Field(description="How newer local-only changes should be treated before manual sync.")
    remote_sync_policy: str = Field(description="How to interpret remote state after local-only replica edits.")
    edited_replica_reporting_rule: str = Field(description="How edited local replica files should be surfaced back to the user.")
    remote_page_mapping_rule: str = Field(description="How a local replica file should be mapped back to its remote Docmost page.")
    manual_sync_prompt_rule: str = Field(description="When the client should prompt the user to sync local replica changes back to remote.")

    model_config = {"from_attributes": True}


class ReplicaNameResolutionOut(BaseModel):
    input_title: str = Field(description="Requested page title.")
    slug_id: Optional[str] = Field(None, description="Optional remote or planned slug identifier.")
    page_id: Optional[UUID] = Field(None, description="Optional remote page UUID.")
    sanitized_title: str = Field(description="Filesystem-safe form of the title used as the base directory name.")
    local_dir_name: str = Field(description="Resolved local directory name for the page.")
    collision_strategy: str = Field(description="Naming strategy used to resolve the final directory name.")

    model_config = {"from_attributes": True}


class ReplicaTreeNode(BaseModel):
    id: UUID = Field(description="Page UUID")
    title: Optional[str] = Field(None, description="Page title")
    slug_id: str = Field(description="Short URL-friendly identifier")
    parent_page_id: Optional[UUID] = Field(None, description="UUID of the parent page, or null for root pages")
    local_dir_name: str = Field(description="Resolved directory name for this page inside the replica.")
    local_dir_path: str = Field(description="Replica-relative directory path for this page.")
    content_file_path: str = Field(description="Replica-relative content file path for this page.")
    meta_file_path: str = Field(description="Replica-relative metadata file path for this page.")
    children: list["ReplicaTreeNode"] = Field(default_factory=list, description="Nested child pages in replica form.")

    model_config = {"from_attributes": True}


class ReplicaStructureOut(BaseModel):
    space: SpaceSummaryOut
    replica_root: str = Field(description="Replica root directory path for the space.")
    replica_meta_file_path: str = Field(description="Replica-relative path to the replica metadata file.")
    tree_cache_file_path: str = Field(description="Replica-relative path to the tree cache file.")
    standards: ReplicaStandardsOut
    root_pages: list[ReplicaTreeNode] = Field(
        default_factory=list,
        description="Root-level page directories in replica form, each with nested descendants.",
    )
    orphan_pages: list[ReplicaTreeNode] = Field(
        default_factory=list,
        description="Replica nodes for pages that could not be attached to a normal root because the parent is missing or unreachable.",
    )

    model_config = {"from_attributes": True}


ReplicaTreeNode.model_rebuild()
