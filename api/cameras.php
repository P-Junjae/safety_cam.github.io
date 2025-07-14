<?php
// api/cameras.php
require_once('../config.php'); // config.phpのパスを適切に修正
header('Content-Type: application/json');

try {
    $stmt = $pdo->query("SELECT id, name, stream_url FROM cameras");
    $cameras = $stmt->fetchAll(PDO::FETCH_ASSOC);
    echo json_encode($cameras);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Failed to load cameras: ' . $e->getMessage()]);
}
?>