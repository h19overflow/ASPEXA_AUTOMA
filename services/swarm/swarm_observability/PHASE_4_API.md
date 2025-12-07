# Phase 4: API Endpoints

## Files to Modify

| File | Changes |
|------|---------|
| `api_gateway/routers/scan.py` | Add control endpoints |

---

## 4.1 New Endpoints

```python
from services.swarm.entrypoint import cancel_scan, pause_scan, resume_scan


@router.post("/scan/{scan_id}/cancel")
async def cancel_endpoint(scan_id: str):
    return await cancel_scan(scan_id)


@router.post("/scan/{scan_id}/pause")
async def pause_endpoint(scan_id: str):
    return await pause_scan(scan_id)


@router.post("/scan/{scan_id}/resume")
async def resume_endpoint(scan_id: str):
    return await resume_scan(scan_id)


@router.get("/scan/{scan_id}/status")
async def status_endpoint(scan_id: str):
    mgr = get_manager(scan_id)
    return {
        "scan_id": scan_id,
        "cancelled": mgr.is_cancelled,
        "paused": mgr.is_paused,
    }
```

---

## 4.2 Response includes scan_id

Update streaming endpoint to return scan_id in initial event:

```python
@router.post("/scan/start/stream")
async def start_scan_stream(request: ScanStartRequest):
    scan_id = str(uuid.uuid4())

    async def generate():
        async for event in execute_scan_streaming(request, scan_id=scan_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Scan-Id": scan_id},
    )
```

---

## Done When

- [x] All 4 endpoints work
- [x] scan_id in response header
- [x] Status endpoint returns correct state
