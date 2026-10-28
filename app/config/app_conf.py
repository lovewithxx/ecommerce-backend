"""
应用配置，全部从 .env 读取。

为什么用 pydantic-settings 而不是 os.getenv：
    1. 自动类型转换（端口 "3306" -> int）
    2. 启动时就校验，缺字段立刻报错
    3. case_sensitive=False 后，.env 里写大写或小写都能匹配
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # 数据库
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "ecom_app"

    # 调试：True 时打印 SQL、异常带 traceback
    debug: bool = True

    # 大模型（第二步才用，先给默认值，不配也能启动）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """
        mysql+aiomysql://用户:密码@主机:端口/库名?charset=utf8mb4

        charset=utf8mb4 不能省：MySQL 的 utf8 只支持 3 字节，存不了 emoji。
        """
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()
