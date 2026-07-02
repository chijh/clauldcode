# つくば市の天気を Genie CLI で取得し、Windows のトースト通知で表示する。
# タスクスケジューラから毎朝呼び出される想定（Windows PowerShell 5.1 で動作）。

$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'

# Python 本体（PATH の Store スタブを避けるため実体を優先）
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = 'python' }

$main = Join-Path $PSScriptRoot '..\main.py'

# 天気を取得（失敗しても通知は出す）
try {
    $text = (& $py $main 今日の天気 2>&1 | Out-String).Trim()
} catch {
    $text = "天気の取得に失敗しました: $($_.Exception.Message)"
}
if (-not $text) { $text = '天気を取得できませんでした。' }

# XML エスケープ（天気文に念のため）
$body = $text -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;'
$title = 'つくば市の天気（Genie）'

# WinRT トースト通知
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime]        | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]          | Out-Null

$xml = @"
<toast>
  <visual>
    <binding template="ToastGeneric">
      <text>$title</text>
      <text>$body</text>
    </binding>
  </visual>
</toast>
"@

$doc = New-Object Windows.Data.Xml.Dom.XmlDocument
$doc.LoadXml($xml)

# PowerShell を発信元アプリとして通知（AppUserModelID）
$appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
$toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)

