# GHMC Backend

## Project Structure

- `.env.example`
- `manage.py`
- `pyproject.toml`
- `.github/`
  - `workflows/`
    - `ci.yml`
- `authentication/`
  - `admin.py`
  - `apps.py`
  - `exceptions.py`
  - `managers.py`
  - `models.py`
  - `serializers.py`
  - `tokens.py`
  - `views.py`
  - `__init__.py`
  - `tests/`
  - `migrations/`
- `config/`
  - `api_router.py`
  - `asgi.py`
  - `celery.py`
  - `settings.py`
  - `test_settings.py`
  - `urls.py`
  - `wsgi.py`
  - `__init__.py`
- `helpers/`
  - `__init__.py`
  - `cloudinaryUtils.py`
  - `emailClient.py`
  - `enums.py`
  - `models.py`
  - `redisClient.py`

- `inference/`
  - `aggregation.py`
  - `context.py`
  - `dispatcher.py`
  - `promptBuilder.py`
  - `redis_worker.py`
  - `responseProcessor.py`
  - `style.py`
  - `systemPrompt.py`
  - `tasks.py`
  - `__init__.py`
  - `clients/`
    - `base.py`
    - `openRouter.py`
  - `tests/`
    - `test_aggregation.py`
    - `test_context.py`
    - `test_inferenceservice.py`
    - `test_openrouter.py`
    - `test_promptbuilder.py`
    - `test_responseprocessor.py`
    - `test_style.py`
    - `test_systemprompt.py`
    - `test_tasks.py`
    - `test_worker.py`

- `memories/`
  - `forms.py`
  - `models.py`
  - `serializers.py`
  - `tasks.py`
  - `urls.py`
  - `views.py`
  - `__init__.py`
  - `tests/`
    - `conftest.py`
    - `test_models.py`
    - `test_serializers.py`
    - `test_urls.py`
    - `test_views.py`

## Start the virtual environment

Use the following command to start the venv to eliminate environment differences

```bash
.venv/Scripts/activate
```

## Copy the env file and update with real values

Copy out the env stubs into a new env file and replace with real variable values

```bash
cp .env.example .env
```

```powershell
python -c "import shutil; shutil.copy('example.env', '.env')"
```

## Install dependencies

Run this command to install all the environment dependencies

```bash
uv sync
```

## Run the Server

Use the following command to start the FastAPI application in reload mode:

```bash
python manage.py runserver
```

## API Docs

Once the server is running, open the docs at:

```text
http://127.0.0.1:3000/docs
```

# Wait-For-It

## Project Overview

The Wait-for-it project is a terminal-integrated service that assists developers and software engineers in documenting their projects from idea phase to final deployment, in the form of logs images and video.

## Justification

I chose to build this project as a backend engineer who often forgets to record my entire building journey settling for random linkedIn posts once in a purple moon. The drive behind this app is the ability to actually document the build process seamlessly from the terminal.

## What does documentation look like with WFI

There are three main methods of documentation currently provided by WFI

1. **Logs**: Written text, can be useful for documenting perspectives behind decisions made. Here's an example; "Introduced extra authentication layer between internal system and client using mTLS credentials for better security." Logs can act as fodder for articles during the duration of product development, as opposed to trying to remeber all decisions and their driving forces.
   >
2. **Images**: Image files, these can be draft architecture diagrams, error logs screenshots, images of product pitches or other important footage of the creation process.
   >
3. **Videos**: Video files, These can be demo videos, product pitch videos, or other important footage of the creation process.

# QuickStart

set up the directory to handle waitforit commands

```python
waitforit init
```
