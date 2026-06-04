"""
Industry Pack Import API

POST /api/v1/industry-packs/import
Import an industry pack from a .nexus-pack (zip) file.

Sprint 110: B110-2
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from reins.common.database import get_db
from reins.industry.pack_importer import (
    PackImporter,
    PackImportError,
    InvalidPackError,
    ChecksumMismatchError,
    DependencyMissingError,
    PackExistsError,
    SecurityError,
    IncompatibleFormatError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/industry-packs", tags=["industry-packs-import"])


@router.post("/import")
async def import_industry_pack(
    file: UploadFile = File(..., description="Industry pack file (.nexus-pack)"),
    strategy: str = Form("create", description="Import strategy: create, upsert, or force"),
    db: Session = Depends(get_db),
):
    """
    Import an industry pack from a .nexus-pack (zip) file.

    Args:
        file: The .nexus-pack zip file to import.
        strategy:
            - "create" (default): Fail with 409 if pack already exists.
            - "upsert": Update existing pack; insert if new.
            - "force": Overwrite existing pack completely.

    Returns:
        Import result JSON with success status, pack_id, and counts.

    Error responses:
        - 400: Invalid pack, checksum mismatch, missing dependencies, incompatible format
        - 409: Pack already exists (create strategy)
        - 422: Invalid file or strategy parameter
    """
    # Validate strategy
    if strategy not in ("create", "upsert", "force"):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid strategy '{strategy}'. Must be 'create', 'upsert', or 'force'.",
        )

    # Read file bytes
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read upload: {e}",
        )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty file received.",
        )

    # Import
    importer = PackImporter(db)

    try:
        result = importer.import_pack(file_bytes, strategy=strategy)
        return result

    except PackExistsError as e:
        raise HTTPException(status_code=409, detail=e.message)

    except (InvalidPackError, ChecksumMismatchError, DependencyMissingError,
            SecurityError, IncompatibleFormatError) as e:
        raise HTTPException(status_code=400, detail=e.message)

    except PackImportError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    except Exception as e:
        logger.exception(f"Pack import failed unexpectedly: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during import: {str(e)}",
        )
