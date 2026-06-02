#!/usr/bin/env bash
# 논문 자동 다운로드. 사용법: bash scripts/fetch_papers.sh
# 키는 OneDrive 밖 ~/.config/research_keys.env 에서 읽음 (ELSEVIER_API_KEY, WILEY_TDM_TOKEN).
set -u
KEYS="${RESEARCH_KEYS:-$HOME/.config/research_keys.env}"
[ -f "$KEYS" ] || KEYS="/c/Users/TUPA/.config/research_keys.env"
if [ -f "$KEYS" ]; then set -a; . "$KEYS"; set +a; else echo "키 파일 없음: $KEYS"; fi
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$(cd "$HERE/../pdfs" && pwd)"
XMLDIR="$OUT/_xml"; mkdir -p "$XMLDIR"
MAN="$HERE/papers.tsv"
UA="Mozilla/5.0 (research TDM)"
ok=0; fail=0; fails=""
while IFS=$'\t' read -r fname method id rest; do
  case "${fname:-}" in ''|\#*) continue;; esac
  [ -z "${method:-}" ] && continue
  dest="$OUT/$fname"
  if [ "${FORCE:-0}" != "1" ] && [ -s "$dest" ] && [ "$(head -c4 "$dest" 2>/dev/null)" = "%PDF" ]; then echo "SKIP  $fname (이미 있음)"; ok=$((ok+1)); continue; fi
  case "$method" in
    elsevier) base="${fname%.pdf}"
              # 신뢰 소스: 전문 XML -> 텍스트 (모든 Elsevier 제목에서 안정적으로 추출됨)
              curl -s -L -A "$UA" -H "X-ELS-APIKey: ${ELSEVIER_API_KEY:-}" -H "Accept: text/xml" -o "$XMLDIR/$base.xml" "https://api.elsevier.com/content/article/doi/$id"
              sed -e 's/<[^>]*>/ /g' "$XMLDIR/$base.xml" 2>/dev/null | tr -s ' \n' ' \n' > "$XMLDIR/$base.txt"
              xw=$(wc -w < "$XMLDIR/$base.txt" 2>/dev/null)
              # 읽기용 PDF (일부 제목은 이미지/미리보기일 수 있음 — 텍스트는 XML에서 확보)
              code=$(curl -s -L -A "$UA" -H "X-ELS-APIKey: ${ELSEVIER_API_KEY:-}" -H "Accept: application/pdf" -o "$dest" -w "%{http_code}" "https://api.elsevier.com/content/article/doi/$id");;
    wiley)    url="https://api.wiley.com/onlinelibrary/tdm/v1/articles/$id"
              code=$(curl -s -L -A "$UA" -H "Wiley-TDM-Client-Token: ${WILEY_TDM_TOKEN:-}" -o "$dest" -w "%{http_code}" "$url");;
    arxiv)    code=$(curl -s -L -A "$UA" -o "$dest" -w "%{http_code}" "https://arxiv.org/pdf/$id");;
    url)      code=$(curl -s -L -A "$UA" -o "$dest" -w "%{http_code}" "$id");;
    *) echo "?? unknown method '$method' for $fname"; continue;;
  esac
  sig=$(head -c 4 "$dest" 2>/dev/null); sz=$(wc -c < "$dest" 2>/dev/null)
  if [ "$sig" = "%PDF" ]; then printf "OK    %-42s http=%s %8s B\n" "$fname" "$code" "$sz"; ok=$((ok+1))
  else printf "FAIL  %-42s (%s %s) http=%s %sB\n" "$fname" "$method" "$id" "$code" "$sz"; fail=$((fail+1)); fails="$fails $fname"; rm -f "$dest"; fi
  [ "$method" = elsevier ] && echo "        ↳ 전문 XML(_xml/): ${xw:-?} 단어"
done < "$MAN"
echo "------------------------------------------------------------"
echo "완료: $ok 성공, $fail 실패.${fails:+  실패:$fails}"
