# CS NEA 
## But this time its fully django 
### No nextjs frontend backend stuff

### Always run
- python manage.py tailwind start

- celery -A cs_nea beat --loglevel=info

- celery -A cs_nea worker --loglevel=info
