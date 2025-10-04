<?php
// config.phpの読み込み
require_once '../../config.php';

// ヘッダー設定
header('Content-Type: application/json');

// HTTPメソッドがPOSTであるかを確認
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method Not Allowed']);
    exit;
}

// JSONデータを取得し、デコード
$data = json_decode(file_get_contents('php://input'), true);

// 必要なデータが揃っているか確認
if (!isset($data['username']) || !isset($data['password'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Missing username or password']);
    exit;
}

$username = $data['username'];
$password = $data['password'];

try {
    // データベース接続
    $pdo = new PDO(
        "mysql:host=" . DB_SERVER . ";port=" . DB_PORT . ";dbname=" . DB_NAME,
        DB_USERNAME,
        DB_PASSWORD
    );
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // ユーザー名の重複チェック
    $stmt = $pdo->prepare("SELECT COUNT(*) FROM users WHERE username = ?");
    $stmt->execute([$username]);
    if ($stmt->fetchColumn() > 0) {
        http_response_code(409); // Conflict
        echo json_encode(['success' => false, 'message' => 'Username already exists.']);
        exit;
    }

    // パスワードのハッシュ化（必須のセキュリティ対策）
    $hashedPassword = password_hash($password, PASSWORD_DEFAULT);

    // ユーザー情報をデータベースに登録
    // role, email, full_nameは仮の値
    $sql = "INSERT INTO users (username, password_hash, email, full_name, role) VALUES (?, ?, ?, ?, ?)";
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$username, $hashedPassword, 'dummy@example.com', '新規ユーザー', 'teacher']);

    // 登録成功
    http_response_code(201); // Created
    echo json_encode(['success' => true, 'message' => 'Registration successful!']);

} catch (PDOException $e) {
    // データベースエラー
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Database error: ' . $e->getMessage()]);
}
?>
