from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import Response
from sqlmodel import Session
from app.database import get_session
from app.models import SentEmail

router = APIRouter()

@router.get("/track_open")
def track_open(email_id: int, session: Session = Depends(get_session)):
    email = session.get(SentEmail, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    if email.status == "sent":
        email.status = "opened"
        session.add(email)
        session.commit()

    # Transparent 1x1 GIF
    pixel = b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"
    return Response(content=pixel, media_type="image/gif")

