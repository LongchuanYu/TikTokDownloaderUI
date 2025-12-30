import requests
import os
# 导入URL解析模块
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "change_this_secret_key"

# 登录态有效期 7 天
app.permanent_session_lifetime = timedelta(days=7)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DW_DIR = "/home/liyang/Downloads/DoukDownload"

# =====================
# 模拟用户（你可以换数据库）
# =====================
USERS = {
    "admin": {
        "id": "1",
        "password": "123456"
    }
}

def remote_url(api_url):
    return f'http://localhost:5555{api_url}'

def parse_dy_url(dy_url):
    try:
        # 定义目标URL字符串
        url = dy_url

        # 解析URL，获取路径部分
        parsed_url = urlparse(url)
        path = parsed_url.path  # 路径结果：'/video/7579559651487629978'

        # 从路径中提取数字（分割路径字符串）
        target_number = path.split("/")[-1]  # 按"/"分割后取最后一个元素
        return target_number
    except Exception as e:
        print(f'parse dy url failed: {e}')
        return ''

def download_small_file_by_requests(url, save_path):
    """
    requests下载小文件（直接读取后写入）
    :param url: 目标资源URL
    :param save_path: 本地保存路径（含文件名）
    """
    try:
        # 构造请求头（模拟浏览器，避免部分网站反爬）
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # 发送GET请求获取资源
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # 抛出HTTP请求错误（如404、500）
        
        # 确保保存目录存在
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # 写入本地文件（二进制模式wb适合所有文件类型：视频、图片、文档等）
        with open(save_path, "wb") as f:
            f.write(response.content)
        
        return ''
    except requests.exceptions.RequestException as e:
        err_msg = f"小文件下载失败（HTTP请求错误）：{str(e)}"
        return err_msg
    except Exception as e:
        err_msg = f"小文件下载失败：{str(e)}"
        return err_msg

class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

class Response:
    def __init__(self):
        self._success = True
        self._result = None

    def _res(self):
        return jsonify({
            'success': self._success,
            'result': self._result
        })

    def success(self, result):
        self._result = result
        return self._res()

    def error(self, result):
        self._success = False
        self._result = result
        return self._res()

@login_manager.user_loader
def load_user(user_id):
    for username, info in USERS.items():
        if info["id"] == user_id:
            return User(info["id"], username)
    return None

# =====================
# 登录页
# =====================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user_info = USERS.get(username)
        if user_info and user_info["password"] == password:
            user = User(user_info["id"], username)
            login_user(user, remember=True)  # remember=True → 7天
            return redirect(url_for("home"))

        return render_template("login.html", error="用户名或密码错误")

    return render_template("login.html")

# =====================
# 主页（你自己写内容）
# =====================
@app.route("/")
@login_required
def home():
    return render_template("home.html")
    
@app.route("/api/confirm", methods=["POST"])
@login_required
def confirm_api():
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return Response().error('输入内容为空')

    # ===== 这里写你的业务逻辑 =====
    res = requests.post(remote_url('/douyin/share'), json={ 'text': text })
    if (res.status_code != 200):
        print(res.json())
        return Response().error("解析分享连接失败")
    res_json = res.json()
    share_url = res_json.get('url')
    detail_id = parse_dy_url(share_url)
    if not detail_id:
        return Response().error('解析deail_id失败')

    res = requests.post(remote_url('/douyin/detail'), json={ 'detail_id': detail_id })
    if (res.status_code != 200):
        print(res.json())
        return Response().error("获取作品详情失败")
    res_json = res.json()
    
    try:
        data = res_json['data']
        download_url = data['downloads']
        desc = data['desc']
    except Exception as e:
        print(res.json())
        return Response().error("detail字段获取错误")

    dw_path = os.path.join(DW_DIR, desc[:10])

    err_msg = download_small_file_by_requests(download_url, dw_path)
    if err_msg:
        return Response().error(f"下载失败: {err_msg}")

    return Response().success("成功")

# =====================
# 退出登录
# =====================
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
