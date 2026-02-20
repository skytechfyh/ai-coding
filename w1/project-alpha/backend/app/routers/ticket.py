from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("")
def get_tickets(
    tag_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    tickets, total = ticket_service.TicketService.get_tickets(
        db, tag_id=tag_id, status=status, search=search, skip=skip, limit=page_size
    )

    return {
        "success": True,
        "data": {
            "items": [TicketResponse.model_validate(t) for t in tickets],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.get_ticket_by_id(db, ticket_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}


@router.post("")
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    new_ticket = ticket_service.TicketService.create_ticket(db, ticket)
    return {"success": True, "data": TicketResponse.model_validate(new_ticket)}


@router.put("/{ticket_id}")
def update_ticket(ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_db)):
    updated_ticket = ticket_service.TicketService.update_ticket(db, ticket_id, ticket)
    return {"success": True, "data": TicketResponse.model_validate(updated_ticket)}


@router.patch("/{ticket_id}")
def patch_ticket(ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_db)):
    updated_ticket = ticket_service.TicketService.update_ticket(db, ticket_id, ticket)
    return {"success": True, "data": TicketResponse.model_validate(updated_ticket)}


@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket_service.TicketService.delete_ticket(db, ticket_id)
    return {"success": True, "message": "Ticket 删除成功"}


@router.patch("/{ticket_id}/complete")
def complete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.complete_ticket(db, ticket_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}


@router.patch("/{ticket_id}/uncomplete")
def uncomplete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.uncomplete_ticket(db, ticket_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}


@router.post("/{ticket_id}/tags")
def add_tag_to_ticket(ticket_id: int, data: dict, db: Session = Depends(get_db)):
    tag_id = data.get("tag_id")
    if not tag_id:
        return {"success": False, "error": {"code": "INVALID_INPUT", "message": "tag_id 不能为空"}}

    ticket = ticket_service.TicketService.add_tag_to_ticket(db, ticket_id, tag_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}


@router.delete("/{ticket_id}/tags/{tag_id}")
def remove_tag_from_ticket(ticket_id: int, tag_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.remove_tag_from_ticket(db, ticket_id, tag_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}
