from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.tag import TagCreate, TagUpdate, TagResponse
from app.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("")
def get_tags(db: Session = Depends(get_db)):
    tags = tag_service.TagService.get_tags(db)
    return {"success": True, "data": [TagResponse.model_validate(t) for t in tags]}


@router.get("/{tag_id}")
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = tag_service.TagService.get_tag_by_id(db, tag_id)
    return {"success": True, "data": TagResponse.model_validate(tag)}


@router.post("")
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    new_tag = tag_service.TagService.create_tag(db, tag)
    return {"success": True, "data": TagResponse.model_validate(new_tag)}


@router.put("/{tag_id}")
def update_tag(tag_id: int, tag: TagUpdate, db: Session = Depends(get_db)):
    updated_tag = tag_service.TagService.update_tag(db, tag_id, tag)
    return {"success": True, "data": TagResponse.model_validate(updated_tag)}


@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag_service.TagService.delete_tag(db, tag_id)
    return {"success": True, "message": "标签删除成功"}
