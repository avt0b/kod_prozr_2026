#!/usr/bin/env bash
# Выкладка релиза на стенде (OPS-09). Запускается на хосте из каталога деплоя.
# Обычно его вызывает .github/workflows/release.yml по ssh; вручную — для отката и статуса.
#
#   deploy/deploy.sh deploy <tag> <image-prefix> [<registry-user>]
#       pull образов <image-prefix>/{backend,frontend}:<tag>, бэкап БД, миграции, up,
#       health + smoke. При провале — автоматический откат на предыдущий успешный тег.
#       Если передан <registry-user>, токен GHCR читается из stdin (в лог не попадает).
#   deploy/deploy.sh rollback      вернуть предыдущий успешный тег (вручную)
#   deploy/deploy.sh status        текущий и предыдущий теги, состояние контейнеров
#
# Состояние хранится в .release/ рядом с docker-compose.yml:
#   current_tag, previous_tag, image_prefix, history.log; бэкапы БД — в backups/.
# Переменные: API_URL (http://127.0.0.1:8000), SMOKE_ARGS (--keep-demo),
#   DEPLOY_SEED=true — залить data/generated после миграций (только первый деплой на пустую БД).
set -Eeuo pipefail

cd "$(dirname "$0")/.."

STATE_DIR=.release
BACKUP_DIR=backups
API_URL=${API_URL:-http://127.0.0.1:8000}
SMOKE_ARGS=${SMOKE_ARGS:---keep-demo}
WAIT_TIMEOUT=${WAIT_TIMEOUT:-300}
COMPOSE=(docker compose -f docker-compose.yml -f deploy/docker-compose.release.yml)

log() { printf '[deploy] %s\n' "$*"; }
die() { printf '[deploy] ОШИБКА: %s\n' "$*" >&2; exit 1; }

state() { cat "$STATE_DIR/$1" 2>/dev/null || true; }
set_state() { printf '%s\n' "$2" > "$STATE_DIR/$1"; }
history() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >> "$STATE_DIR/history.log"; }

use_images() {
  # $1 — префикс образов, $2 — тег.
  export BACKEND_IMAGE="$1/backend:$2" FRONTEND_IMAGE="$1/frontend:$2"
}

wait_health() {
  for _ in $(seq 60); do
    if curl -fsS --max-time 5 "$API_URL/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

backup_db() {
  # $1 — тег, перед миграциями которого снимается дамп.
  mkdir -p "$BACKUP_DIR"
  local file
  file="$BACKUP_DIR/pre-$1-$(date -u +%Y%m%d-%H%M%S).sql.gz"
  # shellcheck disable=SC2016  # переменные раскрываются внутри контейнера postgres.
  "${COMPOSE[@]}" exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$file"
  log "бэкап БД: $file"
}

# Поднять релиз $1 из префикса $2. Возвращает не 0, если health или smoke не прошли.
start_release() {
  local tag=$1 prefix=$2
  use_images "$prefix" "$tag"
  log "релиз $tag: pull образов"
  # Без входа в реестр (ручной откат) берутся уже скачанные образы; нет образа — упадёт up.
  "${COMPOSE[@]}" pull --quiet --ignore-pull-failures backend frontend || return 1
  "${COMPOSE[@]}" up -d --no-build --wait --wait-timeout "$WAIT_TIMEOUT" postgres || return 1
  if [ "${SKIP_BACKUP:-false}" != "true" ]; then
    backup_db "$tag" || return 1
  fi
  log "релиз $tag: миграции"
  "${COMPOSE[@]}" run --rm -T --no-deps backend alembic upgrade head || return 1
  if [ "${DEPLOY_SEED:-false}" = "true" ]; then
    log "релиз $tag: сиды data/generated (DEPLOY_SEED=true)"
    "${COMPOSE[@]}" run --rm -T --no-deps backend python -m src.seed --dir data/generated || return 1
  fi
  log "релиз $tag: up"
  "${COMPOSE[@]}" up -d --no-build --wait --wait-timeout "$WAIT_TIMEOUT" backend frontend || return 1
  log "релиз $tag: health"
  wait_health || { log "health не ответил"; return 1; }
  log "релиз $tag: smoke $SMOKE_ARGS"
  # shellcheck disable=SC2086  # SMOKE_ARGS — список аргументов.
  python3 scripts/smoke.py --api "$API_URL" $SMOKE_ARGS || return 1
}

registry_login() {
  # $1 — пользователь реестра; токен — первая строка stdin.
  local user=$1 token registry=${2%%/*}
  IFS= read -r token || true
  [ -n "$token" ] || die "токен реестра не передан на stdin"
  printf '%s' "$token" | docker login "$registry" -u "$user" --password-stdin >/dev/null
  # Токен GitHub Actions живёт только во время job: сохранённый логин удаляем сразу после выкладки.
  trap 'docker logout "'"$registry"'" >/dev/null 2>&1 || true' EXIT
  log "вход в $registry выполнен"
}

cmd_deploy() {
  local tag=${1:-} prefix=${2:-} user=${3:-}
  if [ -z "$tag" ] || [ -z "$prefix" ]; then
    die "использование: deploy.sh deploy <tag> <image-prefix> [<registry-user>]"
  fi
  [ -f .env ] || die "нет .env в $(pwd): создайте его по .env.example (docs/devops.md, раздел 7)"
  mkdir -p "$STATE_DIR"
  [ -n "$user" ] && registry_login "$user" "$prefix"

  local prev prev_prefix
  prev=$(state current_tag)
  prev_prefix=$(state image_prefix)
  log "текущий релиз: ${prev:-нет}, выкладываем: $tag"

  if start_release "$tag" "$prefix"; then
    if [ -n "$prev" ] && [ "$prev" != "$tag" ]; then
      set_state previous_tag "$prev"
    fi
    set_state current_tag "$tag"
    set_state image_prefix "$prefix"
    history "deploy $tag ok (previous: ${prev:-none})"
    log "релиз $tag выложен"
    return 0
  fi

  history "deploy $tag FAILED"
  if [ -z "$prev" ] || [ "$prev" = "$tag" ]; then
    "${COMPOSE[@]}" logs --tail=100 backend || true
    die "релиз $tag не прошёл проверки, предыдущего тега нет — откатывать некуда"
  fi
  log "релиз $tag не прошёл проверки, откат на $prev"
  "${COMPOSE[@]}" logs --tail=100 backend || true
  if SKIP_BACKUP=true DEPLOY_SEED=false start_release "$prev" "${prev_prefix:-$prefix}"; then
    history "rollback to $prev ok"
    log "откат на $prev выполнен. Миграции $tag не откатываются: если схема несовместима," \
      "восстановите бэкап из $BACKUP_DIR/pre-$tag-*.sql.gz (docs/devops.md, раздел 7)"
  else
    history "rollback to $prev FAILED"
    log "откат на $prev тоже не прошёл проверки — нужен ручной разбор"
  fi
  exit 1
}

cmd_rollback() {
  local cur prev prefix
  cur=$(state current_tag)
  prev=$(state previous_tag)
  prefix=$(state image_prefix)
  if [ -z "$prev" ] || [ -z "$prefix" ]; then
    die "предыдущий тег не записан в $STATE_DIR/previous_tag"
  fi
  log "ручной откат: $cur → $prev"
  SKIP_BACKUP=${SKIP_BACKUP:-false} DEPLOY_SEED=false start_release "$prev" "$prefix" \
    || { history "manual rollback to $prev FAILED"; die "откат на $prev не прошёл проверки"; }
  set_state current_tag "$prev"
  set_state previous_tag "$cur"
  history "manual rollback $cur -> $prev ok"
  log "откат выполнен, текущий релиз: $prev"
}

cmd_status() {
  echo "current_tag:  $(state current_tag)"
  echo "previous_tag: $(state previous_tag)"
  echo "image_prefix: $(state image_prefix)"
  local prefix tag
  prefix=$(state image_prefix)
  tag=$(state current_tag)
  if [ -n "$prefix" ] && [ -n "$tag" ]; then
    use_images "$prefix" "$tag"
    "${COMPOSE[@]}" ps
  fi
  tail -n 10 "$STATE_DIR/history.log" 2>/dev/null || true
}

case "${1:-}" in
  deploy) shift; cmd_deploy "$@" ;;
  rollback) cmd_rollback ;;
  status) cmd_status ;;
  *) die "использование: deploy.sh deploy <tag> <image-prefix> [<registry-user>] | rollback | status" ;;
esac
