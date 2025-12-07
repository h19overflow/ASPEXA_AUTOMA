# Unused Routes Cleanup Plan

## Overview
This document outlines the cleanup of dead code from both the API Gateway (backend) and Viper Command Center (frontend). These routes/functions were created for non-streaming approaches but are no longer used.

## Analysis Summary
- **10 backend routes** to delete
- **10 frontend functions** to delete
- **0 breaking changes** (all code is unused)

---

## Backend Routes to Delete

### 1. scans.py - HEAD endpoints (existence checks)
**File**: `services/api_gateway/routers/scans.py`

| Route | Function | Line |
|-------|----------|------|
| `HEAD /api/scans/recon/{scan_id}` | `check_recon_exists` | ~TBD |
| `HEAD /api/scans/garak/{scan_id}` | `check_garak_exists` | ~TBD |
| `HEAD /api/scans/exploit/{scan_id}` | `check_exploit_exists` | ~TBD |

**Reason**: Never called from frontend. GET endpoints are used instead.

---

### 2. phase1.py - Framing types endpoint
**File**: `services/api_gateway/routers/snipers/phase1.py`

| Route | Function | Line |
|-------|----------|------|
| `GET /api/snipers/phase1/framing-types` | `list_framing_types` | ~TBD |

**Reason**: Frontend uses hardcoded framing options in components.

---

### 3. phase2.py - Standalone phase2 and preview
**File**: `services/api_gateway/routers/snipers/phase2.py`

| Route | Function | Line |
|-------|----------|------|
| `POST /api/snipers/phase2` | `execute_phase2` | ~TBD |
| `POST /api/snipers/phase2/preview` | `preview_conversion` | ~TBD |

**Reason**: Frontend only uses `executePhase2WithPhase1()` which chains phases.

---

### 4. phase3.py - Chained phase3 and scorers
**File**: `services/api_gateway/routers/snipers/phase3.py`

| Route | Function | Line |
|-------|----------|------|
| `POST /api/snipers/phase3/with-phase2` | `execute_phase3_with_phase2` | ~TBD |
| `GET /api/snipers/phase3/scorers` | `list_scorers` | ~TBD |

**Reason**: Frontend uses standalone `executePhase3()` after manual phase2.

---

### 5. attack.py - Non-streaming attack endpoints
**File**: `services/api_gateway/routers/snipers/attack.py`

| Route | Function | Line |
|-------|----------|------|
| `POST /api/snipers/attack/full` | `run_full_attack` | ~TBD |
| `POST /api/snipers/attack/adaptive` | `run_adaptive_attack` | ~TBD |

**Reason**: Frontend only uses streaming versions (`/stream` suffix).

---

## Frontend Functions to Delete

### File: `viper-command-center/src/lib/api/services.ts`

| Function | Line | Corresponding Backend Route |
|----------|------|----------------------------|
| `checkReconExists()` | ~395 | `HEAD /api/scans/recon/{id}` |
| `checkGarakExists()` | ~399 | `HEAD /api/scans/garak/{id}` |
| `checkExploitExists()` | ~403 | `HEAD /api/scans/exploit/{id}` |
| `getFramingTypes()` | ~493 | `GET /api/snipers/phase1/framing-types` |
| `executePhase2()` | ~499 | `POST /api/snipers/phase2` |
| `previewConversion()` | ~511 | `POST /api/snipers/phase2/preview` |
| `executePhase3WithPhase2()` | ~521 | `POST /api/snipers/phase3/with-phase2` |
| `getScorers()` | ~525 | `GET /api/snipers/phase3/scorers` |
| `executeFullAttack()` | ~531 | `POST /api/snipers/attack/full` |
| `executeAdaptiveAttack()` | ~537 | `POST /api/snipers/attack/adaptive` |

Also remove from exports:
- `scanService` object exports (lines ~457-459)
- `sniperService` object exports (lines ~777-788)

---

## Execution Order

### Step 1: Backend Cleanup
1. Delete HEAD endpoints from `scans.py`
2. Delete `list_framing_types` from `phase1.py`
3. Delete `execute_phase2` and `preview_conversion` from `phase2.py`
4. Delete `execute_phase3_with_phase2` and `list_scorers` from `phase3.py`
5. Delete `run_full_attack` and `run_adaptive_attack` from `attack.py`

### Step 2: Frontend Cleanup
1. Delete all 10 functions from `services.ts`
2. Remove deleted functions from export objects
3. Delete any related TypeScript types if orphaned

### Step 3: Verification
1. Run backend: `python -m services.api_gateway.main` - verify no import errors
2. Run frontend: `npm run build` - verify no TypeScript errors
3. Run tests if available

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Breaking existing functionality | **None** | All code verified as unused via grep |
| Import errors after deletion | **Low** | Functions are self-contained |
| Type errors in frontend | **Low** | Types may be orphaned but won't break build |

---

## Rollback Plan
If issues arise:
1. Git revert the cleanup commits
2. Commits should be atomic per-file for easy rollback

---

## Post-Cleanup Benefits
- Reduced code surface area
- Clearer API contract
- Easier maintenance
- Reduced confusion about which endpoints to use
