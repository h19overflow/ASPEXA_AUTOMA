"""Scans router - S3 scan result operations."""
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import asyncio

from libs.persistence import (
    load_scan,
    list_scans,
    scan_exists,
    delete_scan,
    ScanType,
    ArtifactNotFoundError,
)

router = APIRouter(prefix="/scans", tags=["scans"])

class ScanIdentifier(BaseModel):
    scan_type: str
    scan_id: str

class BatchDeleteRequest(BaseModel):
    scans: List[ScanIdentifier]


def _summary_to_dict(summary) -> Dict[str, Any]:
    """Convert ScanResultSummary to dict."""
    return {
        "scan_id": summary.scan_id,
        "scan_type": summary.scan_type.value,
        "audit_id": summary.audit_id,
        "timestamp": summary.timestamp,
        "s3_key": summary.s3_key,
        "filename": summary.filename,
    }


@router.get("")
async def list_all_scans(
    scan_type: Optional[str] = None,
    audit_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List scans with optional filters.

    Args:
        scan_type: Filter by type (recon, garak, exploit)
        audit_id: Filter by audit ID substring
    """
    type_filter = None
    if scan_type:
        try:
            type_filter = ScanType(scan_type)
        except ValueError:
            raise HTTPException(400, f"Invalid scan_type: {scan_type}")

    summaries = await list_scans(scan_type=type_filter, audit_id_filter=audit_id)
    return [_summary_to_dict(s) for s in summaries]


@router.get("/recon")
async def list_recon_scans(audit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all reconnaissance scans."""
    summaries = await list_scans(scan_type=ScanType.RECON, audit_id_filter=audit_id)
    return [_summary_to_dict(s) for s in summaries]


@router.get("/garak")
async def list_garak_scans(audit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all garak vulnerability scans."""
    summaries = await list_scans(scan_type=ScanType.GARAK, audit_id_filter=audit_id)
    return [_summary_to_dict(s) for s in summaries]


@router.get("/exploit")
async def list_exploit_scans(audit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all exploit scans."""
    summaries = await list_scans(scan_type=ScanType.EXPLOIT, audit_id_filter=audit_id)
    return [_summary_to_dict(s) for s in summaries]


@router.get("/recon/{scan_id}")
async def get_recon_scan(scan_id: str, validate: bool = False) -> Dict[str, Any]:
    """Get a reconnaissance scan result."""
    try:
        result = await load_scan(ScanType.RECON, scan_id, validate=validate)
        if validate:
            return result.model_dump()
        return result
    except ArtifactNotFoundError:
        raise HTTPException(404, f"Recon scan {scan_id} not found")


@router.get("/garak/{scan_id}")
async def get_garak_scan(scan_id: str, validate: bool = False) -> Dict[str, Any]:
    """Get a garak vulnerability scan result."""
    try:
        result = await load_scan(ScanType.GARAK, scan_id, validate=validate)
        if validate:
            return result.model_dump()
        return result
    except ArtifactNotFoundError:
        raise HTTPException(404, f"Garak scan {scan_id} not found")


@router.get("/exploit/{scan_id}")
async def get_exploit_scan(scan_id: str, validate: bool = False) -> Dict[str, Any]:
    """Get an exploit scan result."""
    try:
        result = await load_scan(ScanType.EXPLOIT, scan_id, validate=validate)
        if validate:
            return result.model_dump()
        return result
    except ArtifactNotFoundError:
        raise HTTPException(404, f"Exploit scan {scan_id} not found")

@router.get("/checkpoint/{scan_id}")
async def get_checkpoint_scan(scan_id: str, validate: bool = False) -> Dict[str, Any]:
    """Get a checkpoint scan result."""
    try:
        result = await load_scan(ScanType.CHECKPOINT, scan_id, validate=validate)
        if validate:
            return result.model_dump()
        return result
    except ArtifactNotFoundError:
        raise HTTPException(404, f"Checkpoint scan {scan_id} not found")

@router.delete("/recon/{scan_id}")
async def delete_recon_scan(scan_id: str) -> Dict[str, str]:
    """Delete a recon scan from S3."""
    deleted = await delete_scan(ScanType.RECON, scan_id)
    if not deleted:
        raise HTTPException(404, f"Recon scan {scan_id} not found")
    return {"status": "deleted", "scan_id": scan_id}


@router.delete("/garak/{scan_id}")
async def delete_garak_scan(scan_id: str) -> Dict[str, str]:
    """Delete a garak scan from S3."""
    deleted = await delete_scan(ScanType.GARAK, scan_id)
    if not deleted:
        raise HTTPException(404, f"Garak scan {scan_id} not found")
    return {"status": "deleted", "scan_id": scan_id}


@router.delete("/exploit/{scan_id}")
async def delete_exploit_scan(scan_id: str) -> Dict[str, str]:
    """Delete an exploit scan from S3."""
    deleted = await delete_scan(ScanType.EXPLOIT, scan_id)
    if not deleted:
        raise HTTPException(404, f"Exploit scan {scan_id} not found")
    return {"status": "deleted", "scan_id": scan_id}


@router.delete("/checkpoint/{scan_id}")
async def delete_checkpoint_scan(scan_id: str) -> Dict[str, str]:
    """Delete a checkpoint scan from S3."""
    deleted = await delete_scan(ScanType.CHECKPOINT, scan_id)
    if not deleted:
        raise HTTPException(404, f"Checkpoint scan {scan_id} not found")
    return {"status": "deleted", "scan_id": scan_id}


@router.post("/batch-delete")
async def batch_delete_scans(request: BatchDeleteRequest) -> Dict[str, Any]:
    """Delete multiple scans concurrently."""
    tasks = []
    
    for scan_req in request.scans:
        try:
            scan_type = ScanType(scan_req.scan_type)
        except ValueError:
            continue
            
        tasks.append(delete_scan(scan_type, scan_req.scan_id))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = sum(1 for r in results if r is True)
    not_found_count = sum(1 for r in results if r is False)
    error_count = sum(1 for r in results if isinstance(r, Exception))
    
    return {
        "status": "completed",
        "processed": len(request.scans),
        "deleted": success_count,
        "not_found": not_found_count,
        "errors": error_count
    }
