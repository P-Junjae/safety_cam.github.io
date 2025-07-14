<?php
// api/report_detail.php
require_once('../config.php');
header('Content-Type: application/json');

$report_id = isset($_GET['id']) ? $_GET['id'] : ''; // IDはここでは使わないが、APIの形式に合わせる

// ここではダミーデータを返すが、実際にはIDに基づいて詳細な統計を生成する
// もしreportsテーブルからデータを取得する場合の例 (summary_dataはJSONなのでデコード)
/*
$stmt = $pdo->prepare("SELECT summary_data FROM reports WHERE id = :id");
$stmt->bindParam(':id', $report_id);
$stmt->execute();
$report_data = $stmt->fetch(PDO::FETCH_ASSOC);
$stats = $report_data ? json_decode($report_data['summary_data'], true) : [];
*/

$dummy_stats = [
    ['label' => '人物検知', 'value' => 30],
    ['label' => 'ペット検知', 'value' => 15],
    ['label' => '車両検知', 'value' => 10],
    ['label' => 'その他', 'value' => 5],
];

echo json_encode(['id' => $report_id, 'stats' => $dummy_stats]);
?>