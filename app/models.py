import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import expression
from sqlalchemy_utils import StringEncryptedType

from app.schemas.designers.designer_team_schema import DesignerTeamMembersResponseSchema
from app.schemas.designers.statistics import DesignerTeamShortResponseSchema
from app.schemas.enums.creative_approach import CreativeApproach
from app.schemas.enums.creative_format import CreativeFormat
from app.schemas.enums.media_buyer_team_verticals import VerticalType
from app.schemas.enums.notification_status import NotificationStatus
from app.schemas.enums.task_status import DesignerTaskStatus, WebMasterTaskStatus
from app.schemas.enums.task_type import DesignerTaskTypeEnum
from app.schemas.enums.user import UserRole
from app.schemas.enums.web_master_task import WebMasterProjectType
from app.schemas.media_buyer_team import (
    BaseUserResponseSchema,
    MediaBuyerTeamMembersResponseSchema,
    MediaBuyerTeamShortResponseSchema,
)
from app.schemas.web_masters.web_master_team import WebMasterTeamShortResponseSchema

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
meta = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)


class Base(AsyncAttrs, DeclarativeBase):
    """Base for all models."""

    metadata = meta


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    designer = relationship("Designer", back_populates="user", uselist=False, lazy="noload")
    web_master = relationship("WebMaster", back_populates="user", uselist=False, lazy="noload")
    media_buyer = relationship("MediaBuyer", back_populates="user", uselist=False, lazy="noload")

    telegram_chat_id = Column(BigInteger, unique=True, nullable=True)
    telegram_token = Column(String(36), nullable=True)
    creo = Column(String(50), nullable=True)

    jwt_version = Column(Integer, default=1, nullable=False)

    @property
    def team(self):
        if self.role in (UserRole.designer, UserRole.lead_designer) and self.designer:
            return self.designer.designer_team

        if self.role in (UserRole.web_master, UserRole.lead_web_master) and self.web_master:
            return self.web_master.web_master_team

        if self.role in (UserRole.media_buyer, UserRole.lead_media_buyer) and self.media_buyer:
            return self.media_buyer.media_buyer_team

        return None


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True)
    file_url = Column(String(255), nullable=False)
    file_key = Column(String(255), nullable=True)

    is_description = Column(Boolean, nullable=False, default=False)

    web_master_task_id = Column(Integer, ForeignKey("web_master_tasks.id"), nullable=True)
    web_master_task = relationship("WebMasterTask", back_populates="media_files", foreign_keys=[web_master_task_id])

    designer_task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"), nullable=True)
    designer_task = relationship(
        "DesignerTask", back_populates="media_files", passive_deletes=True, foreign_keys=[designer_task_id]
    )

    creative_id = Column(Integer, ForeignKey("creatives.id", ondelete="CASCADE"), nullable=True)
    creative = relationship("Creative", back_populates="media_files", passive_deletes=True, foreign_keys=[creative_id])


class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class MediaBuyer(Base):
    __tablename__ = "media_buyers"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    allow_view_team_tasks = Column(Boolean, default=False, nullable=False)
    team_lead_id = Column(Integer, ForeignKey("media_buyers.id"), nullable=True)
    team_lead = relationship("MediaBuyer", remote_side=[id], foreign_keys=[team_lead_id])
    assistant_reference_id = Column(Integer, ForeignKey("media_buyers.id"), nullable=True)
    assistant_reference = relationship("MediaBuyer", remote_side=[id], foreign_keys=[assistant_reference_id])

    created_web_master_tasks = relationship(
        "WebMasterTask", back_populates="created_by", foreign_keys="[WebMasterTask.created_by_id]"
    )

    created_designer_tasks = relationship(
        "DesignerTask", primaryjoin="foreign(DesignerTask.created_by_id) == MediaBuyer.id", viewonly=True
    )
    teams = relationship(
        "MediaBuyersTeam",
        secondary="media_buyers_team_members",
        back_populates="members",
    )
    user = relationship("User", back_populates="media_buyer", uselist=False)

    @property
    def media_buyer_team(self) -> MediaBuyerTeamShortResponseSchema | None:
        if not self.teams:
            return None
        team = self.teams[0]
        return MediaBuyerTeamShortResponseSchema(
            id=team.id,
            team_name=team.name,
            has_keitaro_config=bool(team.keitaro_config_id),
        )


class MediaBuyersTeamMembers(Base):
    __tablename__ = "media_buyers_team_members"

    media_buyer_id = Column(Integer, ForeignKey("media_buyers.id", ondelete="CASCADE"), primary_key=True)
    team_id = Column(Integer, ForeignKey("media_buyers_teams.id", ondelete="CASCADE"), primary_key=True)


class MediaBuyersTeam(Base):
    __tablename__ = "media_buyers_teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    vertical = Column(Enum(VerticalType), nullable=False, default=VerticalType.CRYPTO)

    lead_id = Column(Integer, ForeignKey("media_buyers.id"), nullable=True)
    responsible_designer = Column(Integer, ForeignKey("designers.id"), nullable=True)
    responsible_web_master = Column(Integer, ForeignKey("web_masters.id"), nullable=True)

    lead = relationship("MediaBuyer", backref="led_teams")
    members = relationship("MediaBuyer", secondary="media_buyers_team_members", back_populates="teams")
    prefix = Column(String(100), nullable=True)
    custom_task_start_id = Column(Integer, nullable=True)

    responsible_designer_info = relationship(
        "Designer",
        foreign_keys=[responsible_designer],
        back_populates="responsible_for_teams",
    )

    responsible_web_master_info = relationship(
        "WebMaster", foreign_keys=[responsible_web_master], back_populates="responsible_for_teams"
    )
    allow_archives = Column(Boolean, nullable=False, default=False)
    is_deleted = Column(Boolean, default=False)

    keitaro_config_id = Column(Integer, ForeignKey("keitaro_configs.id"), nullable=True)
    keitaro_config = relationship("KeitaroConfig", back_populates="teams")

    @property
    def responsible_designer_user(self) -> BaseUserResponseSchema | None:
        if self.responsible_designer_info and self.responsible_designer_info.user:
            return BaseUserResponseSchema(
                id=self.responsible_designer_info.id, username=self.responsible_designer_info.user.username
            )
        return None

    @property
    def responsible_web_master_user(self) -> BaseUserResponseSchema | None:
        if self.responsible_web_master_info and self.responsible_web_master_info.user:
            return BaseUserResponseSchema(
                id=self.responsible_web_master_info.id, username=self.responsible_web_master_info.user.username
            )
        return None

    @property
    def has_keitaro_config(self) -> bool:
        return self.keitaro_config_id is not None

    @property
    def lead_user(self) -> BaseUserResponseSchema | None:
        if self.lead and self.lead.user:
            return BaseUserResponseSchema(id=self.lead.id, username=self.lead.user.username)
        return None

    @property
    def members_list(self) -> list[MediaBuyerTeamMembersResponseSchema]:
        return [
            MediaBuyerTeamMembersResponseSchema(id=member.id, username=member.user.username if member.user else None)
            for member in self.members
            if member.user
        ]


class Designer(Base):
    __tablename__ = "designers"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_lead_id = Column(Integer, ForeignKey("designers.id"), nullable=True)
    team_lead = relationship("Designer", remote_side=[id])
    assigned_tasks = relationship("DesignerTask", back_populates="assigned_to")
    teams = relationship("DesignersTeam", secondary="designers_team_members", back_populates="members")
    user = relationship("User", back_populates="designer", uselist=False)
    responsible_for_teams = relationship(
        "MediaBuyersTeam",
        back_populates="responsible_designer_info",
    )

    @property
    def designer_team(self) -> DesignerTeamShortResponseSchema | None:
        """Возвращает первую команду дизайнера, если она есть, в формате схемы ответа."""
        if self.teams:
            team = self.teams[0]
            return DesignerTeamShortResponseSchema(id=team.id, team_name=team.name)
        return None


class DesignerTask(Base):
    __tablename__ = "designer_tasks"

    id = Column(Integer, primary_key=True)
    uuid = Column(PG_UUID(as_uuid=True), unique=True, nullable=True, default=uuid.uuid4)
    title = Column(String(100))
    description = Column(Text)
    task_status = Column(Enum(DesignerTaskStatus), nullable=False, default=DesignerTaskStatus.DRAFT)

    task_type = Column(Enum(DesignerTaskTypeEnum), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("designers.id"), nullable=True)
    deadline = Column(DateTime, nullable=True)
    is_high_priority = Column(Boolean, default=False)
    is_operational = Column(Boolean, default=False)

    completed_at = Column(DateTime, nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
    assigned_to = relationship("Designer", back_populates="assigned_tasks")

    history = relationship("DesignerTaskHistory", back_populates="task", foreign_keys="[DesignerTaskHistory.task_id]")

    media_files = relationship("MediaFile", back_populates="designer_task", foreign_keys="[MediaFile.designer_task_id]")

    edits: Mapped[list["DesignerTaskEdit"]] = relationship(back_populates="task", cascade="all, delete")

    difficulties = relationship("DifficultyLevel", secondary="designer_task_difficulties", back_populates="tasks")

    evaluations = relationship("TaskEvaluation", back_populates="designer_task", cascade="all, delete-orphan")

    buyer_team_id = Column(Integer, ForeignKey("media_buyers_teams.id"), nullable=True)
    buyer_team = relationship("MediaBuyersTeam", backref="designer_tasks")
    is_deleted = Column(Boolean, default=False, nullable=False)
    notes = relationship("TaskNote", back_populates="designer_task", cascade="all, delete-orphan", lazy="noload")

    geo_id = Column(Integer, ForeignKey("geos.id", ondelete="SET NULL"), nullable=True)
    geo_ref = relationship("Geo", back_populates="tasks", lazy="selectin")

    language_id = Column(Integer, ForeignKey("languages.id", ondelete="SET NULL"), nullable=True)
    language_ref = relationship("Language", back_populates="tasks", lazy="selectin")

    creatives: Mapped[list["Creative"]] = relationship("Creative", back_populates="task", cascade="all, delete-orphan")
    celebrity_relations = relationship("DesignerTaskCelebrity", back_populates="task", cascade="all, delete-orphan")

    @property
    def files(self):
        return [{"id": file.id, "file_url": file.file_url} for file in self.media_files if not file.is_description]

    @property
    def description_files(self):
        return [{"id": file.id, "file_url": file.file_url} for file in self.media_files if file.is_description]

    @property
    def assigned_to_user(self) -> dict | None:
        if self.assigned_to and self.assigned_to.user:
            team_id = self.assigned_to.teams[0].id if self.assigned_to.teams else None
            return {"id": self.assigned_to.id, "username": self.assigned_to.user.username, "team_id": team_id}
        return None

    @property
    def created_by_user(self) -> dict | None:
        if self.created_by_id and self.created_by:
            team = self.created_by.team
            return {
                "id": self.created_by_id,
                "username": self.created_by.username,
                "team": team.model_dump() if team else None,
            }
        return None

    @property
    def celebrities_list(self) -> list[dict] | None:
        if self.celebrity_relations:
            return [
                {"id": dtc.celebrity.id, "name": dtc.celebrity.name}
                for dtc in self.celebrity_relations
                if dtc.celebrity
            ]
        return None

    @property
    def task_prefix(self) -> str | None:
        if self.created_by_id and self.created_by:
            return self.created_by.media_buyer.teams[0].prefix
        return None

    @property
    def evaluation_required(self) -> bool:
        if not self.task_type:
            return False
        return self.task_type.evaluation_required

    @property
    def vertical(self) -> VerticalType | None:
        return self.buyer_team.vertical if self.buyer_team else None

    @property
    def geo(self) -> dict | None:
        if self.geo_ref:
            return {"id": self.geo_ref.id, "code": self.geo_ref.code, "name": self.geo_ref.name}
        return None

    @property
    def language(self) -> dict | None:
        if self.language_ref:
            return {"id": self.language_ref.id, "code": self.language_ref.code, "name": self.language_ref.name}
        return None

    @property
    def allow_archives(self) -> bool | None:
        return self.buyer_team.allow_archives if self.buyer_team else None


class DesignerTaskType(Base):
    __tablename__ = "task_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    is_inactive = Column(Boolean)
    evaluation_required = Column(Boolean)


class DifficultyLevel(Base):
    __tablename__ = "difficulty_levels"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    points = Column(Integer, nullable=False)
    is_inactive = Column(Boolean, default=False)

    tasks = relationship("DesignerTask", secondary="designer_task_difficulties", back_populates="difficulties")


class DesignerTaskDifficulty(Base):
    __tablename__ = "designer_task_difficulties"

    task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"), primary_key=True)
    difficulty_id = Column(Integer, ForeignKey("difficulty_levels.id"), primary_key=True)


class DesignerTaskEdit(Base):
    __tablename__ = "designer_task_edits"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("designer_tasks.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    solved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["DesignerTask"] = relationship(back_populates="edits")


class DesignersTeamLeads(Base):
    __tablename__ = "designers_team_leads"
    team_id = Column(Integer, ForeignKey("designers_teams.id", ondelete="CASCADE"), primary_key=True)
    designer_id = Column(Integer, ForeignKey("designers.id", ondelete="CASCADE"), primary_key=True)


class DesignersTeam(Base):
    __tablename__ = "designers_teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    leads = relationship(
        "Designer",
        secondary="designers_team_leads",
        lazy="selectin",
    )

    members = relationship("Designer", secondary="designers_team_members", back_populates="teams")

    @property
    def lead_users(self) -> list[BaseUserResponseSchema]:
        return [
            BaseUserResponseSchema(id=designer.id, username=designer.user.username)
            for designer in self.leads
            if designer.user
        ]

    @property
    def members_list(self) -> list[DesignerTeamMembersResponseSchema]:
        return [
            DesignerTeamMembersResponseSchema(id=member.id, username=member.user.username if member.user else None)
            for member in self.members
            if member.user
        ]


class DesignersTeamMembers(Base):
    __tablename__ = "designers_team_members"

    designer_id = Column(Integer, ForeignKey("designers.id", ondelete="CASCADE"), primary_key=True)
    team_id = Column(Integer, ForeignKey("designers_teams.id", ondelete="CASCADE"), primary_key=True)


class TaskCorrection(Base):
    __tablename__ = "task_corrections"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("designer_tasks.id"))
    correction_time = Column(DateTime, default=datetime.utcnow)

    task = relationship("DesignerTask")


class DesignerTaskHistory(Base):
    __tablename__ = "designer_task_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"))
    event = Column(String(32), nullable=False)
    event_info = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    task = relationship("DesignerTask", back_populates="history")

    active = Column(Boolean, default=True, nullable=False)


class TaskEvaluation(Base):
    __tablename__ = "task_evaluations"

    id = Column(Integer, primary_key=True)
    designer_task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"), nullable=True)
    web_master_task_id = Column(Integer, ForeignKey("web_master_tasks.id", ondelete="CASCADE"), nullable=True)
    evaluator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    designer_task = relationship("DesignerTask", back_populates="evaluations")
    web_master_task = relationship("WebMasterTask", back_populates="evaluations")
    evaluator = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "(designer_task_id IS NOT NULL AND web_master_task_id IS NULL) OR "
            "(designer_task_id IS NULL AND web_master_task_id IS NOT NULL)",
            name="check_one_task_reference",
        ),
    )


class WebMaster(Base):
    __tablename__ = "web_masters"

    id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_lead_id = Column(Integer, ForeignKey("web_masters.id"), nullable=True)
    team_lead = relationship("WebMaster", remote_side=[id])
    assigned_tasks = relationship("WebMasterTask", back_populates="assigned_to")
    user = relationship("User", back_populates="web_master", uselist=False)
    teams = relationship("WebMastersTeam", secondary="web_masters_team_members", back_populates="members")
    responsible_for_teams = relationship(
        "MediaBuyersTeam",
        back_populates="responsible_web_master_info",
    )

    @property
    def web_master_team(self) -> WebMasterTeamShortResponseSchema | None:
        if self.teams:
            team = self.teams[0]
            return WebMasterTeamShortResponseSchema(id=team.id, team_name=team.name)
        return None


class WebMasterTask(Base):
    __tablename__ = "web_master_tasks"

    id = Column(Integer, primary_key=True)
    uuid = Column(PG_UUID(as_uuid=True), unique=True, nullable=True, default=uuid.uuid4)

    title = Column(String(100))
    description = Column(Text)
    task_status = Column(Enum(WebMasterTaskStatus), nullable=False, default=WebMasterTaskStatus.DRAFT)

    task_type_id = Column(Integer, ForeignKey("web_master_task_types.id"), nullable=True)
    task_type = relationship("WebMasterTaskType", back_populates="tasks")
    task_points = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey("media_buyers.id"))
    assigned_to_id = Column(Integer, ForeignKey("web_masters.id"), nullable=True)
    deadline = Column(DateTime, nullable=True)
    is_high_priority = Column(Boolean, default=False)

    completed_at = Column(DateTime, nullable=True)

    created_by = relationship("MediaBuyer", back_populates="created_web_master_tasks", foreign_keys=[created_by_id])
    assigned_to = relationship("WebMaster", back_populates="assigned_tasks")

    history = relationship("WebMasterTaskHistory", back_populates="task", foreign_keys="[WebMasterTaskHistory.task_id]")

    media_files = relationship(
        "MediaFile", back_populates="web_master_task", foreign_keys="[MediaFile.web_master_task_id]"
    )

    edits: Mapped[list["WebMasterTaskEdit"]] = relationship(back_populates="task")

    difficulties = relationship(
        "WebMasterDifficultyLevel", secondary="web_master_task_difficulties", back_populates="tasks"
    )

    evaluations = relationship("TaskEvaluation", back_populates="web_master_task", cascade="all, delete-orphan")

    buyer_team_id = Column(Integer, ForeignKey("media_buyers_teams.id"), nullable=True)
    buyer_team = relationship("MediaBuyersTeam", backref="web_master_tasks")
    is_deleted = Column(Boolean, default=False, nullable=False)
    notes = relationship("TaskNote", back_populates="web_master_task", cascade="all, delete-orphan", lazy="noload")

    funnel_id = Column(Integer, ForeignKey("funnels.id"), nullable=True)
    site_name_id = Column(Integer, ForeignKey("site_names.id"), nullable=True)
    celebrity_id = Column(Integer, ForeignKey("celebrities.id"), nullable=True)

    funnel_ref = relationship("Funnel", back_populates="web_master_tasks")
    site_name_ref = relationship("SiteName", back_populates="web_master_tasks")
    celebrity_ref = relationship("Celebrity", back_populates="web_master_tasks")

    geo_id = Column(Integer, ForeignKey("geos.id", ondelete="SET NULL"), nullable=True)
    geo_ref = relationship("Geo", back_populates="web_master_tasks", lazy="selectin")

    project_type = Column(Enum(WebMasterProjectType), nullable=True)

    def _ref_to_dict(self, ref, fields: dict = None) -> dict | None:
        if ref:
            default_fields = {"id": ref.id, "name": ref.name, "is_deleted": ref.is_deleted}
            if fields:
                return {key: getattr(ref, key) for key in fields}
            return default_fields
        return None

    @property
    def funnel(self) -> dict | None:
        return self._ref_to_dict(self.funnel_ref)

    @property
    def celebrity(self) -> dict | None:
        return self._ref_to_dict(self.celebrity_ref)

    @property
    def site_name(self) -> dict | None:
        return self._ref_to_dict(self.site_name_ref)

    @property
    def geo(self) -> dict | None:
        return self._ref_to_dict(self.geo_ref, fields=["id", "code", "name"])

    @property
    def vertical(self) -> VerticalType | None:
        return self.buyer_team.vertical if self.buyer_team else None

    @hybrid_property
    def media_files_info(self):
        """Возвращает список словарей с id и file_url для каждого медиафайла."""
        return [{"id": file.id, "file_url": file.file_url} for file in self.media_files]

    @property
    def assigned_to_user(self) -> dict | None:
        if self.assigned_to and self.assigned_to.user:
            team_id = self.assigned_to.teams[0].id if self.assigned_to.teams else None
            return {"id": self.assigned_to.id, "username": self.assigned_to.user.username, "team_id": team_id}
        return None

    @property
    def created_by_user(self) -> dict | None:
        if self.created_by_id and self.created_by.user:
            return {"id": self.created_by_id, "username": self.created_by.user.username}
        return None


class WebMastersTeamMembers(Base):
    __tablename__ = "web_masters_team_members"

    web_master_id = Column(Integer, ForeignKey("web_masters.id", ondelete="CASCADE"), primary_key=True)
    team_id = Column(Integer, ForeignKey("web_masters_teams.id", ondelete="CASCADE"), primary_key=True)


class WebMastersTeam(Base):
    __tablename__ = "web_masters_teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    lead_id = Column(Integer, ForeignKey("web_masters.id"), nullable=True)

    lead = relationship("WebMaster", primaryjoin="WebMastersTeam.lead_id == WebMaster.id", backref="led_teams")

    members = relationship("WebMaster", secondary="web_masters_team_members", back_populates="teams")

    @property
    def lead_user(self) -> BaseUserResponseSchema | None:
        if self.lead and self.lead.user:
            return BaseUserResponseSchema(id=self.lead.id, username=self.lead.user.username)
        return None

    @property
    def members_list(self) -> list[WebMastersTeamMembers]:
        return [
            WebMastersTeamMembers(id=member.id, username=member.user.username if member.user else None)
            for member in self.members
            if member.user
        ]


class WebMasterTaskDifficulty(Base):
    __tablename__ = "web_master_task_difficulties"

    task_id = Column(Integer, ForeignKey("web_master_tasks.id"), primary_key=True)
    difficulty_id = Column(Integer, ForeignKey("web_master_difficulty_levels.id"), primary_key=True)


class WebMasterDifficultyLevel(Base):
    __tablename__ = "web_master_difficulty_levels"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    points = Column(Float, nullable=False)

    tasks = relationship("WebMasterTask", secondary="web_master_task_difficulties", back_populates="difficulties")


class WebMasterTaskEdit(Base):
    __tablename__ = "web_master_task_edits"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("web_master_tasks.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    solved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["WebMasterTask"] = relationship(back_populates="edits")


class WebMasterTaskCorrection(Base):
    __tablename__ = "web_master_task_corrections"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("web_master_tasks.id"))
    correction_time = Column(DateTime, default=datetime.utcnow)

    task = relationship("WebMasterTask")


class WebMasterTaskHistory(Base):
    __tablename__ = "web_master_task_history"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("web_master_tasks.id", ondelete="CASCADE"))
    buyer_id = Column(Integer, ForeignKey("media_buyers.id"))
    lead_id = Column(Integer, ForeignKey("web_masters.id"))
    assigned_web_master_id = Column(Integer, ForeignKey("web_masters.id"))
    event = Column(String(32), nullable=False)
    event_info = Column(Text, nullable=False)

    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    task = relationship("WebMasterTask", back_populates="history")


class WebMasterTaskType(Base):
    __tablename__ = "web_master_task_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)

    tasks = relationship("WebMasterTask", back_populates="task_type")


class TaskNote(Base):
    __tablename__ = "task_notes"

    id = Column(Integer, primary_key=True)

    designer_task_id = Column(
        Integer,
        ForeignKey("designer_tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    web_master_task_id = Column(
        Integer,
        ForeignKey("web_master_tasks.id", ondelete="CASCADE"),
        nullable=True,
    )

    author_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )

    is_team_note = Column(Boolean, default=False, nullable=False, server_default=expression.false())

    content = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.timezone("utc", func.now()),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.timezone("utc", func.now()),
    )

    author = relationship("User")
    designer_task = relationship("DesignerTask", back_populates="notes")
    web_master_task = relationship("WebMasterTask", back_populates="notes")

    __table_args__ = (
        Index(
            "ux_task_team_note",
            "designer_task_id",
            unique=True,
            postgresql_where=text("is_team_note = TRUE"),
        ),
        UniqueConstraint(
            "designer_task_id",
            "author_id",
            name="ux_task_author_note",
        ),
        UniqueConstraint(
            "web_master_task_id",
            "author_id",
            name="ux_note_webmaster_task_author",
        ),
        CheckConstraint(
            "(designer_task_id IS NOT NULL AND web_master_task_id IS NULL) OR "
            "(designer_task_id IS NULL  AND web_master_task_id IS NOT NULL)",
            name="check_one_task_reference",
        ),
    )


class Geo(Base):
    __tablename__ = "geos"

    id = Column(Integer, primary_key=True)
    code = Column(String(2), unique=True, nullable=False)
    name = Column(String(100), nullable=False)

    tasks = relationship("DesignerTask", back_populates="geo_ref")
    web_master_tasks = relationship("WebMasterTask", back_populates="geo_ref")
    is_deleted = Column(Boolean, default=False, nullable=False)


class Funnel(Base):
    __tablename__ = "funnels"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    web_master_tasks = relationship("WebMasterTask", back_populates="funnel_ref")

    __table_args__ = (Index("ux_funnels_name_lower", func.lower(name), unique=True),)


class SiteName(Base):
    __tablename__ = "site_names"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    web_master_tasks = relationship("WebMasterTask", back_populates="site_name_ref")

    __table_args__ = (Index("ux_site_names_name_lower", func.lower(name), unique=True),)


class Celebrity(Base):
    __tablename__ = "celebrities"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    designer_tasks = relationship("DesignerTaskCelebrity", back_populates="celebrity")
    web_master_tasks = relationship("WebMasterTask", back_populates="celebrity_ref")

    __table_args__ = (Index("ux_celebrities_name_lower", func.lower(name), unique=True),)


class Language(Base):
    __tablename__ = "languages"
    id = Column(Integer, primary_key=True)
    code = Column(String(5), unique=True, nullable=False)  # ISO language code (e.g., 'en', 'uk', 'ru')
    name = Column(String(100), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    tasks = relationship("DesignerTask", back_populates="language_ref")

    __table_args__ = (Index("ux_languages_code_lower", func.lower(code), unique=True),)


class NotificationQueue(Base):
    __tablename__ = "notification_queue"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False)


class DesignerTaskCelebrity(Base):
    __tablename__ = "designer_task_celebrities"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"), nullable=False)
    celebrity_id = Column(Integer, ForeignKey("celebrities.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("DesignerTask", back_populates="celebrity_relations")
    celebrity = relationship("Celebrity", back_populates="designer_tasks")

    __table_args__ = (UniqueConstraint("task_id", "celebrity_id", name="ux_designer_task_celebrity_unique"),)


class Creative(Base):
    __tablename__ = "creatives"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("designer_tasks.id", ondelete="CASCADE"), nullable=False)
    format = Column(Enum(CreativeFormat), nullable=True)
    subtitles = Column(Boolean, nullable=True)
    plashka = Column(Boolean, nullable=True)
    text = Column(Text, nullable=True)
    ad_name = Column(String(100), unique=True, nullable=True)
    campaign_id = Column(Integer, nullable=True)
    campaign_name = Column(String(200), nullable=True)
    streams_data = Column(JSON, nullable=True)
    approach = Column(JSON, nullable=True)
    keitaro_config_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    keitaro_config_user = relationship("User", foreign_keys=[keitaro_config_user_id], lazy="selectin")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    task = relationship("DesignerTask", back_populates="creatives")
    media_files = relationship("MediaFile", back_populates="creative", foreign_keys="[MediaFile.creative_id]")

    @property
    def campaign(self):
        if self.campaign_id and self.campaign_name:
            return {"id": self.campaign_id, "name": self.campaign_name}
        return None

    @property
    def streams(self):
        if self.streams_data:
            return self.streams_data
        return []

    @property
    def approaches(self):
        if self.approach:
            return CreativeApproach.sort_approaches(self.approach)
        return []


class KeitaroConfig(Base):
    __tablename__ = "keitaro_configs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    api_key = Column(StringEncryptedType(String(255), "auto"), nullable=False)
    base_url = Column(String(500), nullable=False)
    creo = Column(String(50), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)

    teams = relationship("MediaBuyersTeam", back_populates="keitaro_config")
