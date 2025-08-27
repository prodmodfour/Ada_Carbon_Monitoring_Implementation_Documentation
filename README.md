## 🚀 Installation and Setup

### 1\. Clone the Repository

First, clone the project and navigate into the source directory.

```sh
git clone https://github.com/prodmodfour/Mock_Ada_Carbon_Monitoring_Implementation.git
cd Mock_Ada_Carbon_Monitoring_Implementation/source
```

### 2\. Install Dependencies

Next, upgrade `pip` and then install the required packages listed in `requirements.txt`.

```sh
python -m pip install -U pip
pip install -r requirements.txt
```

### 3\. Set Up the Database

Run the following commands to create the necessary migrations and apply them.

```sh
python manage.py makemigrations
python manage.py migrate
```

### 4\. Populate Initial Data

These commands will populate the cache with energy and instrument data.

```sh
python manage.py refresh_energy_cache
python manage.py refresh_instrument_averages
```

### 5\. Run the Application

You'll need two separate terminal windows to run the full application.

  * **In your first terminal**, start the background process that syncs workspaces every 60 seconds.

    ```sh
    python manage.py sync_workspaces --sleep 60
    ```

  * **In a second terminal**, start the main development server.

    ```sh
    python manage.py runserver
    ```

Once the server is running, you should be able to access the application in your web browser, typically at `http://127.0.0.1:8000`.