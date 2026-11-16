import io
import uuid
from datetime import date

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agent.graph import analyze_claim
from db.mongo import db
from models.schemas import AnalysisResult, ClaimOut, ClaimUploadError, ClaimUploadResponse

router = APIRouter(prefix="/claims", tags=["claims"])

REQUIRED_UPLOAD_COLUMNS = [
    "provider_id",
    "procedure_code",
    "diagnosis_code",
    "treatment_type",
    "billed_amount",
    "age",
]


def _clean_str(value) -> str:
    """Stringify a CSV cell, treating pandas NaN/None as an empty string.

    Plain `value or ""` doesn't work here: pandas parses blank cells as the
    float NaN, and NaN is truthy in Python, so `NaN or ""` evaluates to NaN
    (not "") and str(NaN) becomes the literal text "nan".
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


@router.get("", response_model=list[ClaimOut])
async def list_claims(limit: int = 50, status: str | None = None):
    query = {"status": status} if status else {}
    cursor = db["claims"].find(query, {"_id": 0}).limit(limit)
    return await cursor.to_list(length=limit)


@router.get("/{claim_id}", response_model=ClaimOut)
async def get_claim(claim_id: str):
    claim = await db["claims"].find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.post("/{claim_id}/analyze", response_model=AnalysisResult)
async def analyze(claim_id: str):
    claim = await db["claims"].find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return await analyze_claim(claim_id)


@router.get("/{claim_id}/analysis", response_model=AnalysisResult)
async def get_analysis(claim_id: str):
    analysis = await db["claim_analyses"].find_one({"claim_id": claim_id}, {"_id": 0})
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this claim yet")
    return analysis


@router.post("/upload", response_model=ClaimUploadResponse)
async def upload_claims(file: UploadFile = File(...), auto_analyze: bool = Form(False)):
    """Bulk-ingest one or many claims from a CSV file.

    Required columns: provider_id, procedure_code, diagnosis_code, treatment_type,
    billed_amount, age (used to create a lightweight patient record for the claim).
    Optional columns: claim_id, patient_id, paid_amount, claim_date, length_of_stay,
    prior_claims_count, status. Unrecognized provider_ids are rejected per-row so the
    rest of the batch still succeeds.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw = await file.read()
    try:
        rows = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001 - surface parse errors to the caller
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}") from exc

    if rows.empty:
        raise HTTPException(status_code=400, detail="CSV file has no rows")

    missing = [col for col in REQUIRED_UPLOAD_COLUMNS if col not in rows.columns]
    if missing:
        raise HTTPException(
            status_code=400, detail=f"CSV is missing required column(s): {', '.join(missing)}"
        )

    provider_ids = {
        doc["provider_id"] async for doc in db["providers"].find({}, {"provider_id": 1})
    }
    existing_claim_ids = {
        doc["claim_id"] async for doc in db["claims"].find({}, {"claim_id": 1})
    }

    claims_to_insert: list[dict] = []
    patients_to_insert: list[dict] = []
    errors: list[ClaimUploadError] = []
    inserted_claim_ids: list[str] = []

    for idx, row in rows.iterrows():
        row_num = idx + 2  # +1 for header row, +1 for 0-index -> 1-index

        provider_id = _clean_str(row.get("provider_id"))
        if provider_id not in provider_ids:
            errors.append(ClaimUploadError(row=row_num, reason=f"Unknown provider_id '{provider_id}'"))
            continue

        try:
            billed_amount = float(row["billed_amount"])
            age = int(row["age"])
        except (TypeError, ValueError):
            errors.append(ClaimUploadError(row=row_num, reason="billed_amount/age must be numeric"))
            continue

        procedure_code = _clean_str(row.get("procedure_code"))
        diagnosis_code = _clean_str(row.get("diagnosis_code"))
        treatment_type = _clean_str(row.get("treatment_type"))
        if not (procedure_code and diagnosis_code and treatment_type):
            errors.append(
                ClaimUploadError(row=row_num, reason="procedure_code/diagnosis_code/treatment_type required")
            )
            continue

        claim_id = _clean_str(row.get("claim_id"))
        if not claim_id or claim_id in existing_claim_ids:
            claim_id = f"CLM-UP-{uuid.uuid4().hex[:8]}"
        existing_claim_ids.add(claim_id)

        patient_id = _clean_str(row.get("patient_id"))
        if not patient_id:
            patient_id = f"PAT-UP-{uuid.uuid4().hex[:8]}"
            patients_to_insert.append({
                "patient_id": patient_id,
                "name": "Uploaded Patient",
                "age": age,
                "gender": "Other",
                "chronic_conditions": 0,
            })

        paid_amount = row.get("paid_amount")
        length_of_stay = row.get("length_of_stay")
        prior_claims_count = row.get("prior_claims_count")
        status = _clean_str(row.get("status")) or "Pending"
        claim_date = _clean_str(row.get("claim_date")) or str(date.today())

        claims_to_insert.append({
            "claim_id": claim_id,
            "provider_id": provider_id,
            "patient_id": patient_id,
            "procedure_code": procedure_code,
            "diagnosis_code": diagnosis_code,
            "treatment_type": treatment_type,
            "billed_amount": round(billed_amount, 2),
            "paid_amount": round(float(paid_amount), 2) if pd.notna(paid_amount) else 0.0,
            "claim_date": claim_date,
            "length_of_stay": int(length_of_stay) if pd.notna(length_of_stay) else 0,
            "prior_claims_count": int(prior_claims_count) if pd.notna(prior_claims_count) else 0,
            "status": status,
            "risk_label": "Unlabeled",
        })
        inserted_claim_ids.append(claim_id)

    if patients_to_insert:
        await db["patients"].insert_many(patients_to_insert)
    if claims_to_insert:
        await db["claims"].insert_many(claims_to_insert)

    analyses: list[AnalysisResult] | None = None
    analysis_errors: list[ClaimUploadError] | None = None
    if auto_analyze and inserted_claim_ids:
        analyses, analysis_errors = [], []
        for claim_id in inserted_claim_ids:
            try:
                analyses.append(await analyze_claim(claim_id))
            except Exception as exc:  # noqa: BLE001 - one bad claim shouldn't kill the batch
                analysis_errors.append(ClaimUploadError(row=0, reason=f"{claim_id}: {exc}"))

    return ClaimUploadResponse(
        inserted_count=len(inserted_claim_ids),
        claim_ids=inserted_claim_ids,
        errors=errors,
        analyses=analyses,
        analysis_errors=analysis_errors,
    )
