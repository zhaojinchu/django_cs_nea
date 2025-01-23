# CS NEA 


### Production only

#### Logs
journalctl -u daphne

#### Restarting services
sudo systemctl restart daphne
sudo systemctl restart nginx
sudo systemctl restart gunicorn
sudo systemctl restart celery
sudo systemctl restart celerybeat

#### Reloads systemd
sudo systemctl daemon-reload

### Services in use
- Redis
- Gunicorn
- Nginx
- Celery
- Daphne
