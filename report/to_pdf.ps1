param([string]$In, [string]$Out)
# Converts a .docx to PDF with Microsoft Word (needed to read the real page numbers for the contents lists).
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($In, $false, $true)
    $doc.ExportAsFixedFormat($Out, 17)
    $doc.Close(0)
} finally {
    $word.Quit()
}
Write-Output "pdf: $Out"
