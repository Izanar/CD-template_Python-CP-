from pydantic import BaseModel, ConfigDict


class WebMasterTaskDifficultiesSchema(BaseModel):
    id: int
    name: str
    points: int

    model_config = ConfigDict(from_attributes=True)
