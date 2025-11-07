from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.config.config import ConfigDTO
from app.dependecies.stub import AppConfigStub


def verify_external_api_key(
    x_api_key: Annotated[str, Header(alias="X-API-Key")],
    config: Annotated[ConfigDTO, Depends(AppConfigStub)],
) -> str:
    if x_api_key != config.external_api.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key. Please provide valid X-API-Key header.")
    return x_api_key
