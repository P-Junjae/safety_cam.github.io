import os
import psycopg2
from flask import Flask, jsonify, request
from datetime import datetime
import json # 用于处理可能的 JSON 类型数据

# --- 配置 ---
app = Flask(__name__)

# 从 Render 提供的环境变量获取数据库连接 URL
# 在 Render 上部署时，这个环境变量会自动设置
DATABASE_URL = os.environ.get('DATABASE_URL')
# 如果在本地测试，可以取消注释下面这行并替换为您自己的本地数据库URL或 Render 外部 URL
# DATABASE_URL = "postgresql://c3p:WvLDvEdBIh8tBY5I3ddTKjinGWAqL33n@dpg-d3gih0ffte5s73c6c7u0-a.singapore-postgres.render.com/safety_cam"


# --- 数据库辅助函数 ---
def get_db_connection():
    """建立数据库连接"""
    if not DATABASE_URL:
        # 在 Render 环境中 DATABASE_URL 必须设置
        # 如果在本地测试且未使用上面的本地 URL，则会报错
        raise ValueError("DATABASE_URL environment variable not set.")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print(f"数据库连接失败: {e}")
        # 在实际应用中，这里应该有更健壮的错误处理和重试机制
        raise

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def home():
    """根路径，返回欢迎信息"""
    return jsonify({
        "message": "安全摄像头项目 API 服务器",
        "status": "运行中"
    })

@app.route('/api/test_db', methods=['GET'])
def test_db_connection():
    """测试数据库连接是否正常"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();") # 查询数据库版本作为测试
        db_version = cursor.fetchone()
        cursor.close()
        return jsonify({"message": "成功连接到 PostgreSQL!", "version": db_version[0]})
    except Exception as e:
        return jsonify({"error": f"数据库连接测试失败: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

# --- 事件相关 Endpoints ---

@app.route('/api/events', methods=['POST'])
def add_event():
    """
    接收来自本地分析脚本的危险事件数据，并将其写入数据库。
    预期 JSON 格式:
    {
      "camera_id": int,         // (可选) 摄像头 ID
      "timestamp": "ISO格式字符串", // 事件发生时间 (例如: "2025-10-27T18:30:00")
      "risk_type": "string",    // 危险类型描述 (例如: "立ち姿勢を検出, 頭が腰より低い状態")
      "score": int,             // 最终得分
      "image_filename": "string" // (推荐) 关联的图片文件名
      "deductions": ["string", ...] // (可选) 具体的扣分原因列表
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "未提供输入数据"}), 400

    # 提取字段
    camera_id = data.get('camera_id', 0) # 如果未提供，默认为 0
    timestamp_str = data.get('timestamp')
    risk_type = data.get('risk_type')
    score = data.get('score')
    image_filename = data.get('image_filename')
    deductions_list = data.get('deductions', []) # 获取扣分列表

    # 数据校验
    if not all([timestamp_str, risk_type, score is not None]):
        missing = [f for f in ['timestamp', 'risk_type', 'score'] if not data.get(f)]
        return jsonify({"success": False, "message": f"缺少必需字段: {', '.join(missing)}"}), 400

    # 转换时间戳
    try:
        # 尝试解析多种可能的 ISO 格式
        event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        try:
             event_time = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            return jsonify({"success": False, "message": "无效的时间戳格式，请使用 ISO 格式 (例如: YYYY-MM-DDTHH:MM:SS)"}), 400


    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 【重要】根据您的实际数据库表结构调整 SQL
        # 假设表名为 'events'
        # 假设 thumbnail_url 存储 image_filename
        # 假设 image_count 暂时存储 1 (因为目前脚本只关联一个文件名)
        # 假设 deductions 存储为 JSON 字符串
        sql = """
        INSERT INTO events (camera_id, event_time, risk_type, score, thumbnail_url, image_count, status, deductions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        cursor.execute(sql, (
            camera_id,
            event_time,
            risk_type,
            score,
            image_filename,
            1,          # image_count 暂时设为 1
            'new',      # status 初始设为 'new'
            json.dumps(deductions_list) # 将列表转为 JSON 字符串存储
        ))
        
        event_id = cursor.fetchone()[0]
        conn.commit()
        
        # --- 触发警报 ---
        # 这里的实现取决于您的警报机制
        # 示例：调用一个发送推送通知的函数
        # send_push_notification(event_id, risk_type, score)
        print(f"事件 {event_id} 已记录，可以触发警报。")

        return jsonify({"success": True, "message": "事件成功添加", "event_id": event_id}), 201
        
    except (Exception, psycopg2.DatabaseError) as error:
        if conn:
            conn.rollback()
        print(f"数据库错误: {error}") # 打印详细错误到服务器日志
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/api/events', methods=['GET'])
def get_events():
    """
    获取危险事件的历史记录列表，支持分页。
    查询参数:
    - page (int, optional, default=1): 页码
    - limit (int, optional, default=20): 每页数量
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
    except ValueError:
        return jsonify({"success": False, "message": "无效的分页参数"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 【重要】根据您的实际数据库表结构调整 SQL
        # 假设按时间倒序排列
        sql = """
        SELECT id, camera_id, event_time, risk_type, score, thumbnail_url, status, deductions
        FROM events
        ORDER BY event_time DESC
        LIMIT %s OFFSET %s;
        """
        cursor.execute(sql, (limit, offset))
        
        events = []
        # 获取列名以便将结果转为字典
        colnames = [desc[0] for desc in cursor.description]
        for row in cursor.fetchall():
            event_dict = dict(zip(colnames, row))
            # 将 datetime 对象转为 ISO 格式字符串，方便 JSON 序列化
            if isinstance(event_dict.get('event_time'), datetime):
                 event_dict['event_time'] = event_dict['event_time'].isoformat()
            # 将 deductions JSON 字符串转回列表
            if isinstance(event_dict.get('deductions'), str):
                try:
                    event_dict['deductions'] = json.loads(event_dict['deductions'])
                except json.JSONDecodeError:
                    event_dict['deductions'] = [] # 解析失败则返回空列表
            events.append(event_dict)
            
        # 获取总数用于分页 (可选但推荐)
        cursor.execute("SELECT COUNT(*) FROM events;")
        total_events = cursor.fetchone()[0]

        return jsonify({
            "success": True,
            "data": events,
            "pagination": {
                "currentPage": page,
                "pageSize": limit,
                "totalItems": total_events,
                "totalPages": (total_events + limit - 1) // limit
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"数据库错误: {error}")
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event_detail(event_id):
    """获取单个事件的详细信息"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 【重要】根据您的实际数据库表结构调整 SQL
        sql = """
        SELECT id, camera_id, event_time, risk_type, score, thumbnail_url, status, deductions
        FROM events
        WHERE id = %s;
        """
        cursor.execute(sql, (event_id,))
        
        row = cursor.fetchone()
        
        if row:
            colnames = [desc[0] for desc in cursor.description]
            event_dict = dict(zip(colnames, row))
            if isinstance(event_dict.get('event_time'), datetime):
                 event_dict['event_time'] = event_dict['event_time'].isoformat()
            if isinstance(event_dict.get('deductions'), str):
                try:
                    event_dict['deductions'] = json.loads(event_dict['deductions'])
                except json.JSONDecodeError:
                    event_dict['deductions'] = []
            return jsonify({"success": True, "data": event_dict})
        else:
            return jsonify({"success": False, "message": "未找到指定 ID 的事件"}), 404

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"数据库错误: {error}")
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

# --- 用户认证 Endpoints (非常基础，仅用于演示) ---
# 【警告】实际生产环境中，绝不能明文存储密码！请使用 bcrypt 等库进行哈希处理！
@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """基础的用户注册 (密码未哈希，不安全!)"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password') # 实际应接收密码，然后哈希处理
    email = data.get('email', f"{username}@example.com") # 默认邮箱
    full_name = data.get('full_name', username)
    role = data.get('role', 'teacher') # 默认角色

    if not username or not password:
        return jsonify({"success": False, "message": "缺少用户名或密码"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "用户名已存在"}), 409
            
        # 【警告】直接存储密码极不安全！应存储哈希值。
        sql = """
        INSERT INTO users (username, password_hash, email, full_name, role) 
        VALUES (%s, %s, %s, %s, %s) RETURNING id;
        """
        cursor.execute(sql, (username, password, email, full_name, role))
        user_id = cursor.fetchone()[0]
        conn.commit()
        
        return jsonify({"success": True, "message": "注册成功", "user_id": user_id}), 201

    except (Exception, psycopg2.DatabaseError) as error:
        if conn: conn.rollback()
        print(f"数据库错误: {error}")
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """基础的用户登录 (密码明文比较，不安全!)"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "缺少用户名或密码"}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 【警告】直接比较密码极不安全！应比较哈希值。
        sql = "SELECT id, password_hash FROM users WHERE username = %s"
        cursor.execute(sql, (username,))
        result = cursor.fetchone()
        
        if result and result[1] == password: # 比较明文密码
            user_id = result[0]
            # 实际应用中，这里应生成一个 JWT Token 并返回
            return jsonify({"success": True, "message": "登录成功", "user_id": user_id, "token": "dummy_token_for_demo"})
        else:
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"数据库错误: {error}")
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            cursor.close()
            conn.close()


# --- 其他 Endpoints (根据企划书可后续添加) ---
# GET /api/cameras - 获取摄像头列表
# GET /api/cameras/{id}/stream - 获取某个摄像头的视频流信息
# POST /api/feedback - 提交误报反馈
# GET /api/reports - 获取定期报告列表
# POST /api/alert - (内部或脚本调用) 触发警报


# --- 启动服务器 ---
if __name__ == '__main__':
    # 获取端口号，Render 会通过 PORT 环境变量指定
    port = int(os.environ.get('PORT', 5000)) 
    print(f"--- Flask API サーバーをポート {port} で起動します ---")
    # 使用 Waitress 作为生产环境服务器 (如果已安装)
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        print("警告: waitress がインストールされていません。Flask の開発サーバーを使用します（本番環境には非推奨）。")
        # debug=False 用于生产环境或 Render 部署
        # host='0.0.0.0' 允许外部访问
        app.run(host='0.0.0.0', port=port, debug=False)

#```

### **如何使用和部署**

#1.  **保存代码**: 将上面的代码保存为 `render_api.py` (或者您喜欢的名字，例如 `app.py`)。
#2.  **安装依赖**: 在您的 `py310-mmpose-stable` 环境中，确保安装了 Flask 和 psycopg2:
#    ```cmd
#    conda activate py310-mmpose-stable
#    pip install Flask psycopg2-binary waitress
#    ```
#3.  **配置环境变量 (本地测试)**: 如果您想在本地运行这个 API 进行测试，需要设置 `DATABASE_URL` 环境变量。在 CMD 中可以这样设置 (仅对当前窗口有效)：
#    ```cmd
#    set DATABASE_URL=postgresql://c3p:WvLDvEdBIh8tBY5I3ddTKjinGWAqL33n@dpg-d3gih0ffte5s73c6c7u0-a.singapore-postgres.render.com/safety_cam
#    python render_api.py
    
