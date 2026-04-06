from __future__ import annotations

from datetime import datetime
from typing import Optional, List
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


class PageCreate(BaseModel):
    title: str = Field(description="Page title (required)")
    parent_page_id: Optional[UUID] = Field(None, description="UUID of the parent page. Must belong to the same space.")
    text_content: Optional[str] = Field(None, description="Plain-text page content")


class PageUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New page title")
    parent_page_id: Optional[UUID] = Field(None, description="New parent page UUID. Must belong to the same space.")
    text_content: Optional[str] = Field(None, description="New plain-text page content")
