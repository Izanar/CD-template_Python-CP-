from pydantic import BaseModel, ConfigDict


class DesignerTaskDifficultiesSchema(BaseModel):
    id: int
    name: str
    points: int

    model_config = ConfigDict(from_attributes=True)
