from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from app.models.ticket import Ticket
from app.models.tag import Tag
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.utils.exceptions import TicketNotFoundException, TagNotFoundException


class TicketService:
    @staticmethod
    def get_tickets(
        db: Session,
        tag_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Ticket], int]:
        query = db.query(Ticket)

        # 按标签筛选
        if tag_id:
            query = query.join(Ticket.tags).filter(Tag.id == tag_id)

        # 按状态筛选
        if status:
            query = query.filter(Ticket.status == status)

        # 按标题搜索
        if search:
            query = query.filter(Ticket.title.ilike(f"%{search}%"))

        # 获取总数
        total = query.count()

        # 分页
        tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()

        return tickets, total

    @staticmethod
    def get_ticket_by_id(db: Session, ticket_id: int) -> Ticket:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise TicketNotFoundException(ticket_id)
        return ticket

    @staticmethod
    def create_ticket(db: Session, ticket_data: TicketCreate) -> Ticket:
        # 处理标签
        tags = []
        if ticket_data.tag_ids:
            tags = db.query(Tag).filter(Tag.id.in_(ticket_data.tag_ids)).all()

        ticket = Ticket(
            title=ticket_data.title,
            description=ticket_data.description,
            tags=tags
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def update_ticket(db: Session, ticket_id: int, ticket_data: TicketUpdate) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)

        # 更新字段
        if ticket_data.title is not None:
            ticket.title = ticket_data.title
        if ticket_data.description is not None:
            ticket.description = ticket_data.description
        if ticket_data.status is not None:
            ticket.status = ticket_data.status

        # 更新标签
        if ticket_data.tag_ids is not None:
            tags = db.query(Tag).filter(Tag.id.in_(ticket_data.tag_ids)).all()
            ticket.tags = tags

        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def delete_ticket(db: Session, ticket_id: int) -> None:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        db.delete(ticket)
        db.commit()

    @staticmethod
    def complete_ticket(db: Session, ticket_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        ticket.status = 'completed'
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def uncomplete_ticket(db: Session, ticket_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        ticket.status = 'pending'
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def add_tag_to_ticket(db: Session, ticket_id: int, tag_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise TagNotFoundException(tag_id)

        if tag not in ticket.tags:
            ticket.tags.append(tag)
            db.commit()
            db.refresh(ticket)
        return ticket

    @staticmethod
    def remove_tag_from_ticket(db: Session, ticket_id: int, tag_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise TagNotFoundException(tag_id)

        if tag in ticket.tags:
            ticket.tags.remove(tag)
            db.commit()
            db.refresh(ticket)
        return ticket
