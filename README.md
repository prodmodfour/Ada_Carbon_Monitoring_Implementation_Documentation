Install and run:

git clone https://github.com/prodmodfour/Mock_Ada_Carbon_Monitoring_Implementation.git
cd Mock_Ada_Carbon_Monitoring_Implementation/source

python -m pip install -U pip
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver