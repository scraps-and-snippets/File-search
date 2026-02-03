$pattern = "your_search_string"
$context = 5
Get-ChildItem -Recurse -File -Include *.cpp,*.h,*.hpp,*.cxx,*.cc,*.inl |
  Select-String -Pattern $pattern -Context $context,$context |
  ForEach-Object {
    # Header per match
    "FILE: $($_.Path)"
    "MATCH LINE: $($_.LineNumber)"
    # Output context block (pre + match + post)
    ($_.Context.PreContext + $_.Line + $_.Context.PostContext) -join "`r`n"
    "`r`n----`r`n"
  } | Out-File -Encoding utf8 results.txt
