# Nginx Web Dockerfile
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# Copy static files
COPY static/ /var/www/html/static/
COPY templates/ /var/www/html/templates/

# Create log directory
RUN mkdir -p /var/log/nginx

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]