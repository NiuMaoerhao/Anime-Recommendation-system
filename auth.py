import bcrypt
from db_helper import DBHelper


class AuthService:
    def __init__(self, db_helper):
        self.db = db_helper

    def hash_password(self, password):
        """加密密码"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)

    def verify_password(self, password, hashed_password):
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

    def register_user(self, username, password, email=None):
        """注册新用户"""
        # 检查用户名是否已存在
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            return False, "用户名已存在"

        # 加密密码并保存用户
        password_hash = self.hash_password(password)
        success = self.db.add_user(username, password_hash.decode('utf-8'), email)
        if success:
            return True, "注册成功"
        return False, "注册失败"

    def login_user(self, username, password):
        """用户登录验证"""
        user = self.db.get_user_by_username(username)
        if not user:
            return False, "用户名不存在"

        # 验证密码
        if self.verify_password(password, user['password']):
            # 更新最后登录时间
            self.db.update_last_login(user['id'])
            return True, user
        return False, "密码错误"