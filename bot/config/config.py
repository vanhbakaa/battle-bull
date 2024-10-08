from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str


    REF_LINK: str = "https://t.me/battle_games_com_bot/start?startapp=frndId6493211155"
    AUTO_APPLY_PROMOCODES: bool = True
    CODES: list[str] = ["BOOSTER"]
    AUTO_TAP: bool = False
    TAP_COUNTS: list[int] = [25, 75]
    AUTO_TASK: bool = True
    AUTO_UPGRADE: bool = True
    DELAY_EACH_ACCOUNT: list[int] = [15,25]
    SLEEP_TIME_BETWEEN_EACH_ROUND: list[int] = [500, 700]

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()

