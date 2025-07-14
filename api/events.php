<?php
// api/events.php
require_once('../config.php');
header('Content-Type: application/json');

$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
$limit = 10; // 1ページあたりの表示数
$offset = ($page - 1) * $limit;

try {
    // risk_type (旧 type), thumbnail_url (旧 thumbnail_url), event_time (旧 event_date)
    $stmt = $pdo->prepare("SELECT id, risk_type, thumbnail_url, event_time FROM events ORDER BY event_time DESC LIMIT :limit OFFSET :offset"); // カラム名を修正
    $stmt->bindParam(':limit', $limit, PDO::PARAM_INT);
    $stmt->bindParam(':offset', $offset, PDO::PARAM_INT);
    $stmt->execute();
    $events = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // 日付フォーマットをJavaScriptに合わせて調整
    foreach ($events as &$event) {
        $event['date'] = (new DateTime($event['event_time']))->format('Y-m-d H:i:s'); // カラム名が event_time に変更
        $event['type'] = $event['risk_type']; // フロントエンドのキー名に合わせる
        $event['thumbnail'] = $event['thumbnail_url']; // フロントエンドのキー名に合わせる
        unset($event['event_time']);
        unset($event['risk_type']);
        unset($event['thumbnail_url']);
    }

    echo json_encode($events);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Failed to load events: ' . $e->getMessage()]);
}
?>