import hashlib, json, os, re, secrets
from pathlib import Path
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, aliased
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from io import BytesIO
from .database import Base, engine, get_db
from .models import User, RegistryOffice, Person, LandParcel, Deed, MutationRecord, VerificationJob, AuditLog
from .schemas import LoginRequest, RegisterRequest, VerifyFields
from .security import hash_password, verify_password, create_token, decode_token
from .seed import seed

app = FastAPI(title="JomiCheck BD API", version="0.1.0", description="Synthetic-data land deed verification prototype. Not an official government service.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|[a-z0-9-]+\.netlify\.app)(:\d+)?$", allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./private_uploads")); UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "application/pdf"}

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    seed()

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401, "Authentication required")
    payload = decode_token(authorization[7:])
    if not payload: raise HTTPException(401, "Invalid or expired token")
    user = db.scalar(select(User).where(User.username == payload.get("sub")))
    if not user: raise HTTPException(401, "User not found")
    return {"username": user.username, "role": user.role}

def audit(db, actor, action, detail=""):
    db.add(AuditLog(actor=actor, action=action, detail=detail[:2000])); db.commit()

def deed_to_dict(d):
    return {"id": d.id, "deed_number": d.deed_number, "registration_date": d.registration_date, "registration_year": d.registration_year,
            "office": d.office.name_en, "seller_name": d.seller.name_en, "buyer_name": d.buyer.name_en,
            "mouza": d.parcel.mouza, "jl_number": d.parcel.jl_number, "khatian_number": d.parcel.khatian_number,
            "dag_number": d.parcel.dag_number, "area_decimal": d.parcel.area_decimal, "deed_type": d.deed_type, "label": "DEMO DATA"}

@app.get("/api/v1/health")
def health(): return {"status": "ok", "service": "JomiCheck BD API", "mode": "synthetic-demo"}

@app.post("/api/v1/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    if not user or not verify_password(data.password, user.password_hash): raise HTTPException(401, "Incorrect username or password")
    return {"access_token": create_token(user.username, user.role), "token_type": "bearer", "user": {"username": user.username, "role": user.role}}

@app.post("/api/v1/auth/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == data.username)): raise HTTPException(409, "Username already exists")
    allowed_roles = {"Citizen/General User", "Registry Officer", "Land Office Officer", "Court/Legal Reviewer", "Bank Verification Officer"}
    role = data.role if data.role in allowed_roles else "Citizen/General User"
    user = User(username=data.username, password_hash=hash_password(data.password), role=role)
    db.add(user); db.commit()
    return {"created": True, "username": user.username, "role": user.role}

@app.get("/api/v1/dashboard/stats")
def stats(db: Session = Depends(get_db), user=Depends(current_user)):
    total = db.scalar(select(func.count(Deed.id))) or 0
    jobs = db.scalar(select(func.count(VerificationJob.id))) or 0
    matched = db.scalar(select(func.count(VerificationJob.id)).where(VerificationJob.status == "MATCHED")) or 0
    mismatch = db.scalar(select(func.count(VerificationJob.id)).where(VerificationJob.status == "MISMATCH_FOUND")) or 0
    unverifiable = db.scalar(select(func.count(VerificationJob.id)).where(VerificationJob.status == "UNVERIFIABLE")) or 0
    recent = db.scalars(select(VerificationJob).order_by(VerificationJob.id.desc()).limit(6)).all()
    return {"demo_records": total, "verification_requests": jobs, "matched": matched, "mismatches": mismatch, "review_required": max(0, jobs-matched-mismatch-unverifiable), "unverifiable": unverifiable, "recent": [{"id":j.id,"filename":j.filename,"status":j.status,"deed_number":j.deed_number,"created_at":j.created_at.isoformat() if j.created_at else ""} for j in recent], "data_label":"SYNTHETIC DEMO DATA"}

@app.get("/api/v1/records/search")
def search_records(q: str = "", db: Session = Depends(get_db), user=Depends(current_user)):
    seller_alias = aliased(Person)
    buyer_alias = aliased(Person)
    stmt = select(Deed).join(Deed.parcel).join(seller_alias, Deed.seller_id == seller_alias.id).join(buyer_alias, Deed.buyer_id == buyer_alias.id).join(Deed.office)
    if q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(or_(Deed.deed_number.ilike(term), LandParcel.khatian_number.ilike(term), LandParcel.dag_number.ilike(term), LandParcel.mouza.ilike(term), seller_alias.name_en.ilike(term), buyer_alias.name_en.ilike(term)))
    deeds = db.scalars(stmt.order_by(Deed.id.desc()).limit(100)).unique().all()
    return {"items": [deed_to_dict(d) for d in deeds], "total": len(deeds), "label": "DEMO DATA — not official land records"}

@app.get("/api/v1/deeds/{deed_id}")
def get_deed(deed_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    d = db.get(Deed, deed_id)
    if not d: raise HTTPException(404, "Demo deed not found")
    return deed_to_dict(d)

@app.get("/api/v1/mutations")
def mutations(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.scalars(select(MutationRecord).order_by(MutationRecord.id.desc()).limit(100)).all()
    return {"items": [{"id":m.id,"deed_number":m.deed.deed_number,"mutation_ref":m.mutation_ref,"status":m.status,"note":m.note,"label":"SIMULATED DEMO"} for m in rows]}

@app.get("/api/v1/audit-logs")
def audit_logs(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)).all()
    return {"items": [{"id":x.id,"actor":x.actor,"action":x.action,"detail":x.detail,"created_at":x.created_at.isoformat() if x.created_at else ""} for x in rows]}

@app.post("/api/v1/verifications")
async def create_verification(file: UploadFile = File(...), fields_json: str = Form("{}"), ocr_text: str = Form(""), ocr_confidence: str = Form(""), db: Session = Depends(get_db), user=Depends(current_user)):
    if file.content_type not in ALLOWED: raise HTTPException(415, "Upload JPG, PNG, or PDF only")
    content = await file.read(MAX_UPLOAD + 1)
    if not content: raise HTTPException(400, "The uploaded file is empty")
    if len(content) > MAX_UPLOAD: raise HTTPException(413, f"File exceeds {MAX_UPLOAD // (1024*1024)} MB limit")
    # Basic signature checks prevent trusting the browser MIME type alone.
    valid_sig = (file.content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff")) or (file.content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n")) or (file.content_type == "application/pdf" and content.startswith(b"%PDF-"))
    if not valid_sig: raise HTTPException(415, "File contents do not match the selected file type")
    try: fields = VerifyFields.model_validate(json.loads(fields_json))
    except Exception: raise HTTPException(422, "Invalid verification fields")
    digest = hashlib.sha256(content).hexdigest()
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(file.filename or "document").name)[:150]
    stored = f"{secrets.token_hex(12)}_{safe_name}"
    (UPLOAD_DIR / stored).write_bytes(content)
    checks = []
    if ocr_text.strip():
        checks.append({"name":"OCR extraction","status":"OCR_READ","detail":f"The uploaded image was read in the browser before matching. Confidence: {ocr_confidence or 'not reported'}%"})
    candidates = []
    if fields.deed_number:
        candidates = db.scalars(select(Deed).where(Deed.deed_number == fields.deed_number)).all()
    if not candidates:
        status = "UNVERIFIABLE"
        checks.append({"name":"Reference record","status":"NOT_FOUND","detail":"No matching deed number exists in the synthetic demo database. This does not mean the document is fake."})
    else:
        d = candidates[0]
        pairs = [("registration_year", fields.registration_year, d.registration_year), ("seller_name", fields.seller_name, d.seller.name_en), ("buyer_name", fields.buyer_name, d.buyer.name_en), ("mouza", fields.mouza, d.parcel.mouza), ("jl_number", fields.jl_number, d.parcel.jl_number), ("khatian_number", fields.khatian_number, d.parcel.khatian_number), ("dag_number", fields.dag_number, d.parcel.dag_number), ("area_decimal", fields.area_decimal, d.parcel.area_decimal)]
        compared = 0; mismatches = []
        for name, given, expected in pairs:
            if given is None or given == "":
                checks.append({"name":name,"status":"NOT_CHECKED","detail":"No value supplied; OCR is not run automatically in this MVP."}); continue
            compared += 1
            ok = str(given).strip().casefold() == str(expected).strip().casefold()
            checks.append({"name":name,"status":"MATCH" if ok else "MISMATCH","submitted":str(given),"reference":str(expected)})
            if not ok: mismatches.append(name)
        if compared == 0:
            status = "REVIEW_REQUIRED"
            checks.append({"name":"Field comparison","status":"REVIEW_REQUIRED","detail":"A deed number was found, but no additional fields were supplied for comparison."})
        elif mismatches:
            status = "MISMATCH_FOUND"
        else:
            status = "MATCHED"
        checks.append({"name":"Reference source","status":"DEMO_ONLY","detail":"Matched against fictional records generated for this prototype; not an official registry."})
        mutation = db.scalar(select(MutationRecord).where(MutationRecord.deed_id == d.id))
        checks.append({"name":"Mutation record","status":"DEMO_RECORD_FOUND" if mutation else "NO_DEMO_RECORD","detail":mutation.mutation_ref if mutation else "No synthetic mutation record found; not evidence of legal status."})
    result = {"status":status,"checks":checks,"file_sha256":digest,"hash_check":"NOT_CHECKED","input_source":"OCR_IMAGE" if ocr_text.strip() else "MANUAL_FIELDS","ocr_text":ocr_text[:12000],"ocr_confidence":ocr_confidence,"biometric":{"status":"NOT_CHECKED","note":"No real biometric data is collected; live identity verification is not connected."},"legal_notice":"Prototype result only. It is not legal advice, an official record, or a determination of ownership.","submitted_fields":fields.model_dump()}
    job = VerificationJob(filename=safe_name, file_sha256=digest, status=status, deed_number=fields.deed_number, result_json=json.dumps(result, ensure_ascii=False), created_by=user["username"])
    db.add(job); db.commit(); db.refresh(job)
    audit(db, user["username"], "verification.created", f"job_id={job.id}; status={status}; filename={safe_name}")
    result.update({"id":job.id,"filename":safe_name,"created_at":job.created_at.isoformat() if job.created_at else ""})
    return result

@app.get("/api/v1/verifications/{verification_id}")
def get_verification(verification_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    job = db.get(VerificationJob, verification_id)
    if not job: raise HTTPException(404, "Verification request not found")
    data = json.loads(job.result_json); data.update({"id":job.id,"filename":job.filename,"status":job.status,"deed_number":job.deed_number,"file_sha256":job.file_sha256,"created_at":job.created_at.isoformat() if job.created_at else ""})
    return data

@app.get("/api/v1/verifications/{verification_id}/checks")
def get_checks(verification_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    job = db.get(VerificationJob, verification_id)
    if not job: raise HTTPException(404, "Verification request not found")
    return {"items": json.loads(job.result_json).get("checks", [])}

_REPORT_FONT_NAMES = None

def _report_fonts():
    """Register embedded Windows fonts so downloaded reports keep their visual identity."""
    global _REPORT_FONT_NAMES
    if _REPORT_FONT_NAMES:
        return _REPORT_FONT_NAMES
    font_paths = {
        "regular": Path(r"C:\Windows\Fonts\arial.ttf"),
        "bold": Path(r"C:\Windows\Fonts\arialbd.ttf"),
        "italic": Path(r"C:\Windows\Fonts\ariali.ttf"),
        "mono": Path(r"C:\Windows\Fonts\consola.ttf"),
    }
    if all(path.exists() for path in font_paths.values()):
        names = {"regular": "JomiReport-Regular", "bold": "JomiReport-Bold", "italic": "JomiReport-Italic", "mono": "JomiReport-Mono"}
        for key, name in names.items():
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(font_paths[key])))
        _REPORT_FONT_NAMES = names
    else:
        _REPORT_FONT_NAMES = {"regular": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique", "mono": "Courier"}
    return _REPORT_FONT_NAMES

def _report_status_style(status):
    palette = {
        "MATCHED": ("#166534", "#dcfce7"),
        "MATCH": ("#166534", "#dcfce7"),
        "MISMATCH_FOUND": ("#b91c1c", "#fee2e2"),
        "MISMATCH": ("#b91c1c", "#fee2e2"),
        "UNVERIFIABLE": ("#b91c1c", "#fee2e2"),
        "REVIEW_REQUIRED": ("#92400e", "#fef3c7"),
        "NOT_FOUND": ("#c2410c", "#ffedd5"),
        "OCR_READ": ("#475569", "#f1f5f9"),
        "NOT_CHECKED": ("#64748b", "#f1f5f9"),
        "DEMO_ONLY": ("#0369a1", "#e0f2fe"),
        "DEMO_RECORD_FOUND": ("#0369a1", "#e0f2fe"),
        "NO_DEMO_RECORD": ("#c2410c", "#ffedd5"),
    }
    text, fill = palette.get(str(status or "").upper(), ("#475569", "#f1f5f9"))
    return HexColor(text), HexColor(fill)

def _report_fit(text, font, size, max_width):
    value = str(text or "")
    if stringWidth(value, font, size) <= max_width:
        return value
    suffix = "..."
    while value and stringWidth(value + suffix, font, size) > max_width:
        value = value[:-1]
    return value.rstrip() + suffix

def _report_pill(pdf, text, right, top, fonts, min_width=0):
    value = str(text or "—").upper()
    text_color, fill_color = _report_status_style(value)
    font = fonts["bold"]
    size = 7.2
    width = max(min_width, stringWidth(value, font, size) + 18)
    height = 16
    pdf.setFillColor(fill_color)
    page_height = pdf._pagesize[1]
    pdf.roundRect(right - width, page_height - top - height, width, height, 8, fill=1, stroke=0)
    pdf.setFillColor(text_color)
    pdf.setFont(font, size)
    pdf.drawCentredString(right - width / 2, page_height - top - 11.2, value)

def _report_wrapped(pdf, text, x, top, max_width, fonts, font_key="regular", size=9.2, color="#475569", leading=12):
    font = fonts[font_key]
    lines = simpleSplit(str(text or ""), font, size, max_width) or [""]
    pdf.setFillColor(HexColor(color))
    pdf.setFont(font, size)
    for index, line in enumerate(lines):
        pdf.drawString(x, pdf._pagesize[1] - top - size - index * leading, line)
    return lines

def _report_check_title(name):
    key = str(name or "").strip().casefold()
    if "ocr" in key:
        return "OCR Extraction Status"
    if "reference record" in key:
        return "Registry Reference Record"
    if "reference source" in key:
        return "Registry Reference Source"
    if "mutation" in key:
        return "Mutation Record"
    if "field comparison" in key:
        return "Field Comparison"
    return str(name or "Verification Check").replace("_", " ").title()

def _report_check_detail(check):
    status = str(check.get("status") or "").upper()
    name = str(check.get("name") or "").casefold()
    detail = str(check.get("detail") or "").strip()
    if "ocr" in name:
        return "The uploaded image was read in the browser before matching."
    if status == "NOT_FOUND" or "reference record" in name:
        return "No matching deed number exists in the synthetic demo database. This outcome does not mean the physical document is counterfeit or fraudulent."
    if detail:
        return detail.replace("This does not mean the document is fake.", "This outcome does not mean the physical document is counterfeit or fraudulent.")
    submitted = check.get("submitted", "")
    reference = check.get("reference", "")
    if submitted or reference:
        return f"Submitted: {submitted or 'Not provided'}   •   Reference: {reference or 'Not provided'}"
    return "No additional diagnostic detail was provided."

def _report_check_height(check, fonts, width):
    if "ocr" in str(check.get("name") or "").casefold():
        return 84
    lines = simpleSplit(_report_check_detail(check), fonts["regular"], 9.2, width - 26) or [""]
    return max(55, 43 + len(lines) * 11)

def _report_check_card(pdf, check, x, top, width, fonts):
    height = _report_check_height(check, fonts, width)
    bottom = top + height
    pdf.setFillColor(white)
    pdf.setStrokeColor(HexColor("#e2e8f0"))
    pdf.setLineWidth(0.8)
    pdf.roundRect(x, pdf._pagesize[1] - bottom, width, height, 8, fill=1, stroke=1)

    title = _report_check_title(check.get("name"))
    status = str(check.get("status") or "NOT_CHECKED").upper()
    pdf.setFillColor(HexColor("#0f172a"))
    pdf.setFont(fonts["bold"], 9.8)
    pdf.drawString(x + 13, pdf._pagesize[1] - top - 17, title)
    _report_pill(pdf, status, x + width - 13, top + 7, fonts)

    if "ocr" in str(check.get("name") or "").casefold():
        _report_wrapped(pdf, _report_check_detail(check), x + 13, top + 28, width - 26, fonts, size=9.2, leading=11)
        raw_confidence = check.get("confidence") or ""
        if not raw_confidence:
            raw_confidence = re.search(r"confidence\s*:?\s*(\d+(?:\.\d+)?)", str(check.get("detail") or ""), flags=re.I)
            raw_confidence = raw_confidence.group(1) if raw_confidence else ""
        confidence = None
        try:
            confidence = max(0, min(100, float(raw_confidence))) if raw_confidence != "" else None
        except (TypeError, ValueError):
            confidence = None
        confidence_text = f"{confidence:.0f}%" if confidence is not None else "Not reported"
        confidence_label_x = x + 13
        confidence_top = top + 57
        pdf.setFillColor(HexColor("#64748b")); pdf.setFont(fonts["regular"], 8.5)
        pdf.drawString(confidence_label_x, pdf._pagesize[1] - confidence_top - 8.5, "Extraction Confidence:")
        label_width = stringWidth("Extraction Confidence:", fonts["regular"], 8.5)
        pdf.setFillColor(HexColor("#334155")); pdf.setFont(fonts["bold"], 8.5)
        pdf.drawString(confidence_label_x + label_width + 4, pdf._pagesize[1] - confidence_top - 8.5, confidence_text)
        value_width = stringWidth(confidence_text, fonts["bold"], 8.5)
        track_x = confidence_label_x + label_width + value_width + 18
        track_y = pdf._pagesize[1] - confidence_top - 7.5
        track_width = 42
        pdf.setFillColor(HexColor("#e2e8f0")); pdf.roundRect(track_x, track_y, track_width, 5, 2.5, fill=1, stroke=0)
        if confidence is not None:
            pdf.setFillColor(HexColor("#f59e0b" if confidence < 70 else "#16a34a"))
            pdf.roundRect(track_x, track_y, track_width * confidence / 100, 5, 2.5, fill=1, stroke=0)
            pdf.setFillColor(HexColor("#c2410c" if confidence < 70 else "#166534")); pdf.setFont(fonts["italic"], 8.2)
            pdf.drawString(track_x + track_width + 8, pdf._pagesize[1] - confidence_top - 8.5, "(Low Confidence)" if confidence < 70 else "(Good Confidence)")
        return height

    detail_lines = _report_wrapped(pdf, _report_check_detail(check), x + 13, top + 27, width - 26, fonts, size=9.2, leading=11)
    return height

def _report_footer(pdf, fonts, reference_id, page_number, total_pages):
    width, height = pdf._pagesize
    left, right = 51, width - 51
    pdf.setStrokeColor(HexColor("#e2e8f0")); pdf.setLineWidth(0.7)
    pdf.line(left, height - 786, right, height - 786)
    pdf.setFillColor(HexColor("#64748b")); pdf.setFont(fonts["regular"], 7.8)
    pdf.drawString(left, height - 802, f"JomiCheck BD • Verification Reference #{reference_id}")
    pdf.drawCentredString(width / 2 + 28, height - 802, "SYNTHETIC DEMO REPORT — NOT AN OFFICIAL DOCUMENT")
    pdf.drawRightString(right, height - 802, f"Page {page_number} of {total_pages}")

@app.get("/api/v1/verifications/{verification_id}/report")
def report(verification_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    job = db.get(VerificationJob, verification_id)
    if not job: raise HTTPException(404, "Verification request not found")
    result = json.loads(job.result_json)
    fonts = _report_fonts()
    buf = BytesIO(); pdf = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    pdf.setTitle("JomiCheck BD — Verification Report")
    pdf.setAuthor("JomiCheck BD")
    left, right = 51, width - 51
    content_width = right - left
    dark = HexColor("#0f172a")
    muted = HexColor("#64748b")
    slate = HexColor("#475569")

    # Header and report identity card.
    pdf.setFillColor(dark); pdf.setFont(fonts["bold"], 20)
    pdf.drawString(left, height - 67, "JomiCheck BD")
    pdf.setFillColor(muted); pdf.setFont(fonts["regular"], 10)
    pdf.drawString(left, height - 85, "Automated Deed & Record Verification System")
    pdf.setFillColor(dark); pdf.roundRect(right - 130, height - 81, 130, 21, 10, fill=1, stroke=0)
    pdf.setFillColor(white); pdf.setFont(fonts["bold"], 7.4)
    pdf.drawCentredString(right - 65, height - 73.5, "SYNTHETIC DEMO REPORT")
    pdf.setStrokeColor(dark); pdf.setLineWidth(1.2); pdf.line(left, height - 99, right, height - 99)

    pdf.setFillColor(white); pdf.setStrokeColor(HexColor("#e2e8f0")); pdf.setLineWidth(0.8)
    pdf.roundRect(left, height - 207, content_width, 96, 9, fill=1, stroke=1)
    col2 = left + content_width / 2 + 4
    for x, label, value, top in [
        (left + 13, "REPORT ID", f"# {job.id}", 124),
        (col2, "OVERALL STATUS", str(job.status or "UNVERIFIABLE").replace("_", " "), 124),
        (left + 13, "FILENAME", _report_fit(job.filename, fonts["bold"], 10.5, content_width / 2 - 37), 166),
        (col2, "DEED NUMBER", job.deed_number or "Not provided", 166),
    ]:
        pdf.setFillColor(muted); pdf.setFont(fonts["bold"], 8.1); pdf.drawString(x, height - top - 8, label)
        if label == "OVERALL STATUS":
            _report_pill(pdf, value, x + content_width / 2 - 17, top + 27, fonts, min_width=92)
        else:
            pdf.setFillColor(dark if value != "Not provided" else muted)
            pdf.setFont(fonts["bold"] if value != "Not provided" else fonts["italic"], 10.5)
            pdf.drawString(x, height - top - 27, value)

    pdf.setFillColor(white); pdf.setStrokeColor(HexColor("#e2e8f0")); pdf.setLineWidth(0.8)
    pdf.roundRect(left, height - 263, content_width, 43, 8, fill=1, stroke=1)
    pdf.setFillColor(slate); pdf.setFont(fonts["bold"], 7.8)
    pdf.drawString(left + 13, height - 232, "DOCUMENT SHA-256 FINGERPRINT")
    pdf.setFillColor(dark); pdf.setFont(fonts["mono"], 8.5)
    pdf.drawString(left + 13, height - 248, _report_fit(job.file_sha256, fonts["mono"], 8.5, content_width - 26))

    # Diagnostics heading.
    pdf.setStrokeColor(HexColor("#94a3b8")); pdf.setLineWidth(0.8)
    pdf.roundRect(left + 1, height - 282, 10, 10, 2, fill=0, stroke=1)
    pdf.setStrokeColor(HexColor("#2563eb")); pdf.setLineWidth(1.1)
    pdf.line(left + 3.5, height - 277, left + 5.5, height - 279); pdf.line(left + 5.5, height - 279, left + 8.5, height - 274.5)
    pdf.setFillColor(dark); pdf.setFont(fonts["bold"], 12)
    pdf.drawString(left + 17, height - 281, "Verification Checks & Diagnostics")

    checks = result.get("checks", []) or []
    # Keep the reference layout order stable: OCR first, registry reference second, then field diagnostics.
    checks = sorted(checks, key=lambda item: (0 if "ocr" in str(item.get("name") or "").casefold() else 1 if "reference record" in str(item.get("name") or "").casefold() else 2))
    legal_text = "A field match is not proof of legal authenticity or ownership. Always verify through authorized official land registry channels."
    legal_lines = simpleSplit(legal_text, fonts["bold"], 8.8, content_width - 39) or [legal_text]
    legal_height = max(50, 27 + len(legal_lines) * 11)
    planned_pages = 1
    planned_cursor = 294
    for check in checks:
        block_height = _report_check_height(check, fonts, content_width)
        if planned_cursor + block_height > 724:
            planned_pages += 1
            planned_cursor = 86
        planned_cursor += block_height + 5
    if max(457, planned_cursor + 9) + legal_height > 769:
        planned_pages += 1

    cursor = 294
    page_number = 1
    total_pages = planned_pages
    for check in checks:
        block_height = _report_check_height(check, fonts, content_width)
        if cursor + block_height > 724:
            _report_footer(pdf, fonts, job.id, page_number, total_pages)
            pdf.showPage(); page_number += 1; cursor = 82
            pdf.setFillColor(dark); pdf.setFont(fonts["bold"], 12)
            pdf.drawString(left, height - 62, "Verification Checks & Diagnostics (continued)")
            cursor = 86
        _report_check_card(pdf, check, left, cursor, content_width, fonts)
        cursor += block_height + 5

    # Put the limitation notice directly below the diagnostics, retaining the reference position for the normal two-card report.
    legal_top = max(457, cursor + 9)
    if legal_top + legal_height > 769:
        _report_footer(pdf, fonts, job.id, page_number, total_pages)
        pdf.showPage(); page_number += 1; legal_top = 58
    pdf.setFillColor(white); pdf.setStrokeColor(HexColor("#fecaca")); pdf.setLineWidth(0.8)
    pdf.roundRect(left, height - legal_top - legal_height, content_width, legal_height, 7, fill=1, stroke=1)
    pdf.setFillColor(HexColor("#dc2626")); pdf.roundRect(left, height - legal_top - legal_height, 4, legal_height, 2, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#991b1b")); pdf.setFont(fonts["bold"], 8.8)
    for index, line in enumerate(legal_lines):
        pdf.drawString(left + 15, height - legal_top - 16 - index * 11, line)

    # Footer is intentionally fixed to the same low-contrast position as the supplied one-page reference.
    _report_footer(pdf, fonts, job.id, page_number, total_pages)
    pdf.save(); buf.seek(0)
    audit(db, user["username"], "report.downloaded", f"verification_id={job.id}")
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="jomicheck-bd-verification-report-{job.id}.pdf"'})

@app.get("/api/v1/verifications")
def list_verifications(db: Session = Depends(get_db), user=Depends(current_user)):
    rows = db.scalars(select(VerificationJob).order_by(VerificationJob.id.desc()).limit(100)).all()
    return {"items":[{"id":r.id,"filename":r.filename,"status":r.status,"deed_number":r.deed_number,"created_at":r.created_at.isoformat() if r.created_at else ""} for r in rows]}
