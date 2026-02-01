#!/bin/bash
set -e

echo "🔧 Создаём пользователя и базу данных..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'Создание пользователя $DB_USER' as info;

    -- Проверяем существование пользователя
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
            CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
            RAISE NOTICE 'Пользователь $DB_USER создан';
        ELSE
            RAISE NOTICE 'Пользователь $DB_USER уже существует';
        END IF;
    END
    \$\$;

    SELECT 'Создание базы $DB_NAME' as info;

    -- Создаём базу если не существует
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_database WHERE datname = '$DB_NAME') THEN
            CREATE DATABASE $DB_NAME
            OWNER $DB_USER
            ENCODING UTF8
            LC_COLLATE='C'
            LC_CTYPE='C'
            TEMPLATE template0;
            RAISE NOTICE 'База $DB_NAME создана';
        ELSE
            RAISE NOTICE 'База $DB_NAME уже существует';
        END IF;
    END
    \$\$;

    -- Даём права
    GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

    SELECT '✅ Инициализация завершена' as status;
EOSQL

echo "✅ База данных готова!"
