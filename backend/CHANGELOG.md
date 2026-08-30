# Changelog

## [0.2.0](https://github.com/j3ko/gainbridge/compare/v0.1.1...v0.2.0) (2026-08-28)


### Features

* display app version in UI footer ([#26](https://github.com/j3ko/gainbridge/issues/26)) ([99fa011](https://github.com/j3ko/gainbridge/commit/99fa011606f8e0d3fa72ba36dc639c5c42f3b3fe))


### Bug Fixes

* evaluate source schedule cron in a configured timezone ([#28](https://github.com/j3ko/gainbridge/issues/28)) ([ac886a6](https://github.com/j3ko/gainbridge/commit/ac886a6ed6cddf5e23a30e51bb3932af1e1e0006))
* recover PR [#46](https://github.com/j3ko/gainbridge/issues/46)'s changes that never reached main ([#47](https://github.com/j3ko/gainbridge/issues/47)) ([6360b0f](https://github.com/j3ko/gainbridge/commit/6360b0f73de0dc79d829fdf8b87ea35bac01e323))

## [0.1.1](https://github.com/j3ko/gainbridge/compare/v0.1.0...v0.1.1) (2026-08-27)


### Bug Fixes

* serialize job/source timestamps with explicit UTC offset ([182ac20](https://github.com/j3ko/gainbridge/commit/182ac20207b121dceba505e3cb3738d86f9558e7))
* use non-nullable return types for required-field UTC serializers ([15222fd](https://github.com/j3ko/gainbridge/commit/15222fd2a23b89eb1f491f7d56f2bef314e51f9b))

## 0.1.0 (2026-08-27)


### Features

* add connection logging for Jellyfin/Plex sources ([c5ba0e5](https://github.com/j3ko/gainbridge/commit/c5ba0e5d682aab627b0764c55618816a35ebc1d0))
* add cron-based scheduled syncs per source ([8eb53d2](https://github.com/j3ko/gainbridge/commit/8eb53d2d48b82f4e45e68a372ee3aa58a6b3d75b))
* add job cancellation and graceful shutdown for sync jobs ([4a5ecb5](https://github.com/j3ko/gainbridge/commit/4a5ecb501ad7794e40dd438ce079bdb70bcdc2c3))
* add per-job sync logging with a dedicated Logs page ([2fdd8ad](https://github.com/j3ko/gainbridge/commit/2fdd8ad67395bbcfe8fcbd3daa2db2703edae22f))
* add Test Connection and Plex OAuth sign-in to source setup ([3cf5b58](https://github.com/j3ko/gainbridge/commit/3cf5b583b598b363ea180e11a454b0a0696802bf))
* let a source scope syncs to a single Plex/Jellyfin library ([364296d](https://github.com/j3ko/gainbridge/commit/364296df9febbb1ba221f35e27f12f3722c9f6ad))
* prune old jobs, rotate logs, and paginate the jobs list ([a6c1fa2](https://github.com/j3ko/gainbridge/commit/a6c1fa2ca96583a1729625ac98960c6db18b1f07))
* reject manual sync when a job is already running for the source ([af0cec5](https://github.com/j3ko/gainbridge/commit/af0cec50700dcc35fd07d22a8d28244a86bc2721))
* remove unnecessary Jellyfin user_id source field ([f14bfa7](https://github.com/j3ko/gainbridge/commit/f14bfa715b93558e50a93c74bcb2f5cb5baefec6))
* replace overwrite toggle with a 3-way ReplayGain write mode ([c33796b](https://github.com/j3ko/gainbridge/commit/c33796bb7b6cb0a6fcf62a382d754f41da6003a3))
* replace self-hosted deploy with CircleCI multi-arch Docker Hub image ([27c9dad](https://github.com/j3ko/gainbridge/commit/27c9dadb05adae4b70e8b95625c299be1354cd41))
* skip ReplayGain writes only when existing tags already match ([c640887](https://github.com/j3ko/gainbridge/commit/c6408877a9f118870f35bee030c15f4a3f10ca36))
* support multiple remote path mappings per source ([89b64b8](https://github.com/j3ko/gainbridge/commit/89b64b8bf1bc1d72c36a1a98f976c15ff83d1e93))
* surface source enabled status and fix disabled-source scheduling ([0f5bb9d](https://github.com/j3ko/gainbridge/commit/0f5bb9d842abceaf61623899ddbc7bd925a34e5e))


### Bug Fixes

* default SQLITE_DB_FILE/LOG_FILE to data/ so the published image persists without .env ([bf3e4ac](https://github.com/j3ko/gainbridge/commit/bf3e4ac5c7e85e467f2524a2789ba78df0b03642))
* drop --workers 4, run single-process ([a0b8215](https://github.com/j3ko/gainbridge/commit/a0b8215e26f39c27398111c13d77d286bc33b92f))
* give the SPA fallback route a tag to avoid startup crash ([c86bc05](https://github.com/j3ko/gainbridge/commit/c86bc05cc50155c7f1e5292d3219fe78be6966be))
* make the app self-migrate instead of relying on prestart.sh ([d2be968](https://github.com/j3ko/gainbridge/commit/d2be9689fe55bb271017bec7061e4e474a884cd4))
* persist SQLite DB and logs, drop stale POSTGRES_PASSWORD ([9fbc239](https://github.com/j3ko/gainbridge/commit/9fbc239964838202a96e61270bf07e1edaffce90))
* put data/ at repo root, not inside backend/ ([bb56b86](https://github.com/j3ko/gainbridge/commit/bb56b8687da24b38fa2a0dacdfa9a8afebdeaa9c))
* recognize existing ReplayGain tags stored as ID3 TXXX frames ([a06cc19](https://github.com/j3ko/gainbridge/commit/a06cc19e000a8ddad910487cd6ee7f95a683e666))
* reload partial Plex tracks before reading audio streams ([a61cba0](https://github.com/j3ko/gainbridge/commit/a61cba0e5194eb7f01800d11a475480227d7dfb3))
* remove unused ACCESS_TOKEN_EXPIRE_MINUTES and EMAIL_RESET_TOKEN_EXPIRE_HOURS ([14b326c](https://github.com/j3ko/gainbridge/commit/14b326c172c5e53e6dc916edb97b16f4e5b9d975))
* remove unused EMAIL_TEST_USER setting ([199f45a](https://github.com/j3ko/gainbridge/commit/199f45aab9694ce2162a6b41443ad309740399be))
* remove unused FIRST_SUPERUSER/email/SMTP settings and dependencies ([2f05b88](https://github.com/j3ko/gainbridge/commit/2f05b881cfa327462d6d6d0c5326b1abab740875))
* remove unused SECRET_KEY and pyjwt leftover from FastAPI template ([f53d5df](https://github.com/j3ko/gainbridge/commit/f53d5df66287c584ad559d0d27631c3a41de4aa9))
* run Alembic migrations before the multi-worker server starts ([df16a58](https://github.com/j3ko/gainbridge/commit/df16a5835bb39eaab01da9d9941a31cc5381d194))
* stop Alembic from disabling the app logger on every startup ([3befde4](https://github.com/j3ko/gainbridge/commit/3befde442222ab7eb4a31270fc43a8e424086d38))
* stop duplicate uvicorn startup logs from stray root handler ([b5464c5](https://github.com/j3ko/gainbridge/commit/b5464c55ef3f4e5f6cdb2f03ccd54a33b03fbc86))
* write ReplayGain tags to MP4/M4A files via freeform atoms ([fa4c412](https://github.com/j3ko/gainbridge/commit/fa4c4121066da83230e0170025fe3a1205b02214))


### Documentation

* rewrite project markdown for Gainbridge, drop template docs ([7ba531b](https://github.com/j3ko/gainbridge/commit/7ba531b528928cf4b310edaf51a694ed3c6b1564))
