Get-ChildItem -Recurse -File -Include *.py,*.md |
  Where-Object {
    $_.FullName -notmatch '[\\/]\.[^\\/]+([\\/]|$)'
  } |
  Sort-Object FullName |
  ForEach-Object {
    $relativePath = Resolve-Path -Relative $_.FullName
    $ext = $_.Extension.TrimStart(".")

    @"
$relativePath
````$ext
$(Get-Content $_.FullName -Raw)
`````

"@
} | Set-Clipboard
