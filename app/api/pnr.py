from fastapi import APIRouter, HTTPException
from app.models.schemas import PNRResponse, PNRRequest
from app.services.pnr_fetcher import get_pnr_info
from app.ml.predictor import predict_confirmation
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/check", response_model=PNRResponse)
async def check_pnr(request: PNRRequest):
    """
    Main endpoint: fetch PNR info + return AI prediction.
    POST /api/pnr/check
    Body: { "pnr": "1234567890" }
    """
    try:
        # 1. Fetch PNR data (real API only — no simulation for real users)
        train_info, is_real = await get_pnr_info(request.pnr)
        logger.info(f"PNR {request.pnr} fetched — real={is_real}")

        # 2. If not real data, return a clear error — don't show fake data
        if not is_real:
            return PNRResponse(
                success=False,
                error="PNR not found. This PNR may be invalid, expired (flushed by IRCTC after 3 months), or the railway API is temporarily unavailable. Please check your PNR number and try again."
            )

        # 3. Run prediction on first passenger's status
        passenger = train_info.passengers[0] if train_info.passengers else None
        if not passenger:
            raise HTTPException(status_code=404, detail="No passenger data found")

        # 4. If chart is prepared, status is final — no prediction needed
        if train_info.chart_prepared:
            return PNRResponse(
                success=True,
                train_info=train_info,
                prediction=None,
            )

        # 5. Check if ticket is cancelled or RAC
        current = passenger.current_status.upper()
        if current.startswith("CAN"):
            return PNRResponse(
                success=True,
                train_info=train_info,
                prediction=None,
            )

        # RAC + chart not prepared = can still predict full berth confirmation
        # RAC + chart prepared = handled above already

        prediction = predict_confirmation(
            pnr=request.pnr,
            class_code=train_info.class_code,
            quota=train_info.quota,
            current_status=passenger.current_status,
            journey_date_str=train_info.journey_date,
        )

        return PNRResponse(
            success=True,
            train_info=train_info,
            prediction=prediction,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PNR {request.pnr}: {e}")
        return PNRResponse(
            success=False,
            error=f"Could not process PNR. Please try again. ({str(e)})"
        )

@router.get("/check/{pnr}", response_model=PNRResponse)
async def check_pnr_get(pnr: str):
    """GET version for easy browser testing."""
    if not pnr.isdigit() or len(pnr) != 10:
        raise HTTPException(status_code=400, detail="PNR must be exactly 10 digits")
    return await check_pnr(PNRRequest(pnr=pnr))