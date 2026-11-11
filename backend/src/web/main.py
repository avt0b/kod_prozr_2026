from src.core.config import get_settings_from_env
from src.web.create_app import create_app

app = create_app(get_settings_from_env())
