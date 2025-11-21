from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from functools import wraps
from db_helper import DBHelper
from recommender import AnimeRecommender
import logging
import random
from auth import AuthService
import secrets

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置密钥用于会话管理
app.secret_key = secrets.token_hex(16)  # 生产环境应使用固定密钥

# 初始化数据库、推荐器和认证服务
try:
    db = DBHelper()
    recommender = AnimeRecommender(db)
    auth_service = AuthService(db)  # 初始化认证服务
    logger.info("数据库、推荐器和认证服务初始化成功")
except Exception as e:
    logger.error(f"初始化失败: {str(e)}", exc_info=True)
    # 初始化失败时仍创建实例防止崩溃，实际部署需处理
    db = None
    recommender = None
    auth_service = None


# 登录保护装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录才能使用该功能', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def index():
    """首页：显示热门动画和推荐表单"""
    try:
        if not db:
            raise Exception("数据库连接未初始化")

        popular_animes = db.get_popular_animes(top_n=6)
        # 确保数据类型正确
        for anime in popular_animes:
            if 'members' in anime:
                anime['members'] = int(anime['members']) if anime['members'] else 0
            if 'score' in anime:
                try:
                    anime['score'] = float(anime['score']) if anime['score'] else 0.0
                except (ValueError, TypeError):
                    anime['score'] = 0.0

        return render_template('index.html', popular_animes=popular_animes)

    except Exception as e:
        logger.error(f"首页加载失败: {str(e)}", exc_info=True)
        return render_template('error.html', message="加载首页失败，请稍后重试"), 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录页面"""
    if request.method == 'POST':
        if not auth_service:
            flash('服务未初始化完成，请稍后再试', 'danger')
            return render_template('login.html')

        username = request.form.get('username')
        password = request.form.get('password')

        success, result = auth_service.login_user(username, password)
        if success:
            # 登录成功，设置会话
            session['user_id'] = result['id']
            session['username'] = result['username']
            next_page = request.args.get('next', '/')
            flash('登录成功，欢迎回来！', 'success')
            return redirect(next_page)
        else:
            flash(result, 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册页面"""
    if request.method == 'POST':
        if not auth_service:
            flash('服务未初始化完成，请稍后再试', 'danger')
            return render_template('register.html')

        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email', '')

        # 表单验证
        if not username or not password:
            flash('用户名和密码不能为空', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('密码长度不能少于6位', 'danger')
            return render_template('register.html')

        success, message = auth_service.register_user(username, password, email)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')

    return render_template('register.html')


@app.route('/logout')
def logout():
    """用户登出"""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('已成功登出', 'success')
    return redirect(url_for('index'))


@app.route('/recommend', methods=['POST'])
@login_required  # 推荐功能需要登录
def recommend():
    """处理推荐请求（需要登录）"""
    try:
        if not recommender or not db:
            return jsonify({"error": "服务未初始化完成"}), 500

        preferred_genres = request.form.getlist('genres')
        min_score = float(request.form.get('min_score', 0))

        if not preferred_genres:
            return jsonify({"error": "请选择至少一种偏好类型"}), 400

        logger.info(f"用户 {session['username']} 请求推荐，偏好类型: {preferred_genres}, 最低评分: {min_score}")

        recommendations = recommender.recommend_based_on_genres(preferred_genres, min_score, top_n=10)

        result = []
        for anime in recommendations:
            members = int(anime['members']) if anime.get('members') else 0
            score = float(anime['score']) if anime.get('score') else 0.0

            result.append({
                "uid": anime.get('uid', ''),
                "title": anime.get('title', '未知标题'),
                "genre": anime.get('genre', []),
                "score": float(anime.get('score', 0.0)),
                "members": int(anime.get('members', 0)),
                "aired": anime.get('aired', '未知时间'),
                "synopsis": (anime.get('synopsis', '')[:150] + "...") if anime.get('synopsis') else "",
                "reason": recommender.explain_recommendation(anime, preferred_genres),
                "img_url": anime.get('img_url') or "https://via.placeholder.com/200x110?text=无图"
            })

        logger.info(f"为用户 {session['username']} 推荐完成，返回{len(result)}条结果")
        return jsonify(result)

    except Exception as e:
        logger.error(f"推荐处理失败: {str(e)}", exc_info=True)
        return jsonify({"error": "推荐处理失败，请稍后重试"}), 500


@app.route('/anime/<int:uid>')
def anime_detail(uid):
    """动漫详情页"""
    anime = db.get_anime_by_uid(uid) if db else None
    if not anime:
        return "动漫不存在", 404

    reviews = db.get_reviews_by_anime_uid(uid) if db else []

    return render_template('detail.html', anime=anime, reviews=reviews)


@app.route('/popular', methods=['GET'])
def get_popular_animes():
    """获取随机热门动画"""
    try:
        if not db:
            return jsonify({"error": "服务未初始化完成"}), 500

        popular_animes = db.get_popular_animes(top_n=20)
        random.shuffle(popular_animes)
        selected = popular_animes[:6]

        result = []
        for anime in selected:
            try:
                members = int(anime.get('members', 0))
            except (ValueError, TypeError):
                members = 0

            try:
                score = float(anime.get('score', 0.0))
            except (ValueError, TypeError):
                score = 0.0

            result.append({
                "uid": anime.get('uid', ''),
                "title": anime.get('title', '未知标题'),
                "genre": anime.get('genre', []),
                "score": score,
                "members": members,
                "img_url": anime.get('img_url') or "https://via.placeholder.com/200x110?text=无图"
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"获取热门动画失败: {str(e)}", exc_info=True)
        return jsonify({"error": "获取热门动画失败"}), 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="页面未找到"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', message="服务器内部错误"), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)