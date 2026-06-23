import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, func, or_
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


def _participant_key(participant_ids: Iterable[str]) -> str:
    return ":".join(sorted(str(participant_id) for participant_id in participant_ids))


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


def _conversation_response(
    conversation: ChatConversation,
    current_user: User,
    *,
    other: User | None = None,
    last_message: ChatMessage | None = None,
    unread_count: int | None = None,
    preloaded: bool = False,
) -> ChatConversationResponse:
    other_id = _other_participant_id(conversation, current_user)
    if not preloaded and other is None and other_id:
        other = (
            db_session.query(User)
            .filter_by(id=other_id, facility_slug=current_user.facility_slug, is_active=True)
            .first()
        )
    if not preloaded and last_message is None:
        last_message = (
            db_session.query(ChatMessage)
            .options(joinedload(ChatMessage.sender))
            .filter_by(conversation_id=conversation.id, facility_slug=current_user.facility_slug)
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
    if not preloaded and unread_count is None:
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
    participant_key = _participant_key(participants)
    conversation = (
        db_session.query(ChatConversation)
        .filter_by(facility_slug=facility_slug, participant_key=participant_key)
        .first()
    )
    if not conversation:
        legacy_conversations = (
            db_session.query(ChatConversation)
            .filter_by(facility_slug=facility_slug, participant_key=None)
            .all()
        )
        conversation = next(
            (item for item in legacy_conversations if _participant_ids(item) == participants),
            None,
        )
        if conversation:
            conversation.participant_key = participant_key
            db_session.commit()

    if not conversation:
        conversation = ChatConversation(
            facility_slug=facility_slug,
            participant_ids=participants,
            participant_key=participant_key,
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
    user_id = str(current_user.id)
    keyed_filter = or_(
        ChatConversation.participant_key.like(f"{user_id}:%"),
        ChatConversation.participant_key.like(f"%:{user_id}"),
    )
    candidates = (
        db_session.query(ChatConversation)
        .filter(
            ChatConversation.facility_slug == facility_slug,
            or_(keyed_filter, ChatConversation.participant_key == None),
        )
        .order_by(ChatConversation.last_message_at.desc())
        .all()
    )
    conversations = [item for item in candidates if _is_participant(item, user_id)]
    if not conversations:
        return []

    for conversation in conversations:
        if not conversation.participant_key:
            conversation.participant_key = _participant_key(_participant_ids(conversation))
    db_session.flush()

    conversation_ids = [conversation.id for conversation in conversations]
    other_ids = {
        other_id
        for conversation in conversations
        if (other_id := _other_participant_id(conversation, current_user))
    }
    staff_by_id = {
        str(user.id): user
        for user in db_session.query(User)
        .filter(
            User.facility_slug == facility_slug,
            User.id.in_(other_ids),
            User.is_active == True,
        )
        .all()
    }

    latest_message_at = (
        db_session.query(
            ChatMessage.conversation_id.label("conversation_id"),
            func.max(ChatMessage.created_at).label("created_at"),
        )
        .filter(
            ChatMessage.facility_slug == facility_slug,
            ChatMessage.conversation_id.in_(conversation_ids),
        )
        .group_by(ChatMessage.conversation_id)
        .subquery()
    )
    latest_messages = (
        db_session.query(ChatMessage)
        .options(joinedload(ChatMessage.sender))
        .join(
            latest_message_at,
            and_(
                ChatMessage.conversation_id == latest_message_at.c.conversation_id,
                ChatMessage.created_at == latest_message_at.c.created_at,
            ),
        )
        .all()
    )
    latest_by_conversation = {}
    for message in latest_messages:
        latest_by_conversation.setdefault(str(message.conversation_id), message)

    unread_by_conversation = {
        str(conversation_id): int(count)
        for conversation_id, count in (
            db_session.query(ChatMessage.conversation_id, func.count(ChatMessage.id))
            .filter(
                ChatMessage.facility_slug == facility_slug,
                ChatMessage.conversation_id.in_(conversation_ids),
                ChatMessage.sender_id != current_user.id,
                ChatMessage.is_read == False,
            )
            .group_by(ChatMessage.conversation_id)
            .all()
        )
    }

    return [
        _conversation_response(
            conversation,
            current_user,
            other=staff_by_id.get(_other_participant_id(conversation, current_user) or ""),
            last_message=latest_by_conversation.get(str(conversation.id)),
            unread_count=unread_by_conversation.get(str(conversation.id), 0),
            preloaded=True,
        )
        for conversation in conversations
    ]


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    conversation_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(role_required(*CHAT_ROLES)),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation_for_user(conversation_id, current_user)
    now = datetime.utcnow()
    updated = (
        db_session.query(ChatMessage)
        .filter(
            ChatMessage.conversation_id == conversation.id,
            ChatMessage.facility_slug == current_user.facility_slug,
            ChatMessage.sender_id != current_user.id,
            ChatMessage.is_read == False,
        )
        .update(
            {ChatMessage.is_read: True, ChatMessage.read_at: now},
            synchronize_session=False,
        )
    )
    if updated:
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
    db_session.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation.id,
        ChatMessage.facility_slug == current_user.facility_slug,
        ChatMessage.sender_id != current_user.id,
        ChatMessage.is_read == False,
    ).update(
        {ChatMessage.is_read: True, ChatMessage.read_at: now},
        synchronize_session=False,
    )
    db_session.commit()
    return ChatUnreadCountResponse(unread_count=_total_unread(current_user))


def _conversation_ids_for_user(current_user: User) -> list[str]:
    facility_slug = _require_facility(current_user)
    user_id = str(current_user.id)
    keyed_filter = or_(
        ChatConversation.participant_key.like(f"{user_id}:%"),
        ChatConversation.participant_key.like(f"%:{user_id}"),
    )
    candidates = (
        db_session.query(ChatConversation.id, ChatConversation.participant_ids)
        .filter(
            ChatConversation.facility_slug == facility_slug,
            or_(keyed_filter, ChatConversation.participant_key == None),
        )
        .all()
    )
    return [
        str(conversation_id)
        for conversation_id, participant_ids in candidates
        if user_id in {str(value) for value in participant_ids or []}
    ]


def _total_unread(current_user: User) -> int:
    facility_slug = _require_facility(current_user)
    conversation_ids = _conversation_ids_for_user(current_user)
    if not conversation_ids:
        return 0
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
