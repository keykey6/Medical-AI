from database.connection import get_connection, init_database, get_pool
from database.session_repo import (
    save_session, get_session, delete_session, get_all_sessions, delete_all_sessions,
    list_user_sessions, rename_session, update_session_active,
)
from database.chat_repo import save_chat_log, get_chat_history
from database.knowledge_repo import add_knowledge_item, get_knowledge_items
from database.report_repo import save_report_record, get_report_records, get_recent_report
from database.health_repo import save_health_profile, get_health_profile, get_health_profile_by_user
from database.user_repo import (
    create_user, get_user_by_username, get_user_by_id,
    bind_session_to_user, mark_session_anonymous, get_session_user,
)
