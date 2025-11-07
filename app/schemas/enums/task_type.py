import enum


class WebMasterTaskType(enum.Enum):
    edit = "edit"
    for_new_project = "for_new_project"
    non_standart = "non_standart"


class DesignerTaskTypeEnum(enum.Enum):
    creo_video = "creo_video"
    creo_statika = "creo_statika"
    land_video = "land_video"
    land_statika = "land_statika"
    plashki_uniq = "plashki/uniq"
    other = "other"

    @property
    def evaluation_required(self) -> bool:
        evaluation_required_types = {
            self.creo_video: True,
            self.creo_statika: True,
            self.plashki_uniq: True,
        }
        return evaluation_required_types.get(self, False)
