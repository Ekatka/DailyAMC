#!/bin/bash

domains=(dailyamr.xyz www.dailyamr.xyz)
rsa_key_size=4096
data_path="./certbot"
email="notforworked@gmail.com" # Adding your email is recommended
staging=1 # Set to 1 if you're testing your setup to avoid hitting request limits

if [ "$staging" != "0" ]; then
  staging_arg="--staging"
fi

for domain in "${domains[@]}"; do
  domain_path="$data_path/conf/live/$domain"
  mkdir -p "$domain_path"
  if [ ! -e "$domain_path/fullchain.pem" ]; then
    echo "### Creating dummy certificate for $domain ..."
    openssl req -x509 -nodes -newkey rsa:1024 -days 1\
      -keyout "$domain_path/privkey.pem" \
      -out "$domain_path/fullchain.pem" \
      -subj "/CN=localhost"
  fi
done

echo "### Starting nginx ..."
docker-compose up --force-recreate -d nginx
echo

for domain in "${domains[@]}"; do
  echo "### Deleting dummy certificate for $domain ..."
  rm -Rf "$data_path/conf/live/$domain/*"
  echo

  echo "### Requesting Let's Encrypt certificate for $domain ..."
  docker-compose run --rm --entrypoint "\
    certbot certonly --webroot -w /var/www/certbot \
      $staging_arg \
      --register-unsafely-without-email \
      --agree-tos \
      --no-eff-email \
      --email $email \
      -d $domain" certbot
  echo
done

echo "### Reloading nginx ..."
docker-compose exec nginx nginx -s reload
