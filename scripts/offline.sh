#!/usr/bin/env bash
# Офлайн-пакет для резервного ноутбука (OPS-07): образы, модель Ollama, .env, исходники, дамп.
#
#   scripts/offline.sh bundle   # на машине с интернетом и собранным стеком (make offline-bundle)
#   scripts/offline.sh load     # на резервном ноутбуке без сети (make offline-load)
#
# Параметры — переменные окружения (Makefile передаёт их из .env):
#   OFFLINE_DIR        каталог пакета, по умолчанию dist/offline
#   POSTGRES_IMAGE     образ БД из .env (он же служит helper-образом для работы с томами)
#   OLLAMA_IMAGE       образ Ollama; кладётся в пакет, если скачан локально
#   WITH_OLLAMA        auto (по умолчанию: если образ есть) | 1 (обязательно) | 0 (не класть)
#   OLLAMA_MODELS_DIR  каталог моделей на хосте (например ~/.ollama/models), если модель
#                      скачана не в том compose; по умолчанию берётся том kodprozr_ollama_models
#   WITH_MODELS        auto | 1 | 0 — то же для моделей
# Подробности и пошаговая инструкция — docs/devops.md §7.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

PROJECT=kodprozr
OFFLINE_DIR=${OFFLINE_DIR:-dist/offline}
BACKEND_IMAGE=kodprozr-backend:local
FRONTEND_IMAGE=kodprozr-frontend:local
POSTGRES_IMAGE=${POSTGRES_IMAGE:-postgres:16.15-alpine}
OLLAMA_IMAGE=${OLLAMA_IMAGE:-ollama/ollama:0.12.6}
OLLAMA_VOLUME=${PROJECT}_ollama_models
OLLAMA_MODELS_DIR=${OLLAMA_MODELS_DIR:-}
WITH_OLLAMA=${WITH_OLLAMA:-auto}
WITH_MODELS=${WITH_MODELS:-auto}

log() { printf '==> %s\n' "$*"; }
die() { printf 'Ошибка: %s\n' "$*" >&2; exit 1; }
have_image() { docker image inspect "$1" >/dev/null 2>&1; }
# gzip или pigz, если он есть (в разы быстрее на многоядерных машинах).
gz() { if command -v pigz >/dev/null 2>&1; then pigz -1; else gzip -1; fi; }
abspath() { (cd "$1" && pwd); }

bundle() {
    for image in "$BACKEND_IMAGE" "$FRONTEND_IMAGE"; do
        have_image "$image" || die "нет образа $image — сначала make build"
    done
    have_image "$POSTGRES_IMAGE" || docker pull "$POSTGRES_IMAGE"

    rm -rf "$OFFLINE_DIR"
    mkdir -p "$OFFLINE_DIR"/{images,models,env,db}
    local dir
    dir=$(abspath "$OFFLINE_DIR")

    log "Образы стека: $BACKEND_IMAGE $FRONTEND_IMAGE $POSTGRES_IMAGE"
    docker save "$BACKEND_IMAGE" "$FRONTEND_IMAGE" "$POSTGRES_IMAGE" | gz >"$dir/images/kodprozr.tar.gz"

    if [ "$WITH_OLLAMA" != 0 ]; then
        if have_image "$OLLAMA_IMAGE"; then
            log "Образ Ollama: $OLLAMA_IMAGE (несколько ГБ, займёт пару минут)"
            docker save "$OLLAMA_IMAGE" | gz >"$dir/images/ollama.tar.gz"
        elif [ "$WITH_OLLAMA" = 1 ]; then
            die "нет образа $OLLAMA_IMAGE — docker pull $OLLAMA_IMAGE или make llm-up"
        else
            log "Образа $OLLAMA_IMAGE нет локально — пакет без LLM (стенд работает на фоллбэке)"
        fi
    fi

    if [ "$WITH_MODELS" != 0 ]; then
        # Модели уже сжаты (GGUF), поэтому tar без gzip.
        if [ -n "$OLLAMA_MODELS_DIR" ]; then
            [ -d "$OLLAMA_MODELS_DIR/manifests" ] || die "$OLLAMA_MODELS_DIR не похож на каталог моделей Ollama (нет manifests/)"
            log "Модели из каталога $OLLAMA_MODELS_DIR"
            tar -C "$OLLAMA_MODELS_DIR" -cf "$dir/models/ollama-models.tar" .
        elif docker volume inspect "$OLLAMA_VOLUME" >/dev/null 2>&1; then
            log "Модели из тома $OLLAMA_VOLUME"
            # Том смонтирован в /root/.ollama, модели лежат в models/ — пакуем содержимое models/.
            docker run --rm --network none --pull never -v "$OLLAMA_VOLUME":/src:ro -v "$dir/models":/out \
                "$POSTGRES_IMAGE" sh -c 'test -d /src/models && tar -C /src/models -cf /out/ollama-models.tar .' \
                || die "в томе $OLLAMA_VOLUME нет моделей — make llm-up"
        elif [ "$WITH_MODELS" = 1 ]; then
            die "модель не найдена: нет тома $OLLAMA_VOLUME, OLLAMA_MODELS_DIR не задан"
        else
            log "Моделей нет (ни тома $OLLAMA_VOLUME, ни OLLAMA_MODELS_DIR) — пакет без модели"
        fi
        [ -s "$dir/models/ollama-models.tar" ] && tar -tf "$dir/models/ollama-models.tar" \
            | sed -n 's#^\./manifests/[^/]*/library/\([^/]*\)/\([^/][^/]*\)$#    модель \1:\2#p'
    fi

    if [ -f .env ]; then
        cp .env "$dir/env/.env"
    else
        cp .env.example "$dir/env/.env"
    fi
    local dump
    dump=$(ls -1t dist/db/*.sql.gz 2>/dev/null | head -n1 || true)
    if [ -n "$dump" ]; then
        log "Последний дамп БД: $dump"
        cp "$dump" "$dir/db/"
    fi

    log "Исходники HEAD (compose, Makefile, data/generated): kodprozr-src.tar.gz"
    git archive --format=tar.gz -o "$dir/kodprozr-src.tar.gz" HEAD
    git diff --quiet HEAD -- || log "ВНИМАНИЕ: есть незакоммиченные правки — в kodprozr-src.tar.gz их нет"

    {
        echo "Офлайн-пакет «Код прозрачности»"
        echo "создан:  $(date '+%F %T')"
        echo "коммит:  $(git rev-parse --short HEAD) ($(git rev-parse --abbrev-ref HEAD))"
        echo "образы:"
        for image in "$BACKEND_IMAGE" "$FRONTEND_IMAGE" "$POSTGRES_IMAGE" "$OLLAMA_IMAGE"; do
            have_image "$image" && echo "  $image $(docker image inspect -f '{{.Id}}' "$image")"
        done
        echo "LLM_MODEL: $(sed -n 's/^LLM_MODEL=//p' "$dir/env/.env")"
        echo
        echo "Загрузка: распаковать kodprozr-src.tar.gz, затем в его корне"
        echo "  make offline-load OFFLINE_DIR=<путь к этому каталогу> && make reset OFFLINE=1"
        echo "Подробно: docs/devops.md §7."
    } >"$dir/MANIFEST.txt"
    find "$dir" -type d -empty -delete
    (cd "$dir" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum >SHA256SUMS)

    log "Готово: $OFFLINE_DIR ($(du -sh "$dir" | cut -f1))"
    (cd "$dir" && find . -type f -exec ls -lh {} + | awk '{print "    " $5 "\t" $9}')
}

load() {
    [ -d "$OFFLINE_DIR" ] || die "нет каталога $OFFLINE_DIR (OFFLINE_DIR=<путь к пакету>)"
    local dir
    dir=$(abspath "$OFFLINE_DIR")
    if [ -f "$dir/SHA256SUMS" ]; then
        log "Проверка контрольных сумм"
        (cd "$dir" && sha256sum --quiet -c SHA256SUMS) || die "пакет повреждён — скопируйте заново"
    fi

    for archive in "$dir"/images/*.tar.gz; do
        [ -e "$archive" ] || die "в $OFFLINE_DIR/images нет образов"
        log "docker load: $(basename "$archive")"
        docker load -i "$archive"
    done

    if [ -s "$dir/models/ollama-models.tar" ]; then
        log "Модели Ollama -> том $OLLAMA_VOLUME"
        # Метки compose, чтобы том считался своим для проекта kodprozr.
        docker volume inspect "$OLLAMA_VOLUME" >/dev/null 2>&1 || docker volume create \
            --label com.docker.compose.project=$PROJECT --label com.docker.compose.volume=ollama_models \
            "$OLLAMA_VOLUME" >/dev/null
        docker run --rm --network none --pull never -v "$OLLAMA_VOLUME":/dst -v "$dir/models":/in:ro \
            "$POSTGRES_IMAGE" sh -c 'mkdir -p /dst/models && tar -C /dst/models -xf /in/ollama-models.tar'
    fi

    if [ -f .env ]; then
        log ".env уже есть — оставляю его (из пакета: $OFFLINE_DIR/env/.env)"
    elif [ -f "$dir/env/.env" ]; then
        cp "$dir/env/.env" .env
        log ".env взят из пакета"
    fi

    log "Образы загружены. Дальше без сети:"
    echo "    make reset OFFLINE=1            # стек с миграциями и сидами"
    [ -s "$dir/models/ollama-models.tar" ] && echo "    make llm-up OFFLINE=1           # Ollama с моделью из пакета"
    for dump in "$dir"/db/*.sql.gz; do
        [ -e "$dump" ] && echo "    make restore FILE=$dump   # если нужен дамп вместо сидов"
    done
    return 0
}

case "${1:-}" in
    bundle) bundle ;;
    load) load ;;
    *) die "использование: $0 bundle|load" ;;
esac
