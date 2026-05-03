import httpx
import random
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from app.models.schemas import TrainInfo, PassengerInfo

RAPIDAPI_KEY  = "8061acae1emsh75d73888d4c28f7p1c2d83jsn97431589cd3a"

# Primary API (irctc27) - POST
API1_HOST = "irctc27.p.rapidapi.com"
API1_URL  = "https://irctc27.p.rapidapi.com/pnr-status.php"

# Secondary API (irctc-indian-railway-pnr-status) - GET
API2_HOST = "irctc-indian-railway-pnr-status.p.rapidapi.com"
API2_URL  = "https://irctc-indian-railway-pnr-status.p.rapidapi.com/getPNRStatus"

TIMEOUT = 10.0

TRAIN_DATA = [
    {"num": "12951", "name": "Mumbai Rajdhani", "from": "NDLS", "from_n": "New Delhi", "to": "BCT", "to_n": "Mumbai Central", "dep": "16:00", "arr": "08:35+1", "dur": "16h 35m", "cls": "SL"},
    {"num": "12301", "name": "Howrah Rajdhani", "from": "NDLS", "from_n": "New Delhi", "to": "HWH", "to_n": "Howrah Jn", "dep": "16:55", "arr": "09:55+1", "dur": "17h 00m", "cls": "3A"},
    {"num": "12009", "name": "Shatabdi Express", "from": "BCT", "from_n": "Mumbai Central", "to": "ADI", "to_n": "Ahmedabad Jn", "dep": "06:25", "arr": "12:55", "dur": "6h 30m", "cls": "CC"},
    {"num": "12213", "name": "Duronto Express", "from": "HWH", "from_n": "Howrah Jn", "to": "PUNE", "to_n": "Pune Jn", "dep": "20:10", "arr": "23:45+1", "dur": "27h 35m", "cls": "3A"},
    {"num": "12621", "name": "Tamil Nadu Express", "from": "NDLS", "from_n": "New Delhi", "to": "MAS", "to_n": "Chennai Central", "dep": "22:30", "arr": "07:40+2", "dur": "33h 10m", "cls": "SL"},
]
NAMES  = ["Rahul Sharma", "Priya Mehta", "Amit Das", "Sneha Patel", "Vikram Singh", "Kavya Nair"]
QUOTAS = ["General (GN)", "General (GN)", "General (GN)", "Ladies (LD)", "Senior Citizen (SC)", "Tatkal (TQ)"]

TRAIN_TIMINGS = {
    "12723": {"dep": "16:45", "arr": "10:30+1", "dur": "17h 45m"},
    "12724": {"dep": "06:20", "arr": "09:45+1", "dur": "27h 25m"},
    "12951": {"dep": "16:00", "arr": "08:35+1", "dur": "16h 35m"},
    "12301": {"dep": "16:55", "arr": "09:55+1", "dur": "17h 00m"},
    "12621": {"dep": "22:30", "arr": "07:40+2", "dur": "33h 10m"},
    "12009": {"dep": "06:25", "arr": "12:55",   "dur": "6h 30m"},
    "12213": {"dep": "20:10", "arr": "23:45+1", "dur": "27h 35m"},
}

# Common station code -> full name lookup
STATION_NAMES = {
    "NDLS": "New Delhi", "BCT": "Mumbai Central", "HWH": "Howrah Jn",
    "MAS": "Chennai Central", "SBC": "KSR Bengaluru", "PUNE": "Pune Jn",
    "ADI": "Ahmedabad Jn", "HYB": "Hyderabad Deccan", "SC": "Secunderabad",
    "BZA": "Vijayawada", "GNT": "Guntur", "VSKP": "Visakhapatnam",
    "NGP": "Nagpur", "BPL": "Bhopal", "ALD": "Prayagraj",
    "LKO": "Lucknow", "CNB": "Kanpur Central", "AGC": "Agra Cantt",
    "JP": "Jaipur", "UDZ": "Udaipur", "JU": "Jodhpur",
    "AMD": "Ahmedabad", "BRC": "Vadodara", "ST": "Surat",
    "PNBE": "Patna Jn", "GAYA": "Gaya Jn", "DHN": "Dhanbad",
    "RNC": "Ranchi", "BSP": "Bilaspur", "R": "Raipur",
    "KGP": "Kharagpur", "BBS": "Bhubaneswar", "VSKP": "Visakhapatnam",
    "GWL": "Gwalior", "JHS": "Jhansi", "KOTA": "Kota Jn",
    "NZM": "Hazrat Nizamuddin", "DLI": "Old Delhi", "DSA": "Delhi Sarai Rohilla",
}

def station_name(code: str) -> str:
    return STATION_NAMES.get(code.upper(), code)


def fmt_date(date_str: str) -> str:
    """Parse any common date format and return DD Mon YYYY."""
    for fmt in (
        "%d-%m-%Y",           # 26-04-2026
        "%Y-%m-%d",           # 2026-04-26
        "%d/%m/%Y",           # 26/04/2026
        "%d %b %Y",           # 26 Apr 2026
        "%b %d, %Y %I:%M:%S %p",  # Apr 26, 2026 6:00:00 AM
        "%b %d, %Y",          # Apr 26, 2026
    ):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%d %b %Y")
        except:
            pass
    return date_str

async def fetch_api1(pnr: str) -> Optional[dict]:
    """Try API1 (irctc27) - POST with form data."""
    try:
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": API1_HOST,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(API1_URL, headers=headers, data={"pnr": pnr})
            print(f"[API1] Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                # Check if it's a quota error
                if "exceeded" in str(data).lower() or "quota" in str(data).lower():
                    print("[API1] Quota exceeded, trying API2...")
                    return None
                return data
    except Exception as e:
        print(f"[API1] Error: {e}")
    return None

async def fetch_api2(pnr: str) -> Optional[dict]:
    """Try API2 (irctc-indian-railway-pnr-status) - GET with PNR in URL."""
    try:
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": API2_HOST,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{API2_URL}/{pnr}", headers=headers)
            print(f"[API2] Status: {resp.status_code}")
            print(f"[API2] Body: {resp.text[:600]}")
            if resp.status_code == 200:
                data = resp.json()
                # Only flag quota error if top-level message says exceeded
                top_msg = str(data.get("message", "")).lower()
                if "exceeded" in top_msg or (data.get("success") is False and "exceeded" in str(data).lower()):
                    print("[API2] Quota exceeded.")
                    return None
                # Validate response has actual train data — flushed PNRs return empty fields
                inner = data.get("data") or {}
                train_num = str(inner.get("trainNumber") or inner.get("trainNo") or "").strip()
                train_name = str(inner.get("trainName") or "").strip()
                if not train_num or train_num in ["0", "00000"] or not train_name:
                    print("[API2] Empty response — PNR is flushed, invalid or not found")
                    return None
                return data
    except Exception as e:
        print(f"[API2] Error: {e}")
    return None

def parse_api1_response(raw: dict, pnr: str) -> TrainInfo:
    data = raw.get("data", raw)
    d    = data.get("pnrResponse", data)
    return _build_train_info(pnr, d,
        train_num  = d.get("trainNo"),
        train_name = d.get("trainName"),
        from_code  = d.get("boardingPoint") or d.get("from"),
        from_name  = d.get("boardingStationName"),
        to_code    = d.get("reservationUpto") or d.get("to"),
        to_name    = d.get("reservationUptoName"),
        doj        = d.get("doj") or d.get("sourceDoj"),
        cls        = d.get("class"),
        quota      = d.get("quota"),
        booked_on  = d.get("bookingDate"),
        pax_list   = d.get("passengerStatus") or [],
        pax_name_key    = "passengerName",
        pax_age_key     = "passengerAge",
        pax_gender_key  = "passengerGender",
        pax_booking_key = "bookingStatusDetails",
        pax_current_key = "currentStatusDetails",
        pax_coach_key   = "coach",
        pax_berth_key   = "berth",
    )

def parse_api2_response(raw: dict, pnr: str) -> TrainInfo:
    # API2 structure: raw -> data -> passenger details
    outer = raw.get("data") or raw
    d = outer if isinstance(outer, dict) else raw
    pax_list = d.get("passengerList") or d.get("passengerStatus") or []
    # Extract quota from first passenger if not at top level
    top_quota = d.get("quota")
    if not top_quota and pax_list:
        top_quota = pax_list[0].get("passengerQuota")
    return _build_train_info(pnr, d,
        train_num  = d.get("trainNumber") or d.get("trainNo"),
        train_name = d.get("trainName"),
        from_code  = d.get("boardingPoint") or d.get("sourceStation") or d.get("from"),
        from_name  = d.get("sourceStationName") or d.get("boardingStationName") or d.get("boardingPoint"),
        to_code    = d.get("reservationUpto") or d.get("destinationStation") or d.get("to"),
        to_name    = d.get("destinationStationName") or d.get("reservationUptoName") or d.get("destinationStation"),
        doj        = d.get("dateOfJourney") or d.get("doj"),
        cls        = d.get("journeyClass") or d.get("class"),
        quota      = top_quota,
        booked_on  = d.get("bookingDate"),
        pax_list   = pax_list,
        pax_name_key    = "passengerName",
        pax_age_key     = "passengerAge",
        pax_gender_key  = "passengerGender",
        pax_booking_key = "bookingStatusDetails",
        pax_current_key = "currentStatusDetails",
        pax_coach_key   = "coachNumber",
        pax_berth_key   = "seatNumber",
    )

def _build_train_info(pnr, d, train_num, train_name, from_code, from_name,
                      to_code, to_name, doj, cls, quota, booked_on,
                      pax_list, pax_name_key, pax_age_key, pax_gender_key,
                      pax_booking_key, pax_current_key, pax_coach_key, pax_berth_key) -> TrainInfo:

    train_num  = str(train_num  or "00000")
    train_name = str(train_name or "Unknown Train").title()
    from_code  = str(from_code  or "???")
    from_name  = str(from_name  or from_code)
    to_code    = str(to_code    or "???")
    to_name    = str(to_name    or to_code)
    doj        = fmt_date(str(doj      or ""))
    cls        = str(cls        or "SL")
    # Handle both "DD-MM-YYYY" and "Apr 25, 2026 10:04:00 AM" booking date formats
    booked_raw = str(booked_on or "")
    booked_on_fmt = booked_raw
    for _fmt in ("%b %d, %Y %I:%M:%S %p", "%b %d, %Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            from datetime import datetime as _dt2
            booked_on_fmt = _dt2.strptime(booked_raw.strip(), _fmt).strftime("%d %b %Y")
            break
        except:
            pass

    quota_raw  = str(quota or "GN")
    quota_map  = {"GN":"General (GN)","TQ":"Tatkal (TQ)","LD":"Ladies (LD)","SC":"Senior Citizen (SC)","CK":"Tatkal (CK)","DF":"Defence (DF)"}
    quota_disp = quota_map.get(quota_raw, quota_raw)

    # Extract departure time from dateOfJourney if API doesn't provide it separately
    # e.g. "Apr 26, 2026 6:00:00 AM" -> "06:00"
    timing = TRAIN_TIMINGS.get(train_num, {})
    dep_from_doj = ""
    try:
        from datetime import datetime as _dt
        _parsed = _dt.strptime(str(d.get("dateOfJourney") or "").strip(), "%b %d, %Y %I:%M:%S %p")
        dep_from_doj = _parsed.strftime("%H:%M")
    except:
        pass
    dep = str(d.get("departureTime") or d.get("dep_time") or d.get("fromTime") or dep_from_doj or timing.get("dep", "—"))
    arr = str(d.get("arrivalTime")   or d.get("arr_time") or d.get("toTime")   or timing.get("arr", "—"))
    dur = str(d.get("duration")      or timing.get("dur", "N/A"))
    # Chart status
    chart_raw = d.get("chartStatus") or d.get("chartPrepared") or ""
    chart_prepared = str(chart_raw).lower() not in ["false", "chart not prepared", "", "none"]
    chart_label = "Chart Prepared" if chart_prepared else "Chart Not Prepared"

    passengers = []
    for i, p in enumerate(pax_list, start=1):
        name    = str(p.get(pax_name_key)    or f"Passenger {i}")
        age     = p.get(pax_age_key)          or 0
        gender  = str(p.get(pax_gender_key)  or "—")
        booking = str(p.get(pax_booking_key) or p.get("bookingStatus") or "WL/1").strip()
        current = str(p.get(pax_current_key) or p.get("currentStatus") or booking).strip()
        coach   = str(p.get(pax_coach_key)   or "").strip()
        berth   = str(p.get(pax_berth_key)   or "").strip()

        if coach and berth:
            current = f"{current} — {coach} / Berth {berth}"

        passengers.append(PassengerInfo(
            name=name, age=int(str(age) or 0),
            gender=gender, booking_status=booking, current_status=current,
        ))

    if not passengers:
        passengers = [PassengerInfo(name="Passenger 1", age=0, gender="—",
                                    booking_status="—", current_status="—")]

    print(f"[Parser] {train_num} {train_name} | {from_code}→{to_code} | {doj} | {len(passengers)} pax | chart={chart_label}")
    return TrainInfo(
        pnr=pnr, train_number=train_num, train_name=train_name,
        from_station=from_code, from_station_name=from_name,
        to_station=to_code,     to_station_name=to_name,
        departure_time=dep,     arrival_time=arr,
        journey_date=doj,       duration=dur,
        class_code=cls,         quota=quota_disp,
        booked_on=booked_on_fmt, passengers=passengers,
        chart_prepared=chart_prepared,
    )

def simulate_pnr_data(pnr: str) -> TrainInfo:
    seed  = int(hashlib.md5(pnr.encode()).hexdigest(), 16) % (2**32)
    rng   = random.Random(seed)
    train = rng.choice(TRAIN_DATA)
    wl    = rng.randint(1, 45)
    doj   = (datetime.now() + timedelta(days=rng.randint(3, 20))).strftime("%d %b %Y")
    booked= (datetime.now() - timedelta(days=rng.randint(5, 30))).strftime("%d %b %Y")
    return TrainInfo(
        pnr=pnr, train_number=train["num"], train_name=train["name"],
        from_station=train["from"], from_station_name=train["from_n"],
        to_station=train["to"],     to_station_name=train["to_n"],
        departure_time=train["dep"],arrival_time=train["arr"],
        journey_date=doj,           duration=train["dur"],
        class_code=train["cls"],    quota=rng.choice(QUOTAS),
        booked_on=booked,
        passengers=[PassengerInfo(
            name=rng.choice(NAMES), age=rng.randint(18, 65),
            gender=rng.choice(["Male", "Female"]),
            booking_status=f"WL/{wl}", current_status=f"WL/{wl}",
        )]
    )

async def get_pnr_info(pnr: str) -> tuple[TrainInfo, bool]:
    # Try API1 first, then API2, then simulate
    raw = await fetch_api1(pnr)
    if raw:
        try:
            return parse_api1_response(raw, pnr), True
        except Exception as e:
            print(f"[API1 Parser] Error: {e}")

    raw = await fetch_api2(pnr)
    if raw:
        try:
            return parse_api2_response(raw, pnr), True
        except Exception as e:
            print(f"[API2 Parser] Error: {e}")

    print("[Fallback] Using simulated data")
    return simulate_pnr_data(pnr), False