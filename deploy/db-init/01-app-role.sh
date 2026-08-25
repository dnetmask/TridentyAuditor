#!/bin/sh
# Crea el rol de APLICACIÓN, separado del rol dueño de las tablas.
#
# Por qué existe (Fase S1): en la imagen oficial de Postgres, POSTGRES_USER
# es SUPERUSUARIO — y los superusuarios ignoran Row-Level Security incluso
# con FORCE ROW LEVEL SECURITY. Si la API se conecta con ese rol, el
# aislamiento multitenant entero queda anulado. La API debe conectarse como
# `tridenty_app`: sin SUPERUSER, sin BYPASSRLS y sin ownership de tablas,
# con solo los permisos DML que necesita.
#
# Este script corre una sola vez, cuando el volumen de datos se inicializa
# (docker-entrypoint-initdb.d). En un volumen que ya existía antes de este
# cambio: `docker compose down -v` para re-inicializar, o ejecutar estas
# mismas sentencias a mano con psql.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE ROLE tridenty_app LOGIN PASSWORD '${TRIDENTY_APP_DB_PASSWORD:-tridenty_app}';
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO tridenty_app;
    GRANT USAGE ON SCHEMA public TO tridenty_app;
    -- Las tablas las crea el rol de migraciones ($POSTGRES_USER) después de
    -- este script; los default privileges hacen que cada tabla/secuencia
    -- futura llegue ya con DML para la app — nunca ownership.
    ALTER DEFAULT PRIVILEGES FOR ROLE $POSTGRES_USER IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tridenty_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE $POSTGRES_USER IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO tridenty_app;
EOSQL
