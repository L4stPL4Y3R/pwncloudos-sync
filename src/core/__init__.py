# Core modules
from .arch import detect_architecture
from .connectivity import check_internet_connectivity, check_github_api_rate_limit
from .privileges import check_sudo_available, request_sudo_upfront
from .safeguards import validate_update_target, is_path_protected
from .state import StateManager
from .rollback import RollbackEngine
