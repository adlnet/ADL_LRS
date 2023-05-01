# if ADL_LRS directory does exist then pull the latest code or else clone the repo
if [ -d "ADL_LRS" ]; then
  echo "Directory ADL_LRS exists."
  cd ADL_TEST
  git pull
  cd ..
else
  echo "Directory ADL_LRS does not exists."
  git clone https://github.com/adlnet/ADL_LRS.git
fi

sudo cp /home/ubuntu/workflow/settings.ini /home/ubuntu/ADL_LRS/settings.ini
sudo cp /home/ubuntu/workflow/docker/settings.ini /home/ubuntu/ADL_LRS/docker/lrs/settings.ini
sudo cp /home/ubuntu/workflow/.env /home/ubuntu/ADL_LRS/.env

cd ADL_LRS
sudo usermod -aG docker $USER
sudo ./init-ssl.sh localhost
sudo docker-compose stop

sudo docker-compose build --no-cache
docker-compose up -d