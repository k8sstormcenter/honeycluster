# Use the official PHP image
FROM php:7.4-apache

# Install ping
RUN apt-get update && \
    apt-get install -y iputils-ping wget curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the PHP script and index.html files into the container
COPY ping.php /var/www/html/
COPY index.html /var/www/html/

# Expose port 80 for Apache
EXPOSE 80

# Start Apache in the foreground
CMD ["apache2-foreground"]