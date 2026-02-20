from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.exceptions import TagNotFoundException, DuplicateNameException


class TagService:
    @staticmethod
    def get_tags(db: Session) -> List[Tag]:
        return db.query(Tag).order_by(Tag.created_at.desc()).all()

    @staticmethod
    def get_tag_by_id(db: Session, tag_id: int) -> Tag:
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise TagNotFoundException(tag_id)
        return tag

    @staticmethod
    def create_tag(db: Session, tag_data: TagCreate) -> Tag:
        # 检查名称是否重复
        existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
        if existing:
            raise DuplicateNameException(tag_data.name)

        tag = Tag(
            name=tag_data.name,
            color=tag_data.color or '#6B7280'
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def update_tag(db: Session, tag_id: int, tag_data: TagUpdate) -> Tag:
        tag = TagService.get_tag_by_id(db, tag_id)

        # 检查名称是否重复
        if tag_data.name and tag_data.name != tag.name:
            existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
            if existing:
                raise DuplicateNameException(tag_data.name)
            tag.name = tag_data.name

        if tag_data.color:
            tag.color = tag_data.color

        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def delete_tag(db: Session, tag_id: int) -> None:
        tag = TagService.get_tag_by_id(db, tag_id)
        db.delete(tag)
        db.commit()
