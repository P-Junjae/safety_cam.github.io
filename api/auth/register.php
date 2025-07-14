<?php
// api/auth/register.php
require_once('../../config.php');
header('Content-Type: application/json');

$data = json_decode(file_get_contents('php://input'), true);

if (!isset($data['username']) || !isset($data['password'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Username and password are required.']);
    exit();
}

$username = $data['username'];
$password_hash = password_hash($data['password'], PASSWORD_DEFAULT); // カラム名に合わせて変更

// 新規追加されたカラムのデフォルト値（仮）
$email = $username . '@example.com';
$full_name = '名無し';
$role = 'user'; // デフォルトロール

try {
    $stmt = $pdo->prepare("INSERT INTO users (username, password_hash, email, full_name, role) VALUES (:username, :password_hash, :email, :full_name, :role)"); // カラム名と追加カラムを修正
    $stmt->bindParam(':username', $username);
    $stmt->bindParam(':password_hash', $password_hash); // カラム名に合わせて変更
    $stmt->bindParam(':email', $email);
    $stmt->bindParam(':full_name', $full_name);
    $stmt->bindParam(':role', $role);
    $stmt->execute();
    echo json_encode(['success' => true, 'message' => 'User registered successfully.']);
} catch (PDOException $e) {
    if ($e->getCode() == 23000) { // Duplicate entry for unique key (username or email)
        http_response_code(409); // Conflict
        echo json_encode(['success' => false, 'message' => 'Username or email already exists.']);
    } else {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => 'Registration failed: ' . $e->getMessage()]);
    }
}
?>