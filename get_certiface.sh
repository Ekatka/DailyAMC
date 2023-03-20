#!/bin/bash


DOMAIN="dailyamc.xyz"
EMAIL="katya.danilina@gmail.com"


if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi

# Obtain SSL certificate using Certbot standalone
sudo certbot certonly --standalone --preferred-challenges http -d $DOMAIN --agree-tos -m $EMAIL --non-interactive

# Configure nginx to use SSL
sed -i "s|#      - \"443:443\"|      - \"443:443\"|" docker-compose-full.yml

# Link SSL certificates to nginx
SSL_CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
sed -i "s|ssl_certificate     /etc/letsencrypt/live/ssl/fullchain.pem;|ssl_certificate     $SSL_CERT_PATH/fullchain.pem;|" ./nginx/nginx.conf
sed -i "s|ssl_certificate_key /etc/letsencrypt/live/ssl/privkey.pem;|ssl_certificate_key $SSL_CERT_PATH/privkey.pem;|" ./nginx/nginx.conf

# Start the Docker services
docker-compose -f docker-compose-full.yml up