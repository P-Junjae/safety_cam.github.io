<?php
// config.php
define('DB_SERVER', 'https://p-junjae.github.io/safety_cam.github.io/');
define('DB_USERNAME', 'root');
define('DB_PASSWORD', '');
define('DB_NAME', 'safety_cam');
define('DB_PORT', 3306);

// CORS設定（開発環境用。本番では特定のオリジンに限定する）
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS, PUT, DELETE');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// プリフライトリクエストの処理
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    exit(0);
}

// データベース接続
try {
    $pdo = new PDO(
        "mysql:host=" . DB_SERVER . ";port=" . DB_PORT . ";dbname=" . DB_NAME,
        DB_USERNAME,
        DB_PASSWORD
    );
    // 修正点: PDO_ERRMODE_EXCEPTION の前に PDO:: を追加
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION); // ここを修正！
    $pdo->exec("set names utf8");
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Database connection failed: ' . $e->getMessage()]);
    exit();
}
?>
