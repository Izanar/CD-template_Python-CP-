from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repository.admin.admin_primitives import AdminPrimitivesRepository
from app.repository.admin.keitaro.admin_keitaro import AdminKeitaroRepository
from app.repository.admin.tasks.designer_tasks.designer_tasks_repo import (
    AdminDesignerTaskRepository,
)
from app.repository.admin.tasks.web_master_tasks.web_master_tasks_repo import (
    AdminWebMasterTaskRepository,
)
from app.repository.admin.teams.designer_team.designer_team_repo import AdminDesignerTeamRepository
from app.repository.admin.teams.media_buyer_team.media_buyer_team_repo import (
    AdminMediaBuyerTeamRepository,
)
from app.repository.admin.teams.web_master_team.web_master_team_repo import (
    AdminWebMasterTeamRepository,
)
from app.repository.creative.creative_repo import CreativeRepository
from app.repository.designers.designer.designer_repo import DesignerRepository
from app.repository.designers.designers_teams.designers_teams_repo import DesignersTeamsRepository
from app.repository.designers.lead_designer.lead_designer_repo import LeadDesignerRepository
from app.repository.designers.task_history.designer_task_history_repo import DesignerTaskHistoryRepository
from app.repository.keitaro.keitaro_repo import KeitaroRepository
from app.repository.media_buyers.assistant.assistant_repo import AssistantRepository
from app.repository.media_buyers.lead_media_buyer.lead_media_buyer_repo import LeadMediaBuyerRepository
from app.repository.media_buyers.media_buyer_team.media_buyer_team_repo import (
    MediaBuyerTeamRepository,
)
from app.repository.media_buyers.tasks.designer_tasks.designer_task_repo import (
    DesignerTaskRepository,
)
from app.repository.media_buyers.tasks.web_master_tasks.web_master_task_repo import (
    WebMasterTaskRepository,
)
from app.repository.media_file.media_file_repo import MediaFileRepository
from app.repository.notifications.notifications_repo import NotificationsRepository
from app.repository.telegram.telegram_repo import TelegramRepository
from app.repository.user.user_repo import UserRepository
from app.repository.web_masters.lead_web_master.lead_web_master_repo import LeadWebMasterRepository
from app.repository.web_masters.task_history.web_master_task_history_repo import (
    WebMasterTaskHistoryRepository,
)
from app.repository.web_masters.web_master.web_master_repo import WebMasterRepository
from app.repository.web_masters.web_master_team.web_master_team_repo import WebMasterTeamRepository


class DatabaseRepository:
    def __init__(
        self,
        user: UserRepository,
        admin_designer_task: AdminDesignerTaskRepository,
        admin_web_master_task: AdminWebMasterTaskRepository,
        admin_designer_team: AdminDesignerTeamRepository,
        admin_media_buyer_team: AdminMediaBuyerTeamRepository,
        admin_web_master_team: AdminWebMasterTeamRepository,
        media_file: MediaFileRepository,
        lead_media_buyer: LeadMediaBuyerRepository,
        media_buyer_team: MediaBuyerTeamRepository,
        assistant: AssistantRepository,
        web_master_task: WebMasterTaskRepository,
        web_master_task_history: WebMasterTaskHistoryRepository,
        designer_task: DesignerTaskRepository,
        lead_web_master: LeadWebMasterRepository,
        web_master: WebMasterRepository,
        lead_designer: LeadDesignerRepository,
        designers_teams: DesignersTeamsRepository,
        designer_task_history: DesignerTaskHistoryRepository,
        designer: DesignerRepository,
        web_masters_teams: WebMasterTeamRepository,
        telegram: TelegramRepository,
        admin_primitives: AdminPrimitivesRepository,
        admin_keitaro: AdminKeitaroRepository,
        notifications: NotificationsRepository,
        creative: CreativeRepository,
        keitaro: KeitaroRepository,
    ) -> None:
        self.admin_designer_task = admin_designer_task
        self.admin_web_master_task = admin_web_master_task
        self.admin_designer_team = admin_designer_team
        self.admin_media_buyer_team = admin_media_buyer_team
        self.admin_web_master_team = admin_web_master_team
        self.admin_keitaro = admin_keitaro

        self.user = user

        self.media_file = media_file

        self.lead_media_buyer = lead_media_buyer
        self.media_buyer_team = media_buyer_team
        self.assistant = assistant
        self.web_master_task = web_master_task
        self.designer_task = designer_task

        self.web_masters_teams = web_masters_teams
        self.lead_web_master = lead_web_master
        self.web_master = web_master
        self.web_master_task_history = web_master_task_history

        self.lead_designer = lead_designer
        self.designer = designer
        self.designer_task_history = designer_task_history
        self.designers_teams = designers_teams
        self.telegram = telegram
        self.admin_primitives = admin_primitives
        self.notifications = notifications
        self.creative = creative
        self.keitaro = keitaro

    @classmethod
    def create(cls, session_maker: async_sessionmaker | None = None) -> "DatabaseRepository":
        if session_maker:
            return cls(
                admin_designer_task=AdminDesignerTaskRepository(session_maker=session_maker),
                admin_web_master_task=AdminWebMasterTaskRepository(session_maker=session_maker),
                admin_designer_team=AdminDesignerTeamRepository(session_maker=session_maker),
                admin_media_buyer_team=AdminMediaBuyerTeamRepository(session_maker=session_maker),
                admin_web_master_team=AdminWebMasterTeamRepository(session_maker=session_maker),
                user=UserRepository(session_maker=session_maker),
                media_file=MediaFileRepository(session_maker=session_maker),
                lead_media_buyer=LeadMediaBuyerRepository(session_maker=session_maker),
                media_buyer_team=MediaBuyerTeamRepository(session_maker=session_maker),
                assistant=AssistantRepository(session_maker=session_maker),
                designer_task=DesignerTaskRepository(session_maker=session_maker),
                web_master_task=WebMasterTaskRepository(session_maker=session_maker),
                web_master_task_history=WebMasterTaskHistoryRepository(session_maker=session_maker),
                web_masters_teams=WebMasterTeamRepository(session_maker=session_maker),
                lead_web_master=LeadWebMasterRepository(session_maker=session_maker),
                web_master=WebMasterRepository(session_maker=session_maker),
                lead_designer=LeadDesignerRepository(session_maker=session_maker),
                designers_teams=DesignersTeamsRepository(session_maker=session_maker),
                designer_task_history=DesignerTaskHistoryRepository(session_maker=session_maker),
                designer=DesignerRepository(session_maker=session_maker),
                telegram=TelegramRepository(session_maker=session_maker),
                admin_primitives=AdminPrimitivesRepository(session_maker=session_maker),
                admin_keitaro=AdminKeitaroRepository(session_maker=session_maker),
                notifications=NotificationsRepository(session_maker=session_maker),
                creative=CreativeRepository(session_maker=session_maker),
                keitaro=KeitaroRepository(session_maker=session_maker),
            )
        return None
