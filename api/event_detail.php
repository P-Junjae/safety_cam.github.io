<?php
// api/event_detail.php
require_once('../config.php');
header('Content-Type: application/json');

$event_id = isset($_GET['id']) ? (int)$_GET['id'] : 0;

if ($event_id === 0) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Event ID is required.']);
    exit();
}

try {
    // risk_type (旧 type), thumbnail_url (旧 large_thumbnail_url), event_time (旧 event_date)
    // safety_cam.sql の events テーブルには large_thumbnail_url がありません。
    // thumbnail_url を largeThumbnail としても使いますが、必要に応じて別途用意するか、
    // image_url の一番最初を代表画像として使うなど調整が必要です。
    $stmt = $pdo->prepare("SELECT id, risk_type, thumbnail_url, event_time, image_count FROM events WHERE id = :id"); // カラム名を修正
    $stmt->bindParam(':id', $event_id, PDO::PARAM_INT);
    $stmt->execute();
    $event = $stmt->fetch(PDO::FETCH_ASSOC);

    if ($event) {
        // 画像を取得
        // event_images テーブルのカラム名が image_url に変更
        $stmt_images = $pdo->prepare("SELECT image_url FROM event_images WHERE event_id = :event_id ORDER BY timestamp ASC");
        $stmt_images->bindParam(':event_id', $event_id, PDO::PARAM_INT);
        $stmt_images->execute();
        $images_raw = $stmt_images->fetchAll(PDO::FETCH_COLUMN);

        $event['date'] = (new DateTime($event['event_time']))->format('Y-m-d H:i:s'); // カラム名が event_time に変更
        $event['type'] = $event['risk_type']; // フロントエンドのキー名に合わせる
        // largeThumbnail は thumbnail_url を流用。もし異なる画像が必要ならデータベース設計見直し。
        $event['largeThumbnail'] = $event['thumbnail_url'];
        $event['images'] = $images_raw; // URLの配列を直接渡す
        $event['detectedImageCount'] = $event['image_count']; // 新しいキー名に合わせる

        unset($event['event_time']);
        unset($event['risk_type']);
        unset($event['thumbnail_url']);
        unset($event['image_count']); // 元のカラムはもう使わない

        echo json_encode($event);
    } else {
        http_response_code(404);
        echo json_encode(['success' => false, 'message' => 'Event not found.']);
    }
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Failed to load event detail: ' . $e->getMessage()]);
}
?>