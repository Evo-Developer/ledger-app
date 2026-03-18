FROM nginx:alpine

# Remove default nginx configuration and default site
RUN rm /etc/nginx/conf.d/default.conf && \
    rm -rf /usr/share/nginx/html/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create html directory and assets
RUN mkdir -p /usr/share/nginx/html/assets

# Copy all HTML files
COPY *.html /usr/share/nginx/html/

# Copy assets directory
COPY assets /usr/share/nginx/html/assets

# Set permissions
RUN chmod -R 755 /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
