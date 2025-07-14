<?php
// api/camera_stream.php
require_once('../config.php');
header('Content-Type: application/json');

$camera_id = isset($_GET['id']) ? (int)$_GET['id'] : 0;

if ($camera_id === 0) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Camera ID is required.']);
    exit();
}

try {
    $stmt = $pdo->prepare("SELECT stream_url FROM camera WHERE id = :id AND is_active = 1"); // テーブル名が camera に変更, is_active も考慮
    $stmt->bindParam(':id', $camera_id, PDO::PARAM_INT);
    $stmt->execute();
    $camera = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($camera) {
        echo json_encode(['streamUrl' => $camera['stream_url']]);
    } else {
        http_response_code(404);
        echo json_encode(['success' => false, 'message' => 'Camera not found or not active.']);
    }
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Failed to get stream: ' . $e->getMessage()]);
}
?>