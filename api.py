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
      "equipment_type": "string", // 设备类型 (例如: "slide", "climbing", "swing")
      "timestamp": "ISO格式字符串", // 事件发生时间 (例如: "2025-10-27T18:30:00")
      "risk_type": "string",    // 【修改】现在是 "abnormal" 或 "normal"
      "score": int,             // 最终得分
      "image_filename": "string" // (推荐) 关联的图片文件名
      "deductions": ["string", ...] // (可选) 具体的扣分原因列表 (当 risk_type 为 "abnormal" 时应提供)
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "未提供输入数据"}), 400

    # 提取字段
    camera_id = data.get('camera_id', 0)
    equipment_type = data.get('equipment_type')
    timestamp_str = data.get('timestamp')
    risk_type = data.get('risk_type') # 现在是 "abnormal" 或 "normal"
    score = data.get('score')
    image_filename = data.get('image_filename')
    deductions_list = data.get('deductions', [])

    # 数据校验 (增加了 equipment_type)
    if not all([equipment_type, timestamp_str, risk_type, score is not None]):
        missing = [f for f in ['equipment_type', 'timestamp', 'risk_type', 'score'] if not data.get(f)]
        return jsonify({"success": False, "message": f"缺少必需字段: {', '.join(missing)}"}), 400

    # 【新】校验 risk_type 的值
    if risk_type not in ["normal", "abnormal"]:
        return jsonify({"success": False, "message": "无效的 risk_type 值，必须是 'normal' 或 'abnormal'"}), 400


    # 转换时间戳
    try:
        # 尝试解析带时区信息的 ISO 格式
        event_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        try:
             # 尝试解析不带时区信息的 ISO 格式 (可能带毫秒)
             event_time = datetime.strptime(timestamp_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return jsonify({"success": False, "message": "无效的时间戳格式，请使用 ISO 格式 (例如: YYYY-MM-DDTHH:MM:SS 或带 Z/时区)"}), 400


    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL 语句增加了 equipment_type 列
        # 假设 thumbnail_url 存储 image_filename, image_count 暂时存储 1
        # 假设 deductions 列类型为 JSONB 或 TEXT
        sql = """
        INSERT INTO events (camera_id, equipment_type, event_time, risk_type, score, thumbnail_url, image_count, status, deductions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """
        # 将 deductions_list 转为 JSON 字符串以便存入 TEXT 或 JSONB 列
        deductions_json = json.dumps(deductions_list)

        cursor.execute(sql, (
            camera_id,
            equipment_type,
            event_time,
            risk_type, # 使用传入的 "normal" 或 "abnormal"
            score,
            image_filename,
            1,          # image_count 暂时设为 1
            'new',      # status 初始设为 'new'
            deductions_json # 存入 JSON 字符串
        ))

        event_id = cursor.fetchone()[0]
        conn.commit()

        # --- 触发警报 ---
        # 【修改】判断条件改为 "abnormal"
        if risk_type == "abnormal":
            # send_push_notification(event_id, equipment_type, score, deductions_list)
            print(f"事件 {event_id} ({equipment_type}) 已记录为 abnormal，可以触发警报。")
        else:
            print(f"事件 {event_id} ({equipment_type}) 已记录为 normal。")


        return jsonify({"success": True, "message": "事件成功添加", "event_id": event_id}), 201

    except (Exception, psycopg2.DatabaseError) as error:
        if conn:
            conn.rollback()
        print(f"数据库错误: {error}") # 打印详细错误到服务器日志
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            # 确保游标总能被关闭
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()

@app.route('/api/events', methods=['GET'])
def get_events():
    """
    获取事件的历史记录列表，支持分页。
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

        # SQL 语句增加了 equipment_type 列
        sql_data = """
        SELECT id, camera_id, equipment_type, event_time, risk_type, score, thumbnail_url, status, deductions
        FROM events
        ORDER BY event_time DESC
        LIMIT %s OFFSET %s;
        """
        cursor.execute(sql_data, (limit, offset))

        events = []
        # 获取列名以便将结果转为字典
        colnames = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        for row in rows:
            event_dict = dict(zip(colnames, row))
            # 将 datetime 对象转为 ISO 格式字符串，方便 JSON 序列化
            if isinstance(event_dict.get('event_time'), datetime):
                 event_dict['event_time'] = event_dict['event_time'].isoformat() + 'Z' # 添加 Z 表示 UTC 或无时区
            # 将 deductions JSON 字符串转回列表 (如果数据库存的是字符串)
            # 如果数据库列类型是 JSONB, psycopg2 可能已经自动转换了
            deductions_data = event_dict.get('deductions')
            if isinstance(deductions_data, str):
                try:
                    event_dict['deductions'] = json.loads(deductions_data)
                except json.JSONDecodeError:
                    event_dict['deductions'] = [] # 解析失败则返回空列表
            elif deductions_data is None:
                 event_dict['deductions'] = [] # 处理 NULL 值
            # 如果 deductions_data 已经是 list (JSONB 列)，则无需处理

            events.append(event_dict)

        # 获取总数用于分页
        sql_count = "SELECT COUNT(*) FROM events;"
        cursor.execute(sql_count)
        total_events = cursor.fetchone()[0]

        return jsonify({
            "success": True,
            "data": events,
            "pagination": {
                "currentPage": page,
                "pageSize": limit,
                "totalItems": total_events,
                "totalPages": (total_events + limit - 1) // limit if limit > 0 else 0
            }
        })

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"数据库错误: {error}")
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            if 'cursor' in locals() and cursor:
                cursor.close()
            conn.close()

@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event_detail(event_id):
    """获取单个事件的详细信息"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # SQL 语句增加了 equipment_type 列
        sql = """
        SELECT id, camera_id, equipment_type, event_time, risk_type, score, thumbnail_url, status, deductions
        FROM events
        WHERE id = %s;
        """
        cursor.execute(sql, (event_id,))

        row = cursor.fetchone()

        if row:
            colnames = [desc[0] for desc in cursor.description]
            event_dict = dict(zip(colnames, row))
            if isinstance(event_dict.get('event_time'), datetime):
                 event_dict['event_time'] = event_dict['event_time'].isoformat() + 'Z'
            deductions_data = event_dict.get('deductions')
            if isinstance(deductions_data, str):
                try:
                    event_dict['deductions'] = json.loads(deductions_data)
                except json.JSONDecodeError:
                    event_dict['deductions'] = []
            elif deductions_data is None:
                 event_dict['deductions'] = []
            return jsonify({"success": True, "data": event_dict})
        else:
            return jsonify({"success": False, "message": "未找到指定 ID 的事件"}), 404

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"数据库错误: {error}")
        return jsonify({"success": False, "message": f"数据库错误: {str(error)}"}), 500
    finally:
        if conn:
            if 'cursor' in locals() and cursor:
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
        # 假设 password_hash 列实际存储明文 (仅用于演示)
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
            if 'cursor' in locals() and cursor:
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
            if 'cursor' in locals() and cursor:
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
        print("--- Waitress サーバーを使用します ---")
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        print("警告: waitress がインストールされていません。Flask の開発サーバーを使用します（本番環境には非推奨）。")
        # debug=False 用于生产环境或 Render 部署
        # host='0.0.0.0' 允许外部访问
        app.run(host='0.0.0.0', port=port, debug=False)

