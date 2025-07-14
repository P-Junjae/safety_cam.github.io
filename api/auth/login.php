<?php
// api/auth/login.php
require_once('../../config.php');
header('Content-Type: application/json');

// エラー表示を有効にする（デバッグ時のみ）
ini_set('display_errors', 1);
error_reporting(E_ALL);

$data = json_decode(file_get_contents('php://input'), true);

if (!isset($data['username']) || !isset($data['password'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Username and password are required.']);
    exit();
}

$username = $data['username'];
$password = $data['password'];

try {
    $stmt = $pdo->prepare("SELECT id, username, password_hash FROM users WHERE username = :username");
    $stmt->bindParam(':username', $username);
    $stmt->execute();
    $user = $stmt->fetch(PDO::FETCH_ASSOC);

    // デバッグ情報を追加
    error_log("Login attempt for username: " . $username);
    error_log("Fetched user data: " . print_r($user, true));
    if ($user) {
        error_log("Stored password hash: " . $user['password_hash']);
        error_log("Password verify result: " . (password_verify($password, $user['password_hash']) ? 'TRUE' : 'FALSE'));
    }

    if ($user && password_verify($password, $user['password_hash'])) {
        // ログイン成功
        echo json_encode(['success' => true, 'message' => 'Login successful.']);
    } else {
        // ログイン失敗
        http_response_code(401); // Unauthorized
        echo json_encode(['success' => false, 'message' => 'Invalid username or password.']);
    }
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Login failed: ' . $e->getMessage()]);
}
?>