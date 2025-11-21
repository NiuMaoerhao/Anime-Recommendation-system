import mysql.connector
from mysql.connector import Error
import ast

# 数据库配置（直接复用你attendance_system中验证有效的配置）
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',  # 与你考勤系统一致的有效密码
    'database': 'python',  # 确保该数据库已在Navicat中创建
    'charset': 'utf8mb4'  # 避免中文乱码
}

class DBHelper:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def _connect(self):
        """内部连接方法，统一处理连接逻辑"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                return True
        except Error as e:
            print(f"数据库连接失败: {e}")
            self._close()  # 连接失败时也关闭资源
            return False

    def _close(self):
        """内部关闭方法，确保cursor和connection都关闭（参考你考勤系统的严谨逻辑）"""
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()

    # 在 get_all_animes 方法中解析数据时添加
    def get_all_animes(self):
        """获取所有动画数据（解析genre为列表）"""
        query = "SELECT * FROM animes"
        result = []
        if self._connect():
            try:
                self.cursor.execute(query)
                result = self.cursor.fetchall()
                # 解析数据字段
                for anime in result:
                    # 解析genre字段
                    if anime['genre']:
                        try:
                            anime['genre'] = ast.literal_eval(anime['genre'])
                        except:
                            anime['genre'] = [anime['genre']]

                    # 新增：转换members为整数
                    if anime['members']:
                        try:
                            anime['members'] = int(anime['members'])
                        except (ValueError, TypeError):
                            anime['members'] = 0
                    else:
                        anime['members'] = 0

                    # 新增：转换score为浮点数
                    if anime['score']:
                        try:
                            anime['score'] = float(anime['score'])
                        except (ValueError, TypeError):
                            anime['score'] = 0.0
                    else:
                        anime['score'] = 0.0
            except Error as e:
                print(f"查询所有动画失败: {e}")
            finally:
                self._close()
        return result

    def get_anime_by_uid(self, uid):
        """通过uid获取单个动画详情"""
        query = "SELECT * FROM animes WHERE uid = %s"
        result = None
        if self._connect():
            try:
                self.cursor.execute(query, (uid,))
                result = self.cursor.fetchone()
                # 解析genre字段
                if result and result['genre']:
                    try:
                        result['genre'] = ast.literal_eval(result['genre'])
                    except:
                        result['genre'] = [result['genre']]
            except Error as e:
                print(f"查询动画uid={uid}失败: {e}")
            finally:
                self._close()
        return result

    def get_popular_animes(self, top_n=10):
        """获取热门动画（按members数量降序排序，取前N个）"""
        animes = self.get_all_animes()
        # 按members字段排序，过滤members为空的情况
        sorted_animes = sorted(
            animes,
            key=lambda x: x['members'] or 0,  # 空值按0处理
            reverse=True
        )
        return sorted_animes[:top_n]

    def get_anime_genres(self):
        """获取所有动画的类型（去重，用于前端类型选择框）"""
        query = "SELECT DISTINCT genre FROM animes"
        genres = set()
        if self._connect():
            try:
                self.cursor.execute(query)
                results = self.cursor.fetchall()
                for item in results:
                    if item['genre']:
                        try:
                            # 解析类型列表并添加到集合（去重）
                            genre_list = ast.literal_eval(item['genre'])
                            genres.update(genre_list)
                        except:
                            genres.add(item['genre'])
            except Error as e:
                print(f"获取动画类型失败: {e}")
            finally:
                self._close()
        return list(genres)

    def get_reviews_by_anime_uid(self, anime_uid):
        """通过动画uid获取相关评论"""
        query = "SELECT * FROM reviews WHERE anime_uid = %s"
        reviews = []
        if self._connect():
            try:
                self.cursor.execute(query, (anime_uid,))
                reviews = self.cursor.fetchall()
            except Error as e:
                print(f"查询动画uid={anime_uid}的评论失败: {e}")
            finally:
                self._close()
        return reviews

    #数据库用户表连接

    def get_user_by_username(self, username):
        """通过用户名获取用户信息"""
        query = "SELECT * FROM users WHERE username = %s"
        user = None
        if self._connect():
            try:
                self.cursor.execute(query, (username,))
                user = self.cursor.fetchone()
            except Error as e:
                print(f"查询用户{username}失败: {e}")
            finally:
                self._close()
        return user

    def add_user(self, username, password_hash, email=None):
        """添加新用户"""
        query = """
        INSERT INTO users (username, password, email) 
        VALUES (%s, %s, %s)
        """
        if self._connect():
            try:
                self.cursor.execute(query, (username, password_hash, email))
                self.connection.commit()
                return True
            except Error as e:
                print(f"添加用户{username}失败: {e}")
                self.connection.rollback()
                return False
            finally:
                self._close()
        return False

    def update_last_login(self, user_id):
        """更新用户最后登录时间"""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        if self._connect():
            try:
                self.cursor.execute(query, (user_id,))
                self.connection.commit()
                return True
            except Error as e:
                print(f"更新用户{user_id}登录时间失败: {e}")
                self.connection.rollback()
                return False
            finally:
                self._close()
        return False