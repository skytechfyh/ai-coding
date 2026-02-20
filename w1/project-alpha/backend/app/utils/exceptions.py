from fastapi import HTTPException, status


class TicketNotFoundException(HTTPException):
    def __init__(self, ticket_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} 不存在"
        )


class TagNotFoundException(HTTPException):
    def __init__(self, tag_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"标签 #{tag_id} 不存在"
        )


class DuplicateNameException(HTTPException):
    def __init__(self, name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"名称 '{name}' 已存在"
        )


class InvalidInputException(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
