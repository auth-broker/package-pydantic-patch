find . -type d -name ".venv" -prune -o -type f \( -name "*.py" -o -name "*.md" \) -print |
sort | while IFS= read -r file; do
  ext="${file##*.}"
  rel="${file#./}"

  printf '%s\n' "$rel"
  printf '```%s\n' "$ext"
  cat "$file"
  printf '\n```\n\n'
done | pbcopy