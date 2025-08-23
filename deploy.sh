#!/bin/bash

# AWS EC2 Ubuntu 22.04 deployment script for Django Affiliate Publisher

set -e  # Exit on error

echo "Starting deployment of Affiliate Publisher..."

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    postgresql \
    postgresql-contrib \
    supervisor \
    git \
    build-essential \
    libpq-dev

# Create application directory
cd /home/ubuntu

# Clone or update repository (replace with your repo)
if [ ! -d "affiliate_publisher" ]; then
    echo "Cloning repository..."
    git clone https://github.com/yourusername/affiliate_publisher.git
    cd affiliate_publisher
else
    echo "Updating repository..."
    cd affiliate_publisher
    git pull
fi

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set up environment variables
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit the .env file with your actual values"
    echo "Run: nano /home/ubuntu/affiliate_publisher/.env"
fi

# Set up PostgreSQL database
echo "Setting up PostgreSQL database..."
sudo -u postgres psql <<EOF
CREATE DATABASE IF NOT EXISTS affiliate_publisher;
CREATE USER IF NOT EXISTS affiliate_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE affiliate_user SET client_encoding TO 'utf8';
ALTER ROLE affiliate_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE affiliate_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE affiliate_publisher TO affiliate_user;
\q
EOF

# Run Django setup commands
echo "Running Django migrations..."
python manage.py makemigrations publisher
python manage.py migrate

# Create directories
echo "Creating necessary directories..."
mkdir -p media/uploads
mkdir -p static
mkdir -p /var/log/gunicorn
sudo chown ubuntu:ubuntu /var/log/gunicorn

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser (optional - uncomment if needed)
# echo "Creating Django superuser..."
# python manage.py createsuperuser --noinput --username admin --email admin@example.com

# Set up Gunicorn with Supervisor
echo "Configuring Supervisor..."
sudo tee /etc/supervisor/conf.d/affiliate_publisher.conf > /dev/null <<'EOF'
[program:affiliate_publisher]
command=/home/ubuntu/affiliate_publisher/venv/bin/gunicorn affiliate_publisher.wsgi:application -c /home/ubuntu/affiliate_publisher/gunicorn_config.py
directory=/home/ubuntu/affiliate_publisher
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/gunicorn/affiliate_publisher.log
stderr_logfile=/var/log/gunicorn/affiliate_publisher_error.log
environment=PATH="/home/ubuntu/affiliate_publisher/venv/bin",DJANGO_SETTINGS_MODULE="affiliate_publisher.settings"
EOF

# Set up Nginx
echo "Configuring Nginx..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp nginx.conf /etc/nginx/sites-available/affiliate_publisher
sudo ln -sf /etc/nginx/sites-available/affiliate_publisher /etc/nginx/sites-enabled/

# Set proper permissions
echo "Setting file permissions..."
sudo chown -R ubuntu:www-data /home/ubuntu/affiliate_publisher
sudo chmod -R 755 /home/ubuntu/affiliate_publisher
sudo chmod -R 775 /home/ubuntu/affiliate_publisher/media
sudo chmod 600 /home/ubuntu/affiliate_publisher/.env

# Restart services
echo "Restarting services..."
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart affiliate_publisher

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
sudo systemctl enable nginx

# Enable supervisor on boot
sudo systemctl enable supervisor

echo "======================================"
echo "Deployment complete!"
echo "======================================"
echo "Next steps:"
echo "1. Edit your .env file: nano /home/ubuntu/affiliate_publisher/.env"
echo "2. Create a superuser: cd /home/ubuntu/affiliate_publisher && source venv/bin/activate && python manage.py createsuperuser"
echo "3. Update ALLOWED_HOSTS in .env with your domain/IP"
echo "4. Access your app at: http://your-ec2-ip"
echo "======================================"