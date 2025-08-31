from typing import Union

from pydantic import BaseModel


class ChatConfig(BaseModel):
    chat_id: int
    param_name: str
    param_value: Union[str, int, bool]


class ChatConfigSetRequest(BaseModel):
    chat_id: int
    param_name: str
    param_value: Union[str, int, bool]


class ChatConfigGetResponse(BaseModel):
    chat_id: int
    param_name: str
    param_value: Union[str, int, bool, None] = None


class AllChatConfigsResponse(BaseModel):
    chat_id: int
    configs: dict[str, Union[str, int, bool]]
