# Two-stage build.
#
# Stage 1 ("build") has Python and the generator. It renders the whole site
# into /dist. Stage 2 has only nginx and the rendered HTML -- no Python, no
# source, no pip cache. That is the point of a multi-stage build: the tools you
# need to *make* the artifact are not the tools you need to *serve* it.

# ---------------------------------------------------------------- stage 1 ----
FROM python:3.12-slim AS build

WORKDIR /src

# Dependencies are copied on their own, before the source. Docker caches each
# layer, so editing a bio file does not re-run pip install.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Now the parts that actually change: the generator, the bios, the site config.
COPY generator/ ./generator/
COPY bios/ ./bios/
COPY site.yml ./site.yml

# Deliberately NOT --strict. A bio file that got merged with a bad team name or
# broken YAML renders with fallback values and a build warning, so the deployed
# site degrades by one card instead of failing to build at all. The hard gate
# lives in CI: .github/workflows/ci.yml runs `generator validate` on every pull
# request, so a broken bio cannot reach the testing branch through review.
RUN python -m generator build --bios bios --config site.yml --out /dist

# ---------------------------------------------------------------- stage 2 ----
FROM nginx:1.27-alpine-slim

LABEL org.opencontainers.image.title="Bio Aggregator" \
      org.opencontainers.image.description="Static professional bio site generated from YAML in bios/." \
      org.opencontainers.image.source="https://github.com/KhourySpecialProjects/linear-github-practice"

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /dist /usr/share/nginx/html

EXPOSE 80

# alpine-slim has no curl; busybox wget is what we get.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://127.0.0.1/ || exit 1
