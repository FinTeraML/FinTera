# FinTera - Financial Technology Solutions

A Django-based financial technology platform with AI-powered analytics and trading capabilities.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [Development Workflow](#development-workflow)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before running this project, make sure you have the following installed:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 14+** - [Download Node.js](https://nodejs.org/) (for Tailwind CSS compilation)
- **Git** - [Download Git](https://git-scm.com/downloads)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd FinTeraML
```

### 2. Set Up Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirement.txt
```

### 4. Set Up Tailwind CSS
```bash
cd util
npm install
cd ..
```

### 5. Database Setup
```bash
# Run database migrations
python manage.py migrate

# Create a superuser (optional)
python manage.py createsuperuser
```

## Running the Project

### 1. Start the Django Development Server
```bash
# Make sure your virtual environment is activated
python manage.py runserver
```

The application will be available at: `http://127.0.0.1:8000/`

### 2. Access the Application
- **Landing Page**: `http://127.0.0.1:8000/`
- **Admin Panel**: `http://127.0.0.1:8000/admin/` (if you created a superuser)

## Development Workflow

### Editing Styles (Tailwind CSS)

If you need to modify the CSS styles:

1. Edit the Tailwind input file:
   ```bash
   # Edit the input CSS file
   util/input.css
   ```

2. Compile the styles:
   ```bash
   cd util
   npx @tailwindcss/cli -i input.css -o ../static/css/styles.css --watch
   ```

   **Note**: Use the `--watch` flag during development to automatically recompile styles when you make changes.

### Making Database Changes

1. Create migrations after model changes:
   ```bash
   python manage.py makemigrations
   ```

2. Apply migrations:
   ```bash
   python manage.py migrate
   ```

### Collecting Static Files (Production)

For production deployment:
```bash
python manage.py collectstatic
```

## Project Structure

```
FinTeraML/
├── FinTeraML/           # Django project settings
│   ├── settings.py      # Project configuration
│   ├── urls.py          # URL routing
│   └── wsgi.py          # WSGI configuration
├── templates/           # HTML templates
│   ├── base.html        # Base template
│   └── landing/         # Landing page templates
├── static/              # Static files (CSS, JS, images)
├── util/                # Tailwind CSS setup
│   ├── input.css        # Tailwind input file
│   ├── package.json     # Node.js dependencies
│   └── node_modules/    # Node.js packages
├── manage.py            # Django management script
├── requirement.txt      # Python dependencies
├── db.sqlite3           # SQLite database
└── README.md            # This file
```

## Troubleshooting

### Common Issues

1. **Virtual Environment Not Activated**
   - Make sure to activate your virtual environment before running any Python commands
   - Look for `(.venv)` in your terminal prompt

2. **Module Not Found Errors**
   - Ensure all dependencies are installed: `pip install -r requirement.txt`
   - Verify you're in the correct directory and virtual environment is activated

3. **Tailwind CSS Not Working**
   - Make sure Node.js is installed and accessible
   - Run `npm install` in the `util/` directory
   - Recompile styles: `cd util && npx @tailwindcss/cli -i input.css -o ../static/css/styles.css`

4. **Database Errors**
   - Run migrations: `python manage.py migrate`
   - If persistent issues, delete `db.sqlite3` and run migrations again

5. **Port Already in Use**
   - Use a different port: `python manage.py runserver 8001`
   - Or kill the process using port 8000

### Getting Help

If you encounter issues not covered here:
1. Check the Django documentation: https://docs.djangoproject.com/
2. Verify all prerequisites are properly installed
3. Ensure all steps in the installation process were completed

## Quick Start Commands

For experienced developers, here's a quick command sequence:

```bash
# Clone and setup
git clone <repository-url> && cd FinTeraML
python -m venv .venv && .venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Setup Tailwind
cd util && npm install && cd ..

# Database and run
python manage.py migrate
python manage.py runserver
```

---

**Happy coding! 🚀**
