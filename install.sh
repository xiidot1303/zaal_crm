#!/bin/bash

set -e

pip install -r requirements.txt

mkdir logs

echo "Project title:"
read project_title
echo "User: "
read user
echo "Database user: "
read db_user
echo "Database password"
read db_password
echo "Bot token: "
read bot_token
echo "Project port"
read port
echo "Bot port"
read bot_port
echo "Project domain"
read domain

secret_key=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

cp conf/env .env
sed -i "s/<port>/$port/g" ".env"
sed -i "s/<bot_port>/$bot_port/g" ".env"
sed -i "s/<secret_key>/$secret_key/g" ".env"
sed -i "s/<db_name>/$project_title/g" ".env"
sed -i "s/<db_user>/$db_user/g" ".env"
sed -i "s/<db_password>/$db_password/g" ".env"
sed -i "s/<bot_token>/$bot_token/g" ".env"
sed -i "s/<domain>/$domain/g" ".env"
sed -i "s/<csrf_trusted_origins>/$domain/g" ".env"

createdb $project_title


python manage.py migrate --skip-checks
python manage.py makemigrations app
python manage.py makemigrations bot
python manage.py migrate app
python manage.py migrate bot
python manage.py collectstatic
python manage.py createsuperuser

touch $project_title
sed -i "s/<title>/$project_title/g" "conf/supervisor.conf"
sed -i "s/<folder>/$project_title/g" "conf/supervisor.conf"
sed -i "s/<user>/$user/g" "conf/supervisor.conf"
sed -i "s/<port>/$port/g" "conf/supervisor.conf"
sed -i "s/<bot_port>/$bot_port/g" "conf/supervisor.conf"
sudo cp conf/supervisor.conf /etc/supervisor/conf.d/$project_title.conf
sudo supervisorctl reread
sudo supervisorctl update

sed -i "s/<project_title>/$project_title/g" "conf/restart.sh"
cp conf/restart.sh .

sed -i "s/<domain>/$domain/g" "conf/nginx.conf"
sed -i "s/<user>/$user/g" "conf/nginx.conf"
sed -i "s/<folder>/$project_title/g" "conf/nginx.conf"
sed -i "s/<port>/$port/g" "conf/nginx.conf"
sed -i "s/<bot_port>/$bot_port/g" "conf/nginx.conf"
sed -i "s/<bot_token>/$bot_token/g" "conf/nginx.conf"
sudo cp conf/nginx.conf /etc/nginx/sites-enabled/$project_title.conf

# give access to nginx to the project folder staticfiles
chmod o+x /home/$user
chmod o+x /home/$user/$project_title
chmod -R o+r /home/$user/$project_title/staticfiles
chmod -R o+X /home/$user/$project_title/staticfiles

sudo nginx -t
echo "Continue?"
read qwerty

sudo certbot --nginx

sudo service nginx reload

curl "https://api.telegram.org/bot$bot_token/setWebhook?url=https://$domain/$bot_token"


echo "Installation complete"

