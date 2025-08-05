#!/bin/bash
# Запуск создания файлf для nginx_config
# chmod +x nginx_config.sh
# Нужно заменить название домена, директорию проекта и название файла \/
# ./nginx_config.sh domain_name.com project_directory domain_name.conf
# Проверяем количество аргументов
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 domain_name project_directory filename"
    exit 1
fi

DOMAIN_NAME=$1
PROJECT_DIRECTORY=$2
FILENAME=$3

# Шаблон конфигурационного файла nginx
CONFIG_TEMPLATE=$(cat <<EOF
server {
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    location / {
        proxy_pass http://0.0.0.0:8000;
        proxy_http_version 1.1;
        proxy_read_timeout 86400;
        proxy_redirect off;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 900M;
    }

    location /ws/ {
        proxy_pass http://0.0.0.0:8001;
        proxy_http_version 1.1;
        proxy_read_timeout 86400;
        proxy_redirect off;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias /var/www/$PROJECT_DIRECTORY/src/_static/;
    }

    location /media/ {
        alias /var/www/$PROJECT_DIRECTORY/src/_media/;
    }
}
EOF
)

# Создаем конфигурационный файл nginx
echo "$CONFIG_TEMPLATE" > "$FILENAME"

echo "Config file created: $FILENAME"

