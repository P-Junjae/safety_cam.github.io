<?php
// api/reports.php
require_once('../config.php');
header('Content-Type: application/json');

$type = isset($_GET['type']) ? $_GET['type'] : 'monthly'; // 'monthly' or 'yearly'

try {
    $reports = [];
    if ($type === 'monthly') {
        // event_time を使用
        $stmt = $pdo->query("SELECT
            DATE_FORMAT(event_time, '%Y-%m') AS monthOrYear,
            COUNT(*) AS total
            FROM events
            GROUP BY monthOrYear
            ORDER BY monthOrYear DESC");
    } elseif ($type === 'yearly') {
        // event_time を使用
        $stmt = $pdo->query("SELECT
            DATE_FORMAT(event_time, '%Y') AS monthOrYear,
            COUNT(*) AS total
            FROM events
            GROUP BY monthOrYear
            ORDER BY monthOrYear DESC");
    } else {
        http_response_code(400);
        echo json_encode(['success' => false, 'message' => 'Invalid report type.']);
        exit();
    }
    $reports = $stmt->fetchAll(PDO::FETCH_ASSOC);

    // IDは適当に生成（実際のreportsテーブルのidがあればそれを使う）
    // 現状 reports テーブルは自動生成ではないため、event_timeに基づく集計はIDを持たない
    // ここでは引き続き仮のIDを生成し、フロントエンドの表示に合わせる
    foreach ($reports as &$report) {
        $report['id'] = md5($report['monthOrYear'] . $report['total']); // 仮のID生成
    }

    echo json_encode($reports);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Failed to load reports: ' . $e->getMessage()]);
}
?>