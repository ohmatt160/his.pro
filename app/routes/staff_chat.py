import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_
from sqlalchemy import inspect
from sqlalchemy.orm import Session, joinedload

from app.extensions import db_session, get_db
from app.models.staff_chat import ChatConversation, ChatMessage
from app.models.user import User
from app.schemas.staff_chat import (
    ChatConversationResponse,
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSenderResponse,
    ChatStaffResponse,
    ChatUnreadCountResponse,
    ChatUploadResponse,
    ConversationCreate,
)
from app.utils.dependencies import role_required
from app.utils.validators import Validators

router = APIRouter(prefix="/chat", tags=["staff-chat"])

CHAT_ROLES = ("ADMIN", "BRANCH_ADMIN", "DOCTOR", "NURSE", "RECEPTIONIST", "PHARMACIST", "LAB_TECH")
MAX_CHAT_FILE_SIZE = 10 * 1024 * 1024
ONLINE_WINDOW = timedelta(minutes=5)
ALLOWED_UPLOAD_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def _require_facility(current_user: User) -> str:
    if not current_user.facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return current_user.facility_slug


def _chat_upload_dir(facility_slug: str) -> Path:
    configured = os.getenv("CHAT_UPLOAD_DIR")
    base = Path(configured) if configured else Path(__file__).resolve().parents[1] / "private_uploads" / "chat"
    path = base / facility_slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def _chat_file_path(facility_slug: str, filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return _chat_upload_dir(facility_slug) / filename


def _full_name(user: User) -> str:
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username


def _is_online(user: User) -> bool:
    return bool(user.last_active and user.last_active >= datetime.utcnow() - ONLINE_WINDOW)


def _staff_response(user: User) -> ChatStaffResponse:
    return ChatStaffResponse(
        id=str(user.id),
        username=user.username,
        full_name=_full_name(user),
        role=user.role,
        department=user.department,
        is_online=_is_online(user),
        last_active=user.last_active.isoformat() if user.last_active else None,
    )


def _sender_response(user: User | None) -> ChatSenderResponse:
    if not user:
        return ChatSenderResponse(id="", username="Unknown", full_name="Unknown", role="")
    return ChatSenderResponse(
        id=str(user.id),
        username=user.username,
        full_name=_full_name(user),
        role=user.role,
    )


def _message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=str(message.id),
        conversation_id=str(message.conversation_id),
        facility_slug=message.facility_slug,
        sender_id=str(message.sender_id),
        sender=_sender_response(message.sender),
        content=message.content,
        message_type=message.message_type,
        file_name=message.file_name,
        file_url=message.file_url,
        file_size=message.file_size,
        file_type=message.file_type,
        is_read=message.is_read,
        read_at=message.read_at.isoformat() if message.read_at else None,
        created_at=message.created_at.isoformat() if message.created_at else "",
    )


def _participant_ids(conversation: ChatConversation) -> list[str]:
    return sorted(str(participant_id) for participant_id in conversation.participant_ids or [])


def _is_participant(conversation: ChatConversation, user_id: str) -> bool:
    return str(user_id) in _participant_ids(conversation)


def _other_participant_id(conversation: ChatConversation, current_user: User) -> str | None:
    return next((participant_id for participant_id in _participant_ids(conversation) if participant_id != str(current_user.id)), None)


def _get_conversation_for_user(conversation_id: str, current_user: User) -> ChatConversation:
    facility_slug = _require_facility(current_user)
    conversation = (
        db_session.query(ChatConversation)
        .filter_by(id=conversation_id, facility_slug=facility_slug)
        .first()
    )
    if not conversation or not _is_participant(conversation, str(current_user.id)):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def _conversation_response(conversation: ChatConversation, current_user: User) -> ChatConversationResponse:
    other_id = _other_participant_id(conversation, current_user)
    other = (
        db_session.query(User)
        .filter_by(id=other_id, facility_slug=current_user.facility_slug, is_active=True)
        .first()
        if other_id
        else None
    )
    last_message = (
        db_session.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter_by(conversation_id=conversation.id, facility_slug=current_user.facility_slug)
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    unread_count = (
        db_session.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.facility_slug == current_user.facility_slug,
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False,
        )
        .count()
    )

    return ChatConversationResponse(
        id=str(conversation.id),
        facility_slug=conversation.facility_slug,
        participant_ids=_participant_ids(conversation),
        other_staff=_staff_response(other) if other else ChatStaffResponse(
            id="",
            username="Unknown",
            full_name="Unknown staff",
            role="",
            is_online=False,
        ),
        last_message=_message_response(last_message) if last_message else None,
        unread_count=unread_count,
        last_message_at=conversation.last_message_at.isoformat() if conversation.last_message_at else None,
        created_at=conversation.created_at.isoformat() if conversation.created_at else "",
    )


def _magic_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"PK\x03\x04"):
        return "application/zip"
    if data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "application/ms-office"
    return None


def _validate_upload(file: UploadFile, data: bytes) -> tuple[str, str]:
    content_type = (file.content_type or "").lower()
    extension = ALLOWED_UPLOAD_TYPES.get(content_type)
    if not extension:
        raise HTTPException(status_code=400, detail="Unsupported chat attachment type")
    if not data:
        raise HTTPException(status_code=400, detail="Chat attachment is empty")
    if len(data) > MAX_CHAT_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Chat attachment must be 10 MB or smaller")

    magic_type = _magic_type(data)
    is_image = content_type in {"image/jpeg", "image/png"} and magic_type == content_type
    is_pdf = content_type == "application/pdf" and magic_type == "application/pdf"
    is_office = content_type in {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    } and magic_type in {"application/zip", "application/ms-office"}

    if not (is_image or is_pdf or is_office):
        raise HTTPException(status_code=400, detail="Attachment content does not match its file type")
    return content_type, extension


@router.get("/staff", response_model=list[ChatStaffResponse])
async def list_chat_staff(
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    staff = (
        db_session.query(User)
        .filter(
            User.facility_slug == facility_slug,
            User.id != current_user.id,
            User.is_active == True,
        )
        .all()
    )
    staff.sort(key=lambda user: (not _is_online(user), _full_name(user).lower()))
    return [_staff_response(user) for user in staff]


@router.get("/health")
async def chat_health(
    current_user: User = Depends(role_required("ADMIN", "BRANCH_ADMIN")),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    inspector = inspect(db.bind)
    tables = set(inspector.get_table_names())
    return {
        "ok": "chat_conversations" in tables and "chat_messages" in tables,
        "facility_slug": facility_slug,
        "tables": {
            "chat_conversations": "chat_conversations" in tables,
            "chat_messages": "chat_messages" in tables,
        },
    }


@router.post("/conversations", response_model=ChatConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_conversation(
    data: ConversationCreate,
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    if data.participant_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot start a conversation with yourself")

    participant = (
        db_session.query(User)
        .filter_by(id=data.participant_id, facility_slug=facility_slug, is_active=True)
        .first()
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Staff member not found")

    participants = sorted([str(current_user.id), str(participant.id)])
    existing = db_session.query(ChatConversation).filter_by(facility_slug=facility_slug).all()
    conversation = next((item for item in existing if _participant_ids(item) == participants), None)

    if not conversation:
        conversation = ChatConversation(
            facility_slug=facility_slug,
            participant_ids=participants,
            last_message_at=datetime.utcnow(),
        )
        db_session.add(conversation)
        db_session.commit()
        db_session.refresh(conversation)

    return _conversation_response(conversation, current_user)


@router.get("/conversations", response_model=list[ChatConversationResponse])
async def list_conversations(
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    facility_slug = _require_facility(current_user)
    conversations = [
        conversation
        for conversation in db_session.query(ChatConversation)
        .filter_by(facility_slug=facility_slug)
        .order_by(ChatConversation.last_message_at.desc())
        .all()
        if _is_participant(conversation, str(current_user.id))
    ]
    return [_conversation_response(conversation, current_user) for conversation in conversations]


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation_for_user(conversation_id, current_user)
    unread_messages = (
        db_session.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.facility_slug == current_user.facility_slug,
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False,
        )
        .all()
    )
    now = datetime.utcnow()
    for message in unread_messages:
        message.is_read = True
        message.read_at = now
    if unread_messages:
        db_session.commit()

    messages = (
        db_session.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .filter_by(conversation_id=conversation.id, facility_slug=current_user.facility_slug)
        .order_by(ChatMessage.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_message_response(message) for message in messages]


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    conversation_id: str,
    data: ChatMessageCreate,
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation_for_user(conversation_id, current_user)
    content = Validators.sanitize_string(data.content) if data.content else None
    if not content and not data.file_url:
        raise HTTPException(status_code=400, detail="Message content or file is required")
    if data.message_type == "text" and not content:
        raise HTTPException(status_code=400, detail="Text messages require content")

    message = ChatMessage(
        conversation_id=conversation.id,
        facility_slug=current_user.facility_slug,
        sender_id=current_user.id,
        content=content,
        message_type=data.message_type,
        file_name=Path(data.file_name).name if data.file_name else None,
        file_url=data.file_url,
        file_size=data.file_size,
        file_type=data.file_type,
        is_read=False,
    )
    conversation.last_message_at = datetime.utcnow()
    db_session.add(message)
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(message)
    return _message_response(message)


@router.post("/upload", response_model=ChatUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_chat_file(
    file: UploadFile = File(...),
    current_user: User = Depends(role_required(*CHAT_ROLES)),
):
    facility_slug = _require_facility(current_user)
    data = await file.read()
    content_type, extension = _validate_upload(file, data)
    filename = f"{secrets.token_urlsafe(24)}{extension}"
    _chat_file_path(facility_slug, filename).write_bytes(data)
    return ChatUploadResponse(
        file_url=f"/chat/files/{filename}",
        file_name=Path(file.filename or "attachment").name,
        file_size=len(data),
        file_type=content_type,
    )


@router.get("/files/{filename}")
async def download_chat_file(
    filename: str,
    current_user: User = Depends(role_required(*CHAT_ROLES)),
):
    facility_slug = _require_facility(current_user)
    path = _chat_file_path(facility_slug, filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@router.put("/conversations/{conversation_id}/read", response_model=ChatUnreadCountResponse)
async def mark_conversation_read(
    conversation_id: str,
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation_for_user(conversation_id, current_user)
    now = datetime.utcnow()
    unread_messages = (
        db_session.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.facility_slug == current_user.facility_slug,
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False,
        )
        .all()
    )
    for message in unread_messages:
        message.is_read = True
        message.read_at = now
    db_session.commit()
    return ChatUnreadCountResponse(unread_count=_total_unread(current_user))


def _total_unread(current_user: User) -> int:
    facility_slug = _require_facility(current_user)
    conversations = [
        conversation
        for conversation in db_session.query(ChatConversation).filter_by(facility_slug=facility_slug).all()
        if _is_participant(conversation, str(current_user.id))
    ]
    if not conversations:
        return 0
    conversation_ids = [conversation.id for conversation in conversations]
    return (
        db_session.query(ChatMessage)
        .filter(
            ChatMessage.facility_slug == facility_slug,
            ChatMessage.conversation_id.in_(conversation_ids),
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False,
        )
        .count()
    )


@router.get("/unread-count", response_model=ChatUnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    return ChatUnreadCountResponse(unread_count=_total_unread(current_user))
