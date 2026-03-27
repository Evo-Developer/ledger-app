FROM nginx:alpine

RUN apk add --no-cache openssl

# Remove default nginx configuration and default site
RUN rm /etc/nginx/conf.d/default.conf && \
    rm -rf /usr/share/nginx/html/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create html directory and assets
RUN mkdir -p /usr/share/nginx/html/assets /etc/nginx/certs

# Copy all HTML files
COPY *.html /usr/share/nginx/html/

# Copy PWA files
COPY manifest.webmanifest /usr/share/nginx/html/
COPY service-worker.js /usr/share/nginx/html/

# Copy assets directory
COPY assets /usr/share/nginx/html/assets

# Set permissions
RUN chmod -R 755 /usr/share/nginx/html

# Copy HTTPS bootstrap script
COPY start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh

# Expose ports
EXPOSE 80 443

# Start nginx
CMD ["/start-nginx.sh"]
