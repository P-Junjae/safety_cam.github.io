<?php
// api/feedback.php
require_once('../config.php');
header('Content-Type: application/json');

$data = json_decode(file_get_contents('php://input'), true);

if (!isset($data['imageUrl'])) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Image URL is required.']);
    exit();
}

$imageUrl = $data['imageUrl'];
// 仮の user_id。実際にはログインセッションから取得する
$user_id = 1; // 適当なユーザーIDを設定（例: 管理者ユーザーのIDなど）

try {
    // image_urlからevent_imagesのIDを取得
    $stmt_img = $pdo->prepare("SELECT id FROM event_images WHERE image_url = :image_url");
    $stmt_img->bindParam(':image_url', $imageUrl);
    $stmt_img->execute();
    $image = $stmt_img->fetch(PDO::FETCH_ASSOC);

    if (!$image) {
        http_response_code(404);
        echo json_encode(['success' => false, 'message' => 'Image not found in database.']);
        exit();
    }
    $image_id = $image['id'];

    // feedbackテーブルに挿入
    $pdo->beginTransaction(); // トランザクション開始
    $stmt = $pdo->prepare("INSERT INTO feedback (image_id, user_id, notes) VALUES (:image_id, :user_id, :notes)"); // カラム名を修正
    $stmt->bindParam(':image_id', $image_id, PDO::PARAM_INT);
    $stmt->bindParam(':user_id', $user_id, PDO::PARAM_INT);
    $notes = "Misdetection reported from frontend."; // 仮のメモ
    $stmt->bindParam(':notes', $notes);
    $stmt->execute();

    // event_imagesテーブルのhas_feedbackを更新
    $stmt_update = $pdo->prepare("UPDATE event_images SET has_feedback = 1 WHERE id = :image_id");
    $stmt_update->bindParam(':image_id', $image_id, PDO::PARAM_INT);
    $stmt_update->execute();

    $pdo->commit(); // トランザクションコミット
    echo json_encode(['success' => true, 'message' => 'Feedback submitted successfully.']);
} catch (PDOException $e) {
    $pdo->rollBack(); // エラー時はロールバック
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Failed to submit feedback: ' . $e->getMessage()]);
}
?>