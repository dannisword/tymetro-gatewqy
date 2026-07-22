from sqlalchemy import Column, String, DateTime, Boolean, func
from app.models.base import AuditModel, IdType

class User(AuditModel):
    __tablename__ = "users"

    id = Column(IdType, primary_key=True, autoincrement=True, comment="流水序")
    orgId = Column("org_id", IdType, nullable=False, comment="組織 ID")
    orgCode = Column("org_code", String(50), nullable=True, comment="組織代碼")
    account = Column(String(50), unique=True, nullable=False, comment="登入帳號")
    userName = Column("user_name", String(100), nullable=True, comment="使用者姓名")
    password = Column(String(255), nullable=True, comment="加密後的密碼")
    enableAt = Column("enable_at", DateTime, nullable=True, comment="生效日期")
    disableAt = Column("disable_at", DateTime, nullable=True, comment="停用日期")
    lastModifyAt = Column("lastModify_at", DateTime, nullable=True, comment="最後修改密碼日期")
    lastLoginAt = Column("lastLogin_at", DateTime, nullable=True, comment="最後登入日期")
    refreshToken = Column("refresh_token", String(500), nullable=True, comment="更新權杖")
    refreshTokenExpiryTime = Column("refresh_token_expiry_time", DateTime, nullable=False, default=func.now(), server_default=func.now(), comment="Token過期時間")
    isMobile = Column("is_mobile", Boolean, nullable=False, server_default="0", comment="是否為行動裝置使用者")
    isActive = Column("is_active", Boolean, nullable=False, server_default="1", comment="是否合法/啟用")

    @property
    def isAccountValid(self) -> bool:
        """判斷帳號當前是否處於有效(啟用中)狀態"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # 門檻 1: isActive 必須為 True
        if not self.isActive:
            return False
            
        # 門檻 2: 若有生效日期，現在必須 >= 生效日期
        if self.enableAt and self.enableAt > now:
            return False
            
        # 門檻 3: 若有停用日期，現在必須 < 停用日期
        if self.disableAt and self.disableAt < now:
            return False
            
        return True
