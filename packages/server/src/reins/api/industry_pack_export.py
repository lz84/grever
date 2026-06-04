"""
Industry Pack Export API

POST /api/v1/industry-packs/{pack_id}/export

Sprint 109: B109-2
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from reins.common.database import get_db
from reins.industry.pack_exporter import (
    PackExporter,
    PackNotFoundError,
    UnsupportedFormatError,
)

router = APIRouter(prefix="/api/v1/industry-packs", tags=["industry-packs-export"])


class ExportRequest(BaseModel):
    """Request body for pack export."""
    format: str = Field(
        default="nexus-pack",
        description="Export format: 'nexus-pack' (zip) or 'json'",
    )
    include_assets: bool = Field(
        default=True,
        description="Whether to include actual content data in the export",
    )


@router.post("/{pack_id}/export")
async def export_pack(
    pack_id: str,
    request: ExportRequest,
    db: Session = Depends(get_db),
):
    """
    Export an industry pack.

    - **pack_id**: The ID of the pack to export.
    - **format**: Export format - "nexus-pack" (zip) or "json".
    - **include_assets**: Include actual content data.

    Returns:
        - For nexus-pack: zip file download (application/zip)
        - For json: JSON response
    """
    exporter = PackExporter(db)

    try:
        data = exporter.export_pack(
            pack_id=pack_id,
            format=request.format,
            include_assets=request.include_assets,
        )
    except PackNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Pack '{pack_id}' not found",
        )
    except UnsupportedFormatError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    if request.format == "nexus-pack":
        return Response(
            content=data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{pack_id}.nexus-pack"',
            },
        )
    else:
        return Response(
            content=data,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{pack_id}.json"',
            },
        )
